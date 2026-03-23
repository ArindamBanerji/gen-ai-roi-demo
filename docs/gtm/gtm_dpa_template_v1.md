# Data Processing Agreement
## Compounding Intelligence Platform — SOC Copilot
**Version:** 1.0 · March 2026  
**Status:** Template — customise controller/processor names and jurisdiction before execution  
**Classification:** Confidential — Legal Review Required Before Use

---

## PARTIES

**Controller ("Customer"):** [CUSTOMER LEGAL NAME], a [jurisdiction] company with registered offices at [ADDRESS] ("Controller")

**Processor ("Company"):** [COMPANY LEGAL NAME], a [jurisdiction] company with registered offices at [ADDRESS] ("Processor")

Together referred to as the "Parties."

This Data Processing Agreement ("DPA") forms part of, and is subject to, the Master Services Agreement or Order Form between the Parties ("Principal Agreement"). In the event of conflict, this DPA governs with respect to personal data processing.

---

## 1. DEFINITIONS

**"Centroid Tensor"** means the numerical array μ ∈ ℝ^(C×A×d) representing the system's accumulated institutional knowledge, derived entirely from the Controller's own verified analyst decisions.

**"Kernel Weights"** means the per-factor noise estimates W = diag(1/σ²) comprising the deployment-specific distance metric, derived from the Controller's operational alert stream.

**"Alert Metadata"** means structured fields associated with a security alert including alert type, category classification, timestamp, and system-assigned identifiers — but expressly excluding alert payload content (raw log data, packet captures, file contents).

**"Factor Vector"** means the numerical representation f ∈ [0,1]^d encoding the six measurable dimensions of an alert (travel_match, asset_criticality, threat_intel_enrichment, time_anomaly, pattern_history, device_trust) as computed by the GAE pipeline.

**"Decision Record"** means a graph node in the deployment's Neo4j instance capturing: alert_id, factor_vector, action_taken, confidence_score, analyst_override (boolean), outcome_verified (boolean), and timestamp.

**"Personal Data"** has the meaning given in applicable data protection law (GDPR Art. 4(1) / UK GDPR / CCPA as applicable).

**"Processing"** has the meaning given in applicable data protection law.

---

## 2. SUBJECT MATTER AND NATURE OF PROCESSING

### 2.1 Purpose
The Processor processes data on behalf of the Controller solely for the purpose of: operating the SOC Copilot inference pipeline, calibrating and updating the Centroid Tensor and Kernel Weights, generating triage recommendations, and producing audit and compliance artefacts as specified in the Principal Agreement.

### 2.2 Data Categories Processed

| Category | Description | Personal Data? | Basis |
|---|---|---|---|
| Alert Metadata | Type, category, timestamp, system IDs | No (typically) | Contract performance |
| Factor Vectors | 6-dimensional numerical scores per alert | No | Contract performance |
| Decision Records | Action, confidence, override flag, outcome | No | Contract performance |
| Analyst Identifiers | Anonymised analyst ID for quality tracking | Yes — pseudonymised | Legitimate interest |
| Identity Tier Flags | executive / board / c_suite (binary flag, no name) | No (flag only) | Contract performance |
| Asset Metadata | Asset age, criticality score (no PII content) | No | Contract performance |

### 2.3 Data Expressly NOT Processed

The following data is **never ingested, stored, or processed** by the Processor's systems:

- Alert payload content (raw log lines, packet captures, file contents, email bodies)
- Employee names, email addresses, or personal identifiers in free-text form
- Biometric or health data
- Financial account details
- Any data not enumerated in §2.2 above

**PII Redaction:** The ci-platform ingestion pipeline applies five regex pattern classes (email, IP address, credit card, SSN, phone) at ingestion with three strategies (redact, hash, drop). PII that passes the ingestion filter is redacted before any graph write. No PII reaches the Neo4j graph.

---

## 3. CONTROLLER INSTRUCTIONS

### 3.1 Documented Instructions
The Controller instructs the Processor to process data as described in §2 and as further specified in the Principal Agreement and applicable product documentation.

### 3.2 Compliance Instruction
The Processor shall notify the Controller without undue delay if it believes an instruction infringes applicable data protection law (GDPR Art. 28(3)(h)).

