# 90-Day Pilot Playbook
## Compounding Intelligence Platform — SOC Copilot
**Version:** 1.0 · March 2026  
**Audience:** Customer Champion + Implementation Lead  
**Purpose:** Week-by-week guide from DPA signature to Tier 2 value demonstration

---

## The Pilot Promise

At the end of 90 days you will have:

1. A system that has seen your environment's specific noise profile and calibrated its distance metric accordingly (DiagonalKernel, Week 1)
2. A measurable accuracy baseline from shadow mode — what we predicted vs. what your analysts actually decided (Week 4)
3. Live triage recommendations with full factor provenance — every recommendation traceable to six numbers your team can inspect (Week 5)
4. An IKS score and centroid drift chart showing the system getting smarter from your decisions (Week 8–12)
5. An auto-approve rate ≥30% at ≥85% accuracy — analyst time freed from routine decisions (Week 10–12)
6. A CFO-ready ROI calculation with actual numbers from your deployment (Week 12)

**If any of these is not achieved by Day 90, we extend the pilot at no charge until it is.**

---

## Prerequisites (Before Day 1)

| Item | Owner | Done When |
|---|---|---|
| DPA signed | Legal (both sides) | Countersigned DPA in hand |
| SIEM access granted | Customer IT | API key / read token for Splunk or Sentinel |
| Champion identified | Customer | Named point-of-contact with analyst team access |
| Implementation slot booked | Both | 2-hour kickoff call scheduled |
| On-premise server provisioned | Customer IT | Ubuntu 22.04+, 16GB RAM, 4 cores, 100GB SSD, Python 3.11 |

---

## Week 1 — P28 Phase 0-2: Import, Compute, Qualify

**Goal:** System has 30 days of historical alert data. Noise profile measured. Kernel selected.

### Day 1–2: Import (P28 Phase 1)
- Connect SIEM connector (Splunk: `config/splunk_connector.yaml` / Sentinel: `config/sentinel_connector.yaml`)
- Ingest last 30 days of alerts into Neo4j graph (~15 min for typical SOC)
- Verify graph population: `GET /api/admin/graph-stats` → node_count, edge_count

**Expected output:** ~3,000–15,000 AlertNodes in graph. Entity resolution matches logged.

### Day 2–3: Compute (P28 Phase 2)
The pipeline measures per-factor noise σ across your alert stream and selects the optimal distance kernel:

```
python manage.py p28_compute --domain soc
```

**Expected output in deployment report:**
```
Factor noise profile:
  travel_match:           σ = 0.18  (high noise — travel data gaps)
  asset_criticality:      σ = 0.06  (low noise — CMDB well-maintained)
  threat_intel_enrichment:σ = 0.09  (moderate)
  time_anomaly:           σ = 0.07  (low)
  pattern_history:        σ = 0.21  (high noise — limited history)
  device_trust:           σ = 0.16  (moderate)

Noise ratio: 3.5× (max/min)
Kernel recommendation: DiagonalKernel (ratio > 1.5 threshold)
σ_mean under DiagonalKernel weighting: 0.14
Deployment zone: GREEN (σ_mean ≤ 0.157)

Remediation suggestions:
  travel_match: Connect HR travel system → σ drops to ~0.09 (est.)
  pattern_history: More historical data → improves over 90 days automatically
```

**Interpretation guide:**
- GREEN: Learning active from Day 1. DiagonalKernel weights unreliable factors down automatically — no manual configuration needed.
- AMBER: Learning active but conservative. Remediation suggestions show which data connections accelerate convergence.
- RED: Frozen mode. Consistency + compliance value from Day 1, learning deferred. See Frozen Mode ROI section.

### Day 3–5: Kickoff with Analyst Team
- Walk through noise profile with analyst team lead
- Review 5 sample alert recommendations from the historical data
- Configure referral rules R1-R7 for your environment (30 min):
  - R1: Who counts as "executive" in your org?
  - R3: Which alert categories are compliance-mandated for human review?
  - R6: What is your "new asset" age threshold?
- Set conservative thresholds for Week 2 shadow mode

**Deliverable:** Signed-off noise profile + configured referral rules.

---

## Week 2–4 — P28 Phase 3: Shadow Mode

**Goal:** System runs silently alongside analysts. We measure agreement rate, identify disagreements, validate predictions against reality.

### What Happens in Shadow Mode
- Every alert scored by the system. No recommendations shown to analysts yet.
- Every analyst decision recorded.
- Agreement rate tracked daily: "System said suppress, analyst said suppress → agree."
- Disagreements flagged for weekly review.

