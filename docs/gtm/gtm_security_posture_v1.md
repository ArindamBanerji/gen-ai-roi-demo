# Security Posture Document
## Compounding Intelligence Platform — SOC Copilot
**Version:** 1.0 · March 2026
**Audience:** CISO / Security Architect evaluating vendor security
**Classification:** Public — safe to share with prospects

---

## Executive Summary

SOC Copilot is designed on a security-first architecture with four principles: no cloud egress of customer data, every decision cryptographically auditable, learning safety rails that prevent silent degradation, and compliance artefacts built into the product rather than added after deployment.

---

## 1. Deployment Architecture

### 1.1 On-Premise by Default

The base deployment runs entirely within the customer's infrastructure. No customer data — alert metadata, factor vectors, decision records, centroid tensors, or analyst identifiers — leaves the customer's environment.

```
Customer Infrastructure:
  ├── SOC Copilot backend (FastAPI, Python 3.11)
  ├── Neo4j graph database (per-deployment instance)
  ├── GAE library (graph-attention-engine, Apache 2.0)
  └── ci-platform (deployment qualification, audit)

External dependencies (base deployment): ZERO
```

**Cloud deployment variant:** Available as an option. In this configuration, data is processed in a dedicated tenant environment. Standard Contractual Clauses (GDPR) and a sub-processor list are provided. Contact for details.

### 1.2 Network Isolation

| Data Flow | Direction | Encrypted | Notes |
|---|---|---|---|
| SIEM → SOC Copilot | Inbound | TLS 1.2+ | Alert ingestion |
| SOC Copilot → Sentinel/Splunk | Outbound | TLS 1.2+ | Write-back only (enrichment tags, IKS, confidence) |
| CISA KEV / NVD | Outbound | TLS 1.2+ | Threat intel pull — public data only |
| Analyst browser → Frontend | Inbound | TLS 1.2+ | React UI served from local deployment |

No telemetry, no usage data, no model training data sent to vendor.

---

## 2. Authentication and Access Control

### 2.1 SAML 2.0 SSO

Authentication is via SAML 2.0 SSO, integrating with the customer's existing identity provider (Okta, Azure AD, Ping, ADFS). No local password database.

- SP-initiated and IdP-initiated flows supported
- Assertion signing required (SHA-256)
- Session timeout: configurable (default 8 hours)

### 2.2 Role-Based Access

| Role | Access |
|---|---|
| SOC Analyst | Alert triage, Tab 1-4 view, override submission |
| SOC Lead | All analyst permissions + shadow mode configuration |
| CISO / Executive | Tab 5 executive narrative, IKS dashboard, read-only |
| Platform Admin | P28 onboarding, threshold configuration, evidence export, reset |

### 2.3 API Security

All backend endpoints require authenticated session. No unauthenticated endpoints in production deployment.

---

## 3. Data Handling

### 3.1 PII Redaction at Ingestion

The ci-platform ingestion pipeline applies PII redaction before any data reaches the graph:

| Pattern Class | Strategy | Example |
|---|---|---|
| Email addresses | Hash (SHA-256) | analyst@firm.com → [HASH] |
| IP addresses | Configurable: redact or hash | 192.168.1.1 → [IP-REDACTED] |
| Credit card numbers | Drop | Never stored |
| Social Security Numbers | Drop | Never stored |
| Phone numbers | Redact | +1-555-0100 → [PHONE-REDACTED] |

Strategy is configurable per pattern class. Default is conservative (drop > hash > redact).

### 3.2 What Is and Is Not Stored

**Stored in Neo4j graph:**
- Alert metadata (type, category, timestamp, system IDs)
- Factor vectors (6 numerical scores per alert, range [0,1])
- Decision records (action, confidence, override flag, outcome)
- Pseudonymised analyst IDs (for quality tracking)
- Entity nodes (assets, users — anonymised identifiers only)

**Never stored:**
- Alert payload content (raw log lines, packet captures, file contents)
- Employee names, email addresses, or PII in free-text form
- Alert body or message content
- Any data not enumerated above

### 3.3 Data Retention

Default retention: 90 days rolling for Decision Records. Configurable per deployment. Centroid tensor and kernel weights retained for duration of deployment (required for product function). Evidence Ledger retained per customer's document retention policy.

---

## 4. Audit Trail

### 4.1 Evidence Ledger

Every triage decision is recorded in a hash-chained Evidence Ledger:

