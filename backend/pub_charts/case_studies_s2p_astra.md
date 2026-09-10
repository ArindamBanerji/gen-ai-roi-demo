# VLD With-Without Case Studies — S2P_ASTRA
**Generated from Stage 1 multi-hop scenarios**
**[PLANTED POSITIVE CONTROL — not production data]**

## Summary

| Category | Count | % |
|---|---|---|
| VLD saves (SP wrong, VLD right) | 40 | 89% |
| VLD hurts (SP right, VLD wrong) | 0 | 0% |
| Both correct | 3 | 7% |
| Both wrong | 2 | 4% |
| **Total multi-hop** | **45** | |

## Case Studies: VLD Saves

*Scenarios where single-pass gets it wrong and VLD gets it right.*

### Case 1: S2P-001-v1
**Type:** hidden_amendment
**Kind:** score_keyed | **rho:** 0.9

**Description:** SYN-Cedar Components: a 12% price increase on pump seals is authorized by a scoped amendment.

#### WITHOUT VLD (single-pass)
- Action: **escalate_to_procurement** ❌ (ground truth: approve)
- Based on surface factors only
- Distance to nearest centroid: 0.6544

#### WITH VLD (investigation)
- **Hop 1:** The invoice has operative contractual coverage once the applicable version is resolved.
  - Checked: contract_management_system
  - Found: Executed amendment SYN-AMD-0001 covers SYN-PO-0001 and pump seals; applicability is determined by the contract's delivery-date clause, not its PO creation date. Its effective date is 2026-08-01, before the 2026-08-15 delivery. The migrated PO references the superseded version. It identifies an approval-register key.
  - Factor `contract_coverage`: 0.080 → 0.949
  - Action after hop 1: **hold_for_review** → (dist: 0.9400)
- **Hop 2:** The apparent unauthorized-change exception is cleared by the scoped approval record.
  - Checked: approval_register
  - Found: The register key identifies approvals by the two roles required by SYN-POL-0001. Both signed on 2026-07-29; the invoice amount of USD 11200.00 is within their documented delegated limit. The approval packet identifies the operative rate-annex key.
  - Factor `policy_conformance`: 0.081 → 0.957
  - Action after hop 2: **partial_approve** → (dist: 0.7041)
- **Hop 3:** The price variance is fully explained by the effective approved amendment.
  - Checked: contract_rate_annex
  - Found: The scoped annex sets USD 112.00 per unit, replacing USD 100.00; 100 units x USD 112.00 = USD 11200.00, exactly the invoice total. No other fee is billed.
  - Factor `price_conformance`: 0.076 → 0.953
  - Action after hop 3: **approve** ✅ (dist: 0.1956)

- Action: **approve** ✅
- Distance to nearest centroid: 0.1956

**Why VLD changed the decision:** Approve USD 11200.00: receipt is documented, the effective amendment applies, approval authority is verified, and its rate exactly reconciles the invoice. All cited records existed before alert arrival. The factor values are planted fixture values, not customer measurements.

**Factor movement:**
| Factor | Surface | Enriched | Δ |
|---|---|---|---|
| amount_materiality | 0.406 | 0.406 | +0.000 |
| contract_coverage | 0.080 | 0.949 | +0.869 ← |
| duplicate_risk | 0.200 | 0.200 | +0.000 |
| policy_conformance | 0.081 | 0.957 | +0.875 ← |
| price_conformance | 0.076 | 0.953 | +0.877 ← |
| receipt_match | 0.641 | 0.641 | +0.000 |
| supplier_trust | 0.593 | 0.593 | +0.000 |

### Case 2: S2P-002-v1
**Type:** hidden_amendment
**Kind:** score_keyed | **rho:** 0.9

**Description:** SYN-Harbor Industrial: a 8% price increase on sterile filters is authorized by a scoped amendment.

#### WITHOUT VLD (single-pass)
- Action: **escalate_to_procurement** ❌ (ground truth: approve)
- Based on surface factors only
- Distance to nearest centroid: 0.6643

