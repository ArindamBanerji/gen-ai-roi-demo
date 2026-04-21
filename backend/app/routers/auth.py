import logging
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse, Response, JSONResponse

log = logging.getLogger(__name__)
router = APIRouter(prefix="/saml", tags=["auth"])


def _get_saml_service():
    from app.auth.config import load_auth_config
    from ci_platform.auth.saml import SAMLConfig, SAMLService
    config = load_auth_config()
    saml_config = SAMLConfig(
        sp_entity_id=config.sp_entity_id,
        sp_acs_url=config.sp_acs_url,
        idp_entity_id=config.idp_entity_id,
        idp_sso_url=config.idp_sso_url,
        idp_x509_cert=config.idp_x509_cert,
    )
    return SAMLService(saml_config), config


@router.get("/metadata")
async def saml_metadata():
    svc, _ = _get_saml_service()
    xml = svc.get_sp_metadata()
    return Response(content=xml, media_type="application/xml")


@router.get("/login")
async def saml_login():
    svc, config = _get_saml_service()
    if not svc.is_configured():
        raise HTTPException(status_code=503,
            detail="SAML IdP not configured")
    result = svc.create_authn_request()
    return RedirectResponse(
        url=result["redirect_url"], status_code=302)


@router.post("/acs")
async def saml_acs(request: Request):
    from app.auth.jwt_utils import create_jwt, derive_role
    from app.auth.config import load_auth_config

    form_data = await request.form()
    saml_response = form_data.get("SAMLResponse", "")
    if not saml_response:
        raise HTTPException(status_code=400,
            detail="Missing SAMLResponse")

    svc, config = _get_saml_service()
    request_data = {
        "http_host": request.headers.get(
            "host", "localhost:8001"),
        "script_name": "/saml/acs",
        "https": "on" if request.url.scheme == "https"
                 else "off",
        "post_data": {"SAMLResponse": saml_response},
    }

    result = svc.validate_response(
        saml_response, request_data=request_data)

    if not result.get("valid"):
        log.warning("SAML validation failed: %s",
                    result.get("error"))
        raise HTTPException(status_code=401,
            detail=result.get("error",
                "SAML validation failed"))

    user_email = result.get("user_email", "unknown")
    attributes = result.get("attributes", {})
    groups = (
        attributes.get("groups", []) or
        attributes.get("memberOf", []) or
        attributes.get(
            "http://schemas.xmlsoap.org/claims/Group",
            []) or
        [])
    if isinstance(groups, str):
        groups = [groups]

    role = derive_role(groups, config.admin_groups)
    token = create_jwt(user_email, role, groups, config)

    log.info("[AUTH] SAML login: %s role=%s groups=%s",
             user_email, role, groups)

    response = RedirectResponse(url="/", status_code=302)
    response.set_cookie(
        key="soc_auth_token", value=token,
        httponly=True,
        secure=request.url.scheme == "https",
        samesite="lax",
        max_age=config.jwt_lifetime_hours * 3600)
    return response


@router.get("/logout")
async def saml_logout():
    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie(key="soc_auth_token")
    log.info("[AUTH] User logged out")
    return response


@router.get("/status")
async def saml_status():
    from app.auth.config import load_auth_config
    config = load_auth_config()
    svc, _ = _get_saml_service()
    return {
        "saml_enabled": config.saml_enabled,
        "idp_configured": svc.is_configured(),
        "sp_entity_id": config.sp_entity_id,
        "sp_acs_url": config.sp_acs_url,
    }