---

## 4. PROCESSOR OBLIGATIONS

### 4.1 Confidentiality
The Processor ensures that persons authorised to process personal data are bound by appropriate confidentiality obligations (GDPR Art. 28(3)(b)).

### 4.2 Security Measures
The Processor implements and maintains the technical and organisational security measures described in Annex B (Security Posture), including:

- **Deployment model:** On-premise deployment within the Controller's infrastructure. No alert data leaves the Controller's environment.
- **Authentication:** SAML 2.0 SSO with role-based access control.
- **Data isolation:** Per-deployment Neo4j instance. No cross-customer data access.
- **Audit trail:** Hash-chained Evidence Ledger. Every decision immutably recorded with centroid_state_hash.
- **Learning safety:** AMBER auto-pause suspends centroid learning when conservation law signals quality degradation. η_override=0.01 attenuates noisy analyst signals by 5× relative to confirmed signals.
- **Rollback:** TD-033 checkpoint mechanism allows rollback of centroid state to any prior ProfileSnapshot.

### 4.3 Sub-processors

**Base Deployment:** The Processor uses **zero sub-processors** in the base on-premise deployment. No Controller data is transmitted to third-party services. All computation occurs within the Controller's infrastructure using the deployed software stack (Python, Neo4j, FastAPI).

**Optional Cloud Deployment:** If the Controller elects a cloud-hosted deployment variant, a list of sub-processors will be provided in Annex C. The Controller must provide prior written authorisation before any new sub-processor is engaged (GDPR Art. 28(2)).

### 4.4 Data Subject Rights
The Processor shall, to the extent technically feasible, assist the Controller in fulfilling data subject rights requests (GDPR Arts. 15–22). Specifically:

- **Right of access (Art. 15):** Decision Records for a given pseudonymised analyst ID are queryable via the Evidence Ledger API.
- **Right to erasure (Art. 17):** Decision Record nodes for a specified analyst ID can be deleted via the `/api/admin/erase-analyst/{id}` endpoint. **Note:** Erasing Decision Records does not un-update centroids already trained on those decisions. If the Controller requires centroid rollback prior to the data subject's first decision, a checkpoint rollback must be performed separately.
- **Right to portability (Art. 20):** Centroid Tensor and Kernel Weights are exportable as JSON artefacts on request. These are the Controller's intellectual assets under §7.

### 4.5 Data Protection Impact Assessment
The Processor shall provide reasonable assistance to the Controller in conducting a DPIA where required by Art. 35, including making available the N3 risk disclosure (§4.6) and the evidence ledger.

### 4.6 Known Risk Disclosure (EU AI Act Art. 9)
The following known risk is disclosed per EU AI Act Article 9(2)(a)–(b):

> **N3 Endogenous Feedback Loop (Residual Risk: MEDIUM)**
>
> The system's calibration state may influence which alerts are selected for analyst verification (high-confidence decisions are less likely to be manually reviewed). If verification selection is systematically biased, centroid learning may learn from a biased sample. Shadow mode (30-day pre-deployment baseline) measures verification selection bias before live mode activates. Full characterisation requires live production data.
>
> Mitigation: Shadow mode deployment required before go-live (enforced by P28 pipeline). Conservation law monitoring (α·q·V ≥ θ_min) provides ongoing early warning.

---

## 5. RETENTION AND DELETION

### 5.1 Default Retention

| Data Category | Default Retention | Configurable? |
|---|---|---|
| Decision Records (graph nodes) | 90 days rolling | Yes — per Controller request |
| ProfileSnapshot nodes (checkpoints) | 12 months | Yes |
| Evidence Ledger export (PDF/CSV) | Retained per Controller's document policy | Controller responsibility |
| Centroid Tensor + Kernel Weights | Retained for duration of Principal Agreement | No — required for product function |