#### WITH VLD (investigation)
- **Hop 1:** The invoice has operative contractual coverage once the applicable version is resolved.
  - Checked: contract_management_system
  - Found: Executed amendment SYN-AMD-0002 covers SYN-PO-0002 and sterile filters; applicability is determined by the buyer legal entity listed in the amendment, not the parent-company record. Its effective date is 2026-08-01, before the 2026-08-15 delivery. The migrated PO references the superseded version. It identifies an approval-register key.
  - Factor `contract_coverage`: 0.080 → 0.940
  - Action after hop 1: **hold_for_review** → (dist: 0.9482)
- **Hop 2:** The apparent unauthorized-change exception is cleared by the scoped approval record.
  - Checked: approval_register
  - Found: The register key identifies approvals by the two roles required by SYN-POL-0002. Both signed on 2026-07-29; the invoice amount of USD 12960.00 is within their documented delegated limit. The approval packet identifies the operative rate-annex key.
  - Factor `policy_conformance`: 0.077 → 0.946
  - Action after hop 2: **partial_approve** → (dist: 0.6986)
- **Hop 3:** The price variance is fully explained by the effective approved amendment.
  - Checked: contract_rate_annex
  - Found: The scoped annex sets USD 86.40 per unit, replacing USD 80.00; 150 units x USD 86.40 = USD 12960.00, exactly the invoice total. No other fee is billed.
  - Factor `price_conformance`: 0.071 → 0.944
  - Action after hop 3: **approve** ✅ (dist: 0.1768)

- Action: **approve** ✅
- Distance to nearest centroid: 0.1768

**Why VLD changed the decision:** Approve USD 12960.00: receipt is documented, the effective amendment applies, approval authority is verified, and its rate exactly reconciles the invoice. All cited records existed before alert arrival. The factor values are planted fixture values, not customer measurements.

**Factor movement:**
| Factor | Surface | Enriched | Δ |
|---|---|---|---|
| amount_materiality | 0.398 | 0.398 | +0.000 |
| contract_coverage | 0.080 | 0.940 | +0.860 ← |
| duplicate_risk | 0.189 | 0.189 | +0.000 |
| policy_conformance | 0.077 | 0.946 | +0.869 ← |
| price_conformance | 0.071 | 0.944 | +0.873 ← |
| receipt_match | 0.649 | 0.649 | +0.000 |
| supplier_trust | 0.600 | 0.600 | +0.000 |

### Case 3: S2P-003-v1
**Type:** hidden_amendment
**Kind:** score_keyed | **rho:** 0.7

**Description:** SYN-Maple Systems: a 6% price increase on network modules is authorized by a scoped amendment.

#### WITHOUT VLD (single-pass)
- Action: **escalate_to_procurement** ❌ (ground truth: approve)
- Based on surface factors only
- Distance to nearest centroid: 0.6467

#### WITH VLD (investigation)
- **Hop 1:** The invoice has operative contractual coverage once the applicable version is resolved.
  - Checked: contract_management_system
  - Found: Executed amendment SYN-AMD-0003 covers SYN-PO-0003 and network modules; applicability is determined by the exact SKU and revision in the rate annex. Its effective date is 2026-08-01, before the 2026-08-15 delivery. The migrated PO references the superseded version. It identifies an approval-register key.
  - Factor `contract_coverage`: 0.070 → 0.953
  - Action after hop 1: **hold_for_review** → (dist: 0.9378)
- **Hop 2:** The apparent unauthorized-change exception is cleared by the scoped approval record.
  - Checked: approval_register
  - Found: The register key identifies approvals by the two roles required by SYN-POL-0003. Both signed on 2026-07-29; the invoice amount of USD 10600.00 is within their documented delegated limit. The approval packet identifies the operative rate-annex key.
  - Factor `policy_conformance`: 0.083 → 0.947
  - Action after hop 2: **partial_approve** → (dist: 0.7002)