**No analyst behaviour change required.** Shadow mode is invisible to the analyst workflow.

### Week 2: First Shadow Report (available after 50 verified decisions)

`GET /api/soc/shadow-report` returns:

```
Shadow Mode Report — Day 7
Decisions recorded: 73
Agreement rate: 78.3%
Disagreement breakdown:
  System: suppress → Analyst: investigate  (12 cases, 16.4%)
  System: escalate → Analyst: suppress     (3 cases, 4.1%)
  System: investigate → Analyst: escalate  (2 cases, 2.7%)
Top disagreement categories: lateral_movement (8), insider_threat (4)
Conservation law: 24.7 (floor: 0.47) — GREEN
```

**Action:** Review the top 5–10 disagreements with the analyst team lead. This is your calibration conversation — not a scorecard, a learning session.

### Week 3: Calibration Checkpoint

By Day 21 (with V≥100 decisions), the system has enough data to show centroid drift — the first evidence of learning:

`GET /api/soc/centroid-evolution` → factor weight shifts over time

Expected: travel_match and pattern_history (high-noise factors) show lower absolute drift (DiagonalKernel attenuating them). threat_intel_enrichment and time_anomaly (low-noise) drift faster and more consistently.

If agreement rate < 72% at Day 21: schedule a 1-hour alignment session. Review the top 10 disagreements. Typical causes: category mapping gaps (alert_type → category), stale threat intel source, missing entity data.

### Week 4: Shadow Mode Review and Go/No-Go

**Criteria for shadow mode exit (any of):**
- ≥250 verified decisions AND agreement rate ≥ 75% → proceed to live
- ≥250 verified decisions AND agreement rate 65–75% → proceed with conservative thresholds (manual review band widens)
- < 250 decisions at Day 28 → extend shadow mode (low-volume SOC: normal)

**Deliverable:** Shadow Mode Report signed off by champion. Go/No-Go decision documented.

---

## Week 5–6 — Go Live: Live Triage Recommendations

**Goal:** System recommendations visible in Tab 1. Analyst team sees factor breakdowns. First referral rules firing.

### Day 29–30: Cutover

```
python manage.py enable_live_mode --domain soc --confirm
```

Tab 1 now shows recommendations with:
- Action (escalate/investigate/suppress/monitor) + confidence %
- Factor breakdown: 6 bars showing which factors drove the decision + kernel weight
- NL explanation: "Anomalous access from Singapore. travel_match=0.89 (high risk, weight=1.0). device_trust=0.71 (MDM enrolled, weight=0.8). Recommend: escalate at 87%."
- Referral flag (if any R1-R7 rule fires): "REFER TO ANALYST — Executive account."

### Week 5–6 Goals

| Metric | Target | Where to See |
|---|---|---|
| Live recommendations flowing | All alerts | Tab 1 alert list |
| Factor breakdown visible | All alerts | Tab 3 alert detail |
| Referral rules firing | R1, R3, R5 (most common) | Tab 3 referral badge |
| IKS > 0 | Initial drift visible | Tab 2 IKS header |
| No "Unknown" classification | < 5% | Tab 1 confidence column |

**Expected analyst reaction:** "It gets the easy ones right. It's wrong on [category X]." This is normal and productive. Category X becomes the Week 6–8 calibration focus.

---

## Week 7–8 — Learning Acceleration

**Goal:** IKS climbing. Auto-approve rate > 20%. Centroid drift visible in Tab 4.

### Decision Economics Checkpoint (Tab 4)

By Week 8, Tab 4 should show:
- Decisions recorded: 400–1,000 (depending on alert volume)
- Auto-approve rate: 20–35% (decisions at ≥85% confidence in high-precision categories)
- Minutes saved this week: auto_approved × 44 min × (1 − FP_rate)
- IKS: 15–35 (meaningful adaptation underway)

### Kernel Validation

The KernelSelector has been running both L2 and DiagonalKernel since Day 1. By Week 8 (≥250 decisions), it locks the winning kernel:

`GET /api/soc/deployment-status` → `kernel_locked: true, kernel: "diagonal", agreement_delta: +4.2pp`

If L2 wins: deployment has relatively uniform noise — both kernels perform similarly. Expected in FinServ or well-integrated environments.

### Week 8 Review with Champion

