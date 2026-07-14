import os
import logging
from dataclasses import dataclass, field
from typing import List

log = logging.getLogger(__name__)


@dataclass
class AuthConfig:
    saml_enabled: bool = False
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    jwt_lifetime_hours: int = 8
    idp_entity_id: str = ""
    idp_sso_url: str = ""
    idp_x509_cert: str = ""
    sp_entity_id: str = "soc-copilot"
    sp_acs_url: str = "http://127.0.0.1:8001/saml/acs"
    admin_groups: List[str] = field(
        default_factory=lambda: ["soc-admins", "administrators"]
    )

    def validate(self) -> List[str]:
        errors = []
        if self.saml_enabled:
            if not self.jwt_secret:
                errors.append(
                    "SAML_JWT_SECRET required when SAML_ENABLED=true")
            elif len(self.jwt_secret) < 32:
                errors.append(
                    "SAML_JWT_SECRET must be >= 32 characters")
            if not self.idp_entity_id:
                errors.append("SAML_IDP_ENTITY_ID required")
            if not self.idp_sso_url:
                errors.append("SAML_IDP_SSO_URL required")
            if not self.idp_x509_cert:
                errors.append("SAML_IDP_X509_CERT required")
        return errors


def load_auth_config() -> AuthConfig:
    return AuthConfig(
        saml_enabled=os.getenv(
            "SAML_ENABLED", "false").lower() == "true",
        jwt_secret=os.getenv("SAML_JWT_SECRET", ""),
        jwt_algorithm="HS256",
        jwt_lifetime_hours=int(
            os.getenv("SAML_JWT_LIFETIME_HOURS", "8")),
        idp_entity_id=os.getenv("SAML_IDP_ENTITY_ID", ""),
        idp_sso_url=os.getenv("SAML_IDP_SSO_URL", ""),
        idp_x509_cert=os.getenv("SAML_IDP_X509_CERT", ""),
        sp_entity_id=os.getenv(
            "SAML_SP_ENTITY_ID", "soc-copilot"),
        sp_acs_url=os.getenv(
            "SAML_SP_ACS_URL",
            "http://127.0.0.1:8001/saml/acs"),
    )