- **Hop 3:** The price variance is fully explained by the effective approved amendment.
  - Checked: contract_rate_annex
  - Found: The scoped annex sets USD 132.50 per unit, replacing USD 125.00; 80 units x USD 132.50 = USD 10600.00, exactly the invoice total. No other fee is billed.
  - Factor `price_conformance`: 0.080 → 0.949
  - Action after hop 3: **approve** ✅ (dist: 0.1945)

- Action: **approve** ✅
- Distance to nearest centroid: 0.1945

**Why VLD changed the decision:** Approve USD 10600.00: receipt is documented, the effective amendment applies, approval authority is verified, and its rate exactly reconciles the invoice. All cited records existed before alert arrival. The factor values are planted fixture values, not customer measurements.

**Factor movement:**
| Factor | Surface | Enriched | Δ |
|---|---|---|---|
| amount_materiality | 0.414 | 0.414 | +0.000 |
| contract_coverage | 0.070 | 0.953 | +0.884 ← |
| duplicate_risk | 0.198 | 0.198 | +0.000 |
| policy_conformance | 0.083 | 0.947 | +0.864 ← |
| price_conformance | 0.080 | 0.949 | +0.869 ← |
| receipt_match | 0.644 | 0.644 | +0.000 |
| supplier_trust | 0.593 | 0.593 | +0.000 |

### Case 4: S2P-004-v1
**Type:** hidden_amendment
**Kind:** score_keyed | **rho:** 0.7

**Description:** SYN-Ridge Laboratory: a 10% price increase on packaging inserts is authorized by a scoped amendment.

#### WITHOUT VLD (single-pass)
- Action: **escalate_to_procurement** ❌ (ground truth: approve)
- Based on surface factors only
- Distance to nearest centroid: 0.6512

#### WITH VLD (investigation)
- **Hop 1:** The invoice has operative contractual coverage once the applicable version is resolved.
  - Checked: contract_management_system
  - Found: Executed amendment SYN-AMD-0004 covers SYN-PO-0004 and packaging inserts; applicability is determined by the release quantity tier, not total framework volume. Its effective date is 2026-08-01, before the 2026-08-15 delivery. The migrated PO references the superseded version. It identifies an approval-register key.
  - Factor `contract_coverage`: 0.084 → 0.941
  - Action after hop 1: **hold_for_review** → (dist: 0.9321)
- **Hop 2:** The apparent unauthorized-change exception is cleared by the scoped approval record.
  - Checked: approval_register
  - Found: The register key identifies approvals by the two roles required by SYN-POL-0004. Both signed on 2026-07-29; the invoice amount of USD 11000.00 is within their documented delegated limit. The approval packet identifies the operative rate-annex key.
  - Factor `policy_conformance`: 0.076 → 0.942
  - Action after hop 2: **partial_approve** → (dist: 0.6810)
- **Hop 3:** The price variance is fully explained by the effective approved amendment.
  - Checked: contract_rate_annex
  - Found: The scoped annex sets USD 55.00 per unit, replacing USD 50.00; 200 units x USD 55.00 = USD 11000.00, exactly the invoice total. No other fee is billed.
  - Factor `price_conformance`: 0.089 → 0.951
  - Action after hop 3: **approve** ✅ (dist: 0.1769)

- Action: **approve** ✅
- Distance to nearest centroid: 0.1769

**Why VLD changed the decision:** Approve USD 11000.00: receipt is documented, the effective amendment applies, approval authority is verified, and its rate exactly reconciles the invoice. All cited records existed before alert arrival. The factor values are planted fixture values, not customer measurements.

**Factor movement:**
| Factor | Surface | Enriched | Δ |
|---|---|---|---|
| amount_materiality | 0.407 | 0.407 | +0.000 |
| contract_coverage | 0.084 | 0.941 | +0.857 ← |
| duplicate_risk | 0.206 | 0.206 | +0.000 |
| policy_conformance | 0.076 | 0.942 | +0.866 ← |
| price_conformance | 0.089 | 0.951 | +0.862 ← |
| receipt_match | 0.656 | 0.656 | +0.000 |
| supplier_trust | 0.610 | 0.610 | +0.000 |