### 5.2 Deletion on Termination
Within 30 days of Principal Agreement termination, the Processor shall:
1. Provide the Controller with a final export of the Centroid Tensor, Kernel Weights, and Evidence Ledger.
2. Delete all data from any Processor-held systems (cloud-hosted variant only — on-premise data is under the Controller's direct control).
3. Certify deletion in writing.

---

## 6. AUDIT AND INSPECTION

### 6.1 Audit Rights
The Controller may audit the Processor's compliance with this DPA once per calendar year upon 30 days' notice, or immediately upon reasonable suspicion of breach. The Processor shall cooperate and provide access to relevant documentation, logs, and the Evidence Ledger.

### 6.2 Evidence Ledger
The hash-chained Evidence Ledger provides a tamper-evident record of every triage decision. Ledger exports are available in PDF (human-readable) and CSV (machine-readable, importable into Controller's SIEM or GRC platform) format via the `/api/soc/evidence-export` endpoint.

---

## 7. DATA OWNERSHIP AND INTELLECTUAL PROPERTY

### 7.1 Controller Owns the Intelligence

The following assets belong exclusively to the Controller and are not used by the Processor for any purpose other than the performance of the Principal Agreement:

| Asset | Description | Owner |
|---|---|---|
| Centroid Tensor μ | (C×A×d) array of institutional knowledge vectors | Controller |
| Kernel Weights W | Per-factor noise estimates from Controller's alert stream | Controller |
| Decision Records | Analyst triage history in Controller's graph | Controller |
| Evidence Ledger | Hash-chained audit trail | Controller |

### 7.2 Controller Can Take Their Intelligence
The Centroid Tensor and Kernel Weights are exportable at any time as portable JSON artefacts. They can be imported into any compatible deployment of the open-source GAE library (Apache 2.0, available at [GITHUB URL]).

### 7.3 Processor IP
The Processor retains all intellectual property rights in the software, algorithms, documentation, and trained models (if any) provided to the Controller. This DPA grants no licence to the Processor's intellectual property beyond what is necessary to perform the Principal Agreement.

---

## 8. BREACH NOTIFICATION

The Processor shall notify the Controller without undue delay (and in any event within **72 hours** of becoming aware) of any personal data breach (GDPR Art. 33), providing:

- Nature of the breach (categories and approximate number of data subjects and records affected)
- Contact details of the data protection officer or point of contact
- Likely consequences of the breach
- Measures taken or proposed to address the breach

**For on-premise deployments:** As all data resides in the Controller's infrastructure, security incidents affecting Controller data are primarily the Controller's responsibility to detect and notify. The Processor shall notify the Controller of any vulnerabilities discovered in the Processor software within 72 hours of discovery.

---

## 9. INTERNATIONAL TRANSFERS

**Base Deployment:** No personal data is transferred internationally by the Processor in the base on-premise deployment configuration. All processing occurs within the Controller's infrastructure.

**Cloud Deployment:** If applicable, Standard Contractual Clauses (SCC) — Controller to Processor module — are incorporated by reference as Annex D. The Processor conducts a Transfer Impact Assessment prior to any transfer to a third country.

---

## 10. TERM AND TERMINATION

This DPA remains in force for the duration of the Principal Agreement. Obligations under this DPA that by their nature should survive termination (including §7 data ownership and §8 breach notification for incidents discovered after termination) shall survive.

---

## ANNEX A — PROCESSING DETAILS SUMMARY

| Field | Value |
|---|---|
| Nature of processing | Inference, centroid learning, audit logging |
| Purpose | SOC alert triage decision support |
| Duration | Duration of Principal Agreement |
| Data subjects | Controller's employees (analyst identifiers, pseudonymised) |
| Data categories | See §2.2 |
| Sub-processors | None (base deployment) |
| Transfers | None (base on-premise deployment) |

---

## ANNEX B — TECHNICAL AND ORGANISATIONAL SECURITY MEASURES

See companion document: `gtm_security_posture_v1.md`

---

## SIGNATURES

**For the Controller:**

Name: ___________________________  
Title: ___________________________  
Date: ___________________________  
Signature: ______________________  

**For the Processor:**

Name: ___________________________  
Title: ___________________________  
Date: ___________________________  
Signature: ______________________  

---

*DPA Template v1.0 · Compounding Intelligence Platform · March 2026*  
*Legal review required before execution. Not legal advice.*  
*Companion documents: gtm_security_posture_v1.md, gtm_pilot_playbook_v1.md*