- **Tamper-evident:** SHA-256 hash chain. Any modification to a past record breaks the chain and is detected by `verify_chain()`.
- **Complete:** Records every decision with: alert_id, timestamp, factor_breakdown, action, confidence, outcome, analyst_override, centroid_state_hash.
- **Epistemic state:** Each entry includes kernel_type, noise_zone, and conservation_status — the conditions under which the decision was made (EU AI Act Art. 15).
- **Export:** PDF (human-readable) and CSV (SIEM/GRC-importable) via `/api/soc/evidence-export`.

### 4.2 Audit Access

Evidence Ledger is accessible to Platform Admins and exportable at any time. No vendor access to the ledger — it resides entirely in the customer's deployment.

---

## 5. Learning Safety

### 5.1 Asymmetric Learning Rate

Analyst override quality is inherently noisier than confirmed decisions. The learning rate is asymmetric:

- `η_confirm = 0.05` — confirmed decisions (clean signal)
- `η_override = 0.01` — analyst overrides (noisy signal, attenuated 5×)

This prevents 13-27pp centroid degradation from low-quality override signals (validated across 24 deployment personas).

### 5.2 Conservation Law Monitoring

The system monitors learning signal health continuously: `α(t) · q(t) · V(t) ≥ θ_min`

When signal drops to AMBER: **AMBER auto-pause** — learning freezes automatically. No silent degradation. Operator is notified.

When signal drops to RED: frozen scorer mode. Consistency and compliance value continue. Learning resumes when signal recovers.

### 5.3 Checkpoint and Rollback

ProfileSnapshot recorded every 50 decisions (when synthesis active). Any prior state is recoverable via the `/api/admin/rollback` endpoint. This addresses the finding (EXP-OP2) that 35% of centroids damaged by harmful overrides never self-recover — rollback is the correct repair mechanism.

### 5.4 Shadow Mode Qualification

Learning does not activate until the deployment passes a 250-decision shadow mode qualification (P28 pipeline). Shadow mode runs both L2 and DiagonalKernel simultaneously, measuring agreement rate against analyst decisions before going live. **Learning never activates silently.**

---

## 6. EU AI Act Compliance

Enforcement date: August 2, 2026.

| Article | Requirement | Implementation |
|---|---|---|
| Art. 9 — Risk Management | Documented risk log, known risks identified | N3 Endogenous Feedback Loop disclosed in DPA. Shadow mode is the mitigation. |
| Art. 12 — Logging | Automatic logging throughout lifecycle | Hash-chained Evidence Ledger. Every decision immutable. |
| Art. 13 — Transparency | Users can interpret system output | Six-factor breakdown + kernel weights + NL explanation per decision. "Show your work." |
| Art. 14 — Human Oversight | Humans can intervene and override | Referral Rules R1-R7 (VETO mechanism). Auto-approve override at any time. AMBER auto-pause. |
| Art. 15 — Robustness | Accuracy and robustness logging | kernel_type, noise_zone, conservation_status per decision in Evidence Ledger. Checkpoint/rollback. |

### 6.1 N3 Risk Disclosure (Art. 9 mandatory)

> **N3 Endogenous Feedback Loop (Residual Risk: MEDIUM)**
> The system's calibration state may influence which alerts are selected for analyst verification. If verification selection is systematically biased, centroid learning may learn from a biased sample. Shadow mode (30-day pre-deployment baseline) measures verification selection bias before live mode activates.

---

## 7. Vulnerability Management

| Area | Policy |
|---|---|
| Dependency scanning | All Python and Node.js dependencies scanned before release |
| Vulnerability disclosure | 72-hour notification to affected customers |
| Penetration testing | Planned before first production customer deployment |
| SOC 2 Type II | In progress — expected Q3 2026 |
| CVE response | Critical: patch within 48 hours. High: within 7 days. |

---

## 8. Key Numbers for RFP Response

| Control | Status |
|---|---|
| Encryption at rest | Neo4j enterprise encryption (configurable AES-256) |
| Encryption in transit | TLS 1.2+ for all connections |
| Authentication | SAML 2.0 SSO |
| Multi-factor authentication | Enforced at IdP level (customer-controlled) |
| Data residency | On-premise by default — data never leaves customer infrastructure |
| Sub-processors (base) | Zero |
| Audit trail | Hash-chained, tamper-evident, exportable |
| Learning safety | Asymmetric η, AMBER auto-pause, checkpoint/rollback |
| Right to erasure (GDPR Art. 17) | Analyst decision records deletable via admin endpoint |
| AI transparency | Factor-level explanation per decision |
| Human oversight | Referral VETO, manual override always available |

---

*Security Posture Document v1.0 · Compounding Intelligence Platform · March 2026*
*Companion: gtm_dpa_template_v1.md, gtm_vsq_prefill_v1.md*