Agenda:
1. IKS trajectory: is it climbing? (should be — linear to √n)
2. Category breakdown: which categories have converged? Which still learning?
3. Referral rule review: are R1-R7 firing appropriately? Any false positives?
4. Remediation suggestions: which data connections would most accelerate learning?

---

## Week 9–12 — Value Demonstration

**Goal:** ≥30% auto-approve rate, measurable time savings, CFO-ready ROI number.

### Week 9–10: Auto-Approve Threshold Tuning

Default auto-approve threshold: confidence ≥ 85% AND category in calibrated set.

If auto-approve rate < 25% by Week 9: review category-specific thresholds with analyst lead. Typical adjustment: lower threshold for suppress/monitor in well-calibrated categories (lateral_movement, cloud_infrastructure). Keep high threshold for escalate.

`POST /api/admin/category-thresholds` → per-category confidence floor

### Week 11: Analyst Benchmarking (Preview)

Shadow mode data enables the first analyst benchmarking view:
- AI vs analyst agreement rate by analyst (anonymised)
- Per-shift breakdown (day/swing/night shift quality variance)
- Categories where AI caught cases analysts marked as false positives

**This is a coaching tool, not a performance review.** Frame it to the analyst team as: "Where does the system see things differently from us? What can we learn from that?"

### Week 12: 90-Day Review

**Deliverables for the 90-day review meeting:**

1. **IKS Score and Trajectory** — Tab 2 screenshot. "The system has accumulated 847 decisions of your firm's judgment."

2. **Accuracy Progression** — shadow mode vs. live mode agreement rate. Expected: 75–82% at Day 90 (compounding from 71.7% static baseline).

3. **Auto-Approve Rate and Time Savings:**
   ```
   Auto-approve rate: 38%
   Decisions recorded: 1,240
   Time saved: 1,240 × 0.38 × 44 min = 20,732 analyst-minutes = 345 analyst-hours
   At $75/hr fully-loaded: $25,900 saved in 90 days
   Annualised: ~$103,600
   ```

4. **Kernel Performance** — which kernel was selected and what lift it delivered.

5. **Referral Rules Performance** — how many referrals, breakdown by rule, false positive rate.

6. **Expansion Triggers** — see §8.

---

## Success Criteria and Expansion Triggers

| Metric | Threshold | Expansion Signal |
|---|---|---|
| IKS at Day 90 | ≥ 20 | System is learning. Expand to full alert volume. |
| Auto-approve rate | ≥ 30% | Ready for Tier 2 value discussion. |
| Accuracy vs. shadow | ≥ 75% | Trust threshold for live operation. |
| ROI (annualised) | ≥ 3× contract value | CFO approval for renewal and expansion. |
| Analyst satisfaction | "I trust the suppress recommendations" | Human adoption — the real gate. |

**Expansion path after 90-day success:**
- **Month 4–6:** Attack chain correlation. 17 individual alerts → 1 campaign. Tier 2 pricing discussion.
- **Month 6–9:** Multi-SIEM expansion (Splunk + Sentinel bidirectional). Full alert coverage.
- **Month 9–12:** NHI behavioural baselines. Service accounts, API keys, AI agents.

---

## Risk Mitigation During Pilot

| Risk | Signal | Response |
|---|---|---|
| Low alert volume (V < 50/day) | Tab 4 shows "CALIBRATING" | Extend shadow mode. Frozen Mode ROI still active. |
| High analyst override rate (> 40%) | Conservation law AMBER | Review category mapping. Schedule alignment session. |
| AMBER auto-pause fires | Learning frozen badge in Tab 2 | Diagnose quality signal. Pause, don't abandon. |
| Analyst distrust of recommendations | Low live-mode adoption | Focus on factor breakdown story — "show your work." |
| Referral rules over-firing | > 30% referral rate | Tune R1-R7 thresholds with champion. |

---

## Contacts

| Role | Responsibility | Contact |
|---|---|---|
| Implementation Lead | P28 pipeline, technical onboarding | [CONTACT] |
| Customer Success | Weekly check-ins, 90-day review | [CONTACT] |
| Security | DPA compliance, Evidence Ledger | [CONTACT] |
| Engineering (escalation) | Bug reports, threshold questions | [CONTACT] |

---

*Pilot Playbook v1.0 · Compounding Intelligence Platform · March 2026*  
*Companion documents: gtm_dpa_template_v1.md, gtm_security_posture_v1.md*  
*"The moat is the graph, not the model. After 1,000 decisions, this system knows your environment."*