### Case 5: S2P-005-v1
**Type:** hidden_amendment
**Kind:** score_keyed | **rho:** 0.9

**Description:** SYN-Willow Services: a 5% price increase on meter assemblies is authorized by a scoped amendment.

#### WITHOUT VLD (single-pass)
- Action: **escalate_to_procurement** ❌ (ground truth: approve)
- Based on surface factors only
- Distance to nearest centroid: 0.6632

#### WITH VLD (investigation)
- **Hop 1:** The invoice has operative contractual coverage once the applicable version is resolved.
  - Checked: contract_management_system
  - Found: Executed amendment SYN-AMD-0005 covers SYN-PO-0005 and meter assemblies; applicability is determined by the invoice currency schedule, with no currency conversion. Its effective date is 2026-08-01, before the 2026-08-15 delivery. The migrated PO references the superseded version. It identifies an approval-register key.
  - Factor `contract_coverage`: 0.073 → 0.942
  - Action after hop 1: **partial_approve** → (dist: 0.9463)
- **Hop 2:** The apparent unauthorized-change exception is cleared by the scoped approval record.
  - Checked: approval_register
  - Found: The register key identifies approvals by the two roles required by SYN-POL-0005. Both signed on 2026-07-29; the invoice amount of USD 8400.00 is within their documented delegated limit. The approval packet identifies the operative rate-annex key.
  - Factor `policy_conformance`: 0.082 → 0.941
  - Action after hop 2: **partial_approve** → (dist: 0.6951)
- **Hop 3:** The price variance is fully explained by the effective approved amendment.
  - Checked: contract_rate_annex
  - Found: The scoped annex sets USD 168.00 per unit, replacing USD 160.00; 50 units x USD 168.00 = USD 8400.00, exactly the invoice total. No other fee is billed.
  - Factor `price_conformance`: 0.069 → 0.959
  - Action after hop 3: **approve** ✅ (dist: 0.1824)

- Action: **approve** ✅
- Distance to nearest centroid: 0.1824

**Why VLD changed the decision:** Approve USD 8400.00: receipt is documented, the effective amendment applies, approval authority is verified, and its rate exactly reconciles the invoice. All cited records existed before alert arrival. The factor values are planted fixture values, not customer measurements.

**Factor movement:**
| Factor | Surface | Enriched | Δ |
|---|---|---|---|
| amount_materiality | 0.410 | 0.410 | +0.000 |
| contract_coverage | 0.073 | 0.942 | +0.868 ← |
| duplicate_risk | 0.194 | 0.194 | +0.000 |
| policy_conformance | 0.082 | 0.941 | +0.859 ← |
| price_conformance | 0.069 | 0.959 | +0.890 ← |
| receipt_match | 0.639 | 0.639 | +0.000 |
| supplier_trust | 0.610 | 0.610 | +0.000 |

### Case 6: S2P-006-v1
**Type:** planned_partial_delivery
**Kind:** score_keyed | **rho:** 1.0

**Description:** SYN-Cedar Components: a planned split delivery permits payment for 60 of 100 units.

#### WITHOUT VLD (single-pass)
- Action: **escalate_to_procurement** ❌ (ground truth: partial_approve)
- Based on surface factors only
- Distance to nearest centroid: 0.9894

#### WITH VLD (investigation)
- **Hop 1:** The PO supports a legitimate staged obligation; it does not authorize paying the undelivered balance.
  - Checked: purchase_order_schedule
  - Found: SYN-PO-0006 permits two deliveries and separates the current warehouse-specific delivery lot from a future tranche. The schedule explicitly permits payment only for quantities already accepted and identifies receipt register key SYN-GR-0006. The supplier billed all 100 units.
  - Factor `contract_coverage`: 0.084 → 0.494
  - Action after hop 1: **partial_approve** ✅ (dist: 0.8904)
