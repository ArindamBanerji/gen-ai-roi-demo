# Vendor Security Questionnaire — Pre-filled Answers
## Compounding Intelligence Platform — SOC Copilot
**Version:** 1.0 · March 2026
**Format:** Question / Answer / Evidence Reference
**Note:** Answers reflect base on-premise deployment. Cloud deployment variant answers available separately.

---

## Section 1: Company and Product Overview

| Question | Answer | Evidence |
|---|---|---|
| Describe your product and its primary function | SOC Copilot is an AI-assisted alert triage system that learns institutional judgment from analyst decisions. It scores alerts using a kernel-based distance metric calibrated to the customer's environment, routes decisions through configurable referral rules, and produces a tamper-evident audit trail of every triage decision. | Product documentation |
| What data does your product process? | Alert metadata, numerical factor vectors, pseudonymised analyst identifiers, asset identifiers. No alert payload content, no PII in free-text form. | DPA §2.2 |
| Where is data processed and stored? | On-premise within the customer's infrastructure. No data leaves the customer's environment in the base deployment. | Architecture diagram |
| Do you have sub-processors? | Zero sub-processors in base on-premise deployment. | DPA §4.3 |

---

## Section 2: Data Security

| Question | Answer | Evidence |
|---|---|---|
| Encryption at rest | Neo4j enterprise encryption (AES-256 configurable). All centroid tensors and decision records encrypted at rest. | Deployment configuration |
| Encryption in transit | TLS 1.2+ for all connections: SIEM ingest, Sentinel/Splunk write-back, analyst browser sessions. | Network architecture |
| Key management | Customer-managed encryption keys. Vendor has no access to encryption keys. | On-premise deployment model |
| Data classification | Alert metadata: Internal. Factor vectors: Internal. Centroid tensor: Confidential (customer's institutional knowledge). Evidence Ledger: Confidential. | DPA §7 |
| Data minimisation | PII redaction at ingestion: 5 regex pattern classes (email, IP, credit card, SSN, phone), 3 strategies (drop, hash, redact). No alert payload content stored. | ci-platform redaction.py |
| Data retention | Default: 90 days rolling for Decision Records. Configurable per deployment. Centroid tensor retained for deployment duration. | DPA §5.1 |
| Data deletion / right to erasure | Analyst decision records deletable via `/api/admin/erase-analyst/{id}`. GDPR Art. 17 compliant. | DPA §4.4 |
| Data portability | Centroid tensor and kernel weights exportable as JSON at any time. Customer owns this data. | DPA §7 |
| Backup and recovery | ProfileSnapshot every 50 decisions. Checkpoint/rollback available via admin API. PITR available in cloud deployment. | TD-033 documentation |

---

## Section 3: Access Control

| Question | Answer | Evidence |
|---|---|---|
| Authentication mechanism | SAML 2.0 SSO. Integrates with customer IdP (Okta, Azure AD, Ping, ADFS). No local password database. | auth/saml.py |
| Multi-factor authentication | Enforced at customer IdP level. MFA policy is customer-controlled. | SAML integration |
| Role-based access control | Four roles: SOC Analyst, SOC Lead, CISO/Executive (read-only), Platform Admin. Least-privilege by default. | Security posture document §2.2 |
| Privileged access | Platform Admin role required for: P28 onboarding, threshold configuration, evidence export, system reset. Separation from analyst role. | Admin router |
| Vendor access to customer data | Zero. On-premise deployment — vendor has no access to customer's Neo4j instance, centroid tensor, or Evidence Ledger. | Deployment architecture |
| Session management | Configurable session timeout (default 8 hours). SAML session binding. | SAML configuration |

---

## Section 4: Application Security

| Question | Answer | Evidence |
|---|---|---|
| Secure development lifecycle | Code review required for all changes. Tests required for all features (478 GAE + 284 SOC + 88 ci-platform tests). Dependency scanning before release. | GitHub repository |
| Penetration testing | Planned before first production customer deployment. Results shared with customers under NDA. | Roadmap |
| Vulnerability disclosure | Vendor notifies affected customers within 72 hours of discovering a vulnerability affecting their deployment. | Security policy |
| OWASP Top 10 | Input validation on all API endpoints. SAML authentication — no local credential storage. No SQL injection surface (Neo4j Cypher with parameterised queries). | Code review |
| API security | All endpoints require authenticated session. No unauthenticated endpoints in production. Rate limiting configurable. | Backend architecture |
| Dependency management | Python and Node.js dependencies pinned. Regular updates. CVE monitoring. | pyproject.toml, package.json |

---

## Section 5: AI / ML Specific

| Question | Answer | Evidence |
|---|---|---|
| EU AI Act compliance status | Designed for compliance. Art. 9 (risk log), Art. 12 (logging), Art. 13 (transparency), Art. 14 (human oversight), Art. 15 (robustness) all implemented. Enforcement date: August 2, 2026. | Security posture §6 |
| Known AI risks disclosed | N3 Endogenous Feedback Loop disclosed in DPA (Art. 9 mandatory). Residual risk: MEDIUM. Mitigation: shadow mode pre-deployment. | DPA §4.6 |
| Human oversight mechanism | Referral Rules R1-R7 (VETO) — 7 configurable policy conditions that force human review regardless of system confidence. Manual override always available. AMBER auto-pause freezes learning on quality degradation. | referral_rules.py |
| Explainability | Every recommendation includes: six-factor breakdown with kernel weights, confidence %, NL explanation, referral reason (if applicable). No black-box decisions. | AlertTriageTab frontend |
| Model training on customer data | Learning uses customer's own verified analyst decisions only. Data is never used to train models for other customers. No cross-customer data sharing in base deployment. | ProfileScorer.update() |
| Bias and fairness monitoring | Conservation law monitors learning signal health. AMBER auto-pause prevents silent drift. Evidence Ledger audit trail enables retrospective bias analysis. | Conservation monitoring |
| AI model rollback | Checkpoint/rollback mechanism (TD-033). Any prior centroid state recoverable. | ProfileScorer.rollback() |

---

## Section 6: Incident Response

| Question | Answer | Evidence |
|---|---|---|
| Incident response plan | Documented IRP. CISO-level escalation within 1 hour of confirmed incident. Customer notification within 72 hours for incidents affecting customer data. | Security policy |
| Breach notification timeline | 72 hours from discovery — meets GDPR Art. 33 requirement. | DPA §8 |
| Evidence preservation | Evidence Ledger hash chain provides tamper-evident record of all system activity at time of incident. | Evidence Ledger |
| Recovery time objective | RTO: < 4 hours for on-premise deployment (centroid tensor + Evidence Ledger backup required). | Deployment guide |

---

## Section 7: Compliance and Certifications

| Question | Answer | Evidence |
|---|---|---|
| SOC 2 Type II | In progress. Expected Q3 2026. | Roadmap |
| SOC 2 Type I | Available on request under NDA. | |
| ISO 27001 | Not certified. On-premise deployment — customer's ISO 27001 controls apply to the deployment environment. | Architecture |
| GDPR | Designed for compliance. DPA template available. Right to erasure implemented. PII redaction at ingestion. | DPA template |
| HIPAA | On-premise deployment within customer's HIPAA-covered environment. BAA available. | DPA |
| EU AI Act | Compliance artefacts built into product (Art. 9-15). | Security posture §6 |
| DORA (financial entities) | Operational resilience testing via shadow mode. Evidence Ledger for audit. Checkpoint/rollback for recovery testing. | DPA |
| FedRAMP | Not applicable — on-premise deployment. | |

---

## Section 8: Third-Party Risk

| Question | Answer | Evidence |
|---|---|---|
| Sub-processors (base) | Zero. No third-party services used in base on-premise deployment. | DPA §4.3 |
| Open-source components | GAE library (Apache 2.0, published). ci-platform (Apache 2.0, published). Full dependency list available on request. | pyproject.toml |
| Software Bill of Materials (SBOM) | Available on request. | |
| Supply chain security | Dependencies pinned. GitHub Actions CI for automated testing. No build-time external calls. | CI configuration |

---

*VSQ Pre-fill v1.0 · Compounding Intelligence Platform · March 2026*
*Answers reflect base on-premise deployment. Cloud deployment answers available separately.*
*Companion documents: gtm_dpa_template_v1.md, gtm_security_posture_v1.md*