- **Hop 2:** The apparent shortage is the scheduled second tranche; the accepted portion is identified.
  - Checked: goods_receipt_log
  - Found: Scoped receipt SYN-GR-0006 confirms 60 accepted units and 40 units not yet delivered. The acceptance record names the staged-payment policy version. The missing units have not been represented as received.
  - Factor `receipt_match`: 0.082 → 0.691
  - Action after hop 2: **partial_approve** ✅ (dist: 0.6684)
- **Hop 3:** A valid staged-payment rule establishes the permitted partial approval.
  - Checked: payment_policy_register
  - Found: SYN-POL-0006 explicitly allows AP to release the accepted tranche on a single invoice and park its remainder. USD 2400.00 = 60 x USD 40.00 is releasable; USD 1600.00 stays blocked until a later accepted receipt. No advance payment is authorized.
  - Factor `policy_conformance`: 0.090 → 0.695
  - Action after hop 3: **partial_approve** ✅ (dist: 0.1104)

- Action: **partial_approve** ✅
- Distance to nearest centroid: 0.1104

**Why VLD changed the decision:** Partially approve USD 2400.00; retain USD 1600.00 pending the remaining receipt. A blanket dispute would contradict the signed delivery schedule. All cited records existed before alert arrival. The factor values are planted fixture values, not customer measurements.

**Factor movement:**
| Factor | Surface | Enriched | Δ |
|---|---|---|---|
| amount_materiality | 0.591 | 0.591 | +0.000 |
| contract_coverage | 0.084 | 0.494 | +0.410 ← |
| duplicate_risk | 0.194 | 0.194 | +0.000 |
| policy_conformance | 0.090 | 0.695 | +0.605 ← |
| price_conformance | 0.558 | 0.558 | +0.000 |
| receipt_match | 0.082 | 0.691 | +0.609 ← |
| supplier_trust | 0.793 | 0.793 | +0.000 |

### Case 7: S2P-007-v1
**Type:** planned_partial_delivery
**Kind:** score_keyed | **rho:** 0.7

**Description:** SYN-Harbor Industrial: a planned split delivery permits payment for 120 of 200 units.

#### WITHOUT VLD (single-pass)
- Action: **escalate_to_procurement** ❌ (ground truth: partial_approve)
- Based on surface factors only
- Distance to nearest centroid: 0.9814

#### WITH VLD (investigation)
- **Hop 1:** The PO supports a legitimate staged obligation; it does not authorize paying the undelivered balance.
  - Checked: purchase_order_schedule
  - Found: SYN-PO-0007 permits two deliveries and separates the current customer-approved production phase from a future tranche. The schedule explicitly permits payment only for quantities already accepted and identifies receipt register key SYN-GR-0007. The supplier billed all 200 units.
  - Factor `contract_coverage`: 0.072 → 0.504
  - Action after hop 1: **partial_approve** ✅ (dist: 0.8891)
- **Hop 2:** The apparent shortage is the scheduled second tranche; the accepted portion is identified.
  - Checked: goods_receipt_log
  - Found: Scoped receipt SYN-GR-0007 confirms 120 accepted units and 80 units not yet delivered. The acceptance record names the staged-payment policy version. The missing units have not been represented as received.
  - Factor `receipt_match`: 0.086 → 0.689
  - Action after hop 2: **partial_approve** ✅ (dist: 0.6700)
- **Hop 3:** A valid staged-payment rule establishes the permitted partial approval.
  - Checked: payment_policy_register
  - Found: SYN-POL-0007 explicitly allows AP to release the accepted tranche on a single invoice and park its remainder. USD 3000.00 = 120 x USD 25.00 is releasable; USD 2000.00 stays blocked until a later accepted receipt. No advance payment is authorized.
  - Factor `policy_conformance`: 0.089 → 0.701
  - Action after hop 3: **partial_approve** ✅ (dist: 0.1153)

- Action: **partial_approve** ✅
- Distance to nearest centroid: 0.1153

**Why VLD changed the decision:** Partially approve USD 3000.00; retain USD 2000.00 pending the remaining receipt. A blanket dispute would contradict the signed delivery schedule. All cited records existed before alert arrival. The factor values are planted fixture values, not customer measurements.

**Factor movement:**
| Factor | Surface | Enriched | Δ |
|---|---|---|---|
| amount_materiality | 0.605 | 0.605 | +0.000 |
| contract_coverage | 0.072 | 0.504 | +0.432 ← |
| duplicate_risk | 0.206 | 0.206 | +0.000 |
| policy_conformance | 0.089 | 0.701 | +0.611 ← |
| price_conformance | 0.548 | 0.548 | +0.000 |
| receipt_match | 0.086 | 0.689 | +0.603 ← |
| supplier_trust | 0.796 | 0.796 | +0.000 |

### Case 8: S2P-008-v1
**Type:** planned_partial_delivery
**Kind:** score_keyed | **rho:** 0.7

**Description:** SYN-Maple Systems: a planned split delivery permits payment for 48 of 80 units.

#### WITHOUT VLD (single-pass)
- Action: **escalate_to_procurement** ❌ (ground truth: partial_approve)
- Based on surface factors only
- Distance to nearest centroid: 0.9727

#### WITH VLD (investigation)
- **Hop 1:** The PO supports a legitimate staged obligation; it does not authorize paying the undelivered balance.
  - Checked: purchase_order_schedule
  - Found: SYN-PO-0008 permits two deliveries and separates the current serial-number range in the release from a future tranche. The schedule explicitly permits payment only for quantities already accepted and identifies receipt register key SYN-GR-0008. The supplier billed all 80 units.
  - Factor `contract_coverage`: 0.085 → 0.486
  - Action after hop 1: **partial_approve** ✅ (dist: 0.9034)
- **Hop 2:** The apparent shortage is the scheduled second tranche; the accepted portion is identified.
  - Checked: goods_receipt_log
  - Found: Scoped receipt SYN-GR-0008 confirms 48 accepted units and 32 units not yet delivered. The acceptance record names the staged-payment policy version. The missing units have not been represented as received.
  - Factor `receipt_match`: 0.089 → 0.700
  - Action after hop 2: **partial_approve** ✅ (dist: 0.6920)
- **Hop 3:** A valid staged-payment rule establishes the permitted partial approval.
  - Checked: payment_policy_register
  - Found: SYN-POL-0008 explicitly allows AP to release the accepted tranche on a single invoice and park its remainder. USD 3600.00 = 48 x USD 75.00 is releasable; USD 2400.00 stays blocked until a later accepted receipt. No advance payment is authorized.
  - Factor `policy_conformance`: 0.070 → 0.692
  - Action after hop 3: **partial_approve** ✅ (dist: 0.1312)

- Action: **partial_approve** ✅
- Distance to nearest centroid: 0.1312

**Why VLD changed the decision:** Partially approve USD 3600.00; retain USD 2400.00 pending the remaining receipt. A blanket dispute would contradict the signed delivery schedule. All cited records existed before alert arrival. The factor values are planted fixture values, not customer measurements.

**Factor movement:**
| Factor | Surface | Enriched | Δ |
|---|---|---|---|
| amount_materiality | 0.612 | 0.612 | +0.000 |
| contract_coverage | 0.085 | 0.486 | +0.401 ← |
| duplicate_risk | 0.189 | 0.189 | +0.000 |
| policy_conformance | 0.070 | 0.692 | +0.623 ← |
| price_conformance | 0.547 | 0.547 | +0.000 |
| receipt_match | 0.089 | 0.700 | +0.611 ← |
| supplier_trust | 0.787 | 0.787 | +0.000 |
