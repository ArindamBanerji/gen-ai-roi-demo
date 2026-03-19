# Coding Guidelines & Prompt Engineering Guide
## Compounding Intelligence Platform
## For Use with Claude Code Sonnet + OpenAI Codex

**Version:** 1.0 · March 13, 2026
**Purpose:** Distilled from 29 completed v5.0 prompts, 7 VIS-2 bug investigations, 5 sprint
phases of design, and explicit LLM judge findings. Every rule here was either validated by
experience or created to prevent a class of bug we actually hit.
**Scope:** Both AI coding agents (Claude Code Sonnet and OpenAI Codex), all repos
(GAE, SOC Copilot, cross-graph-experiments, ci-platform), and all session types
(code, experiment, design doc).

---

## Part 0: Agent Selection — When to Use Which Tool

This decision is irreversible within a session. Do not switch mid-session.

| Task Type | Agent | Reason |
|---|---|---|
| Implementation — all v5.5/v6.0 sprint prompts | **Claude Code Sonnet** | Follows multi-step design specs; handles large context (design docs + test files + target files simultaneously); produces consistent code across long sessions |
| Experiment scripts — PROD-3/4, GATE-R, EXP-S* | **Claude Code Sonnet** | Needs to read existing experiment scaffolding patterns and maintain consistency |
| Architecture review, design critique | **Claude (Opus, in chat)** | Reasoning-intensive; not a coding task |
| Isolated, self-contained utility components | **Codex** | Fast for bounded tasks with complete context; no design doc dependency |
| Performance-sensitive inner loops (if profiling shows need) | **Codex** | Good at tight Python/NumPy implementations |
| Any task requiring reading + understanding design docs | **Claude Code Sonnet** | Codex does not maintain design doc context across file reads reliably |
| React/TypeScript frontend changes | **Claude Code Sonnet** | Better at TypeScript generics, React hooks, and state management patterns used in this codebase |

**Hard rule: Never run Claude Code and Codex in the same repo in the same session.**
If you used Claude Code for a GAE task this session, do not switch to Codex for the
SOC task. Start a new session. Mixing produces conflicting assumptions about state.

---

## Part 1: Universal Prompt Structure

Every prompt — regardless of agent or repo — follows the same skeleton.
Deviation from this structure is the primary cause of scope creep and incomplete work.

### 1.1 The Five-Section Prompt Template

```
[SECTION 1: HEADER — 4 fields, always present]
Repo: <soc-copilot | graph-attention-engine | cross-graph-experiments | ci-platform>
Design spec: <document name §section>
Constraints block: <paste the universal constraints for this repo — see Part 2>
Prerequisites verified: <list what must be true before this prompt runs>

[SECTION 2: READ FIRST — before writing any code]
List every file to read, in order. For each file:
  - Full path relative to repo root
  - What specifically to look for (function name, class name, constant)
  - What question to answer before writing (e.g., "Does bootstrap write DecisionRecords? 
    Expected: NO — verify")

[SECTION 3: CREATE / MODIFY — explicit change list]
Number every change. For each change:
  - Action: CREATE | MODIFY | DELETE | RENAME
  - Target: exact file path
  - What: precise description of what to add/change/remove
  - Why: one sentence connecting to the design spec or bug being fixed
  - Shape/type contract (if applicable): exact types, shapes, return values

[SECTION 4: TESTS — mandatory for every prompt]
New file or existing file to modify.
List each test by name as: test_<what>_<expected_behavior>()
Include at minimum:
  - Happy path test
  - Boundary/edge case test  
  - Error/failure test (what happens when something is wrong, not absent)
Run command: pytest <path> -v

[SECTION 5: ACCEPTANCE CRITERION — single verifiable statement]
A binary condition that is checked LAST, after all tests pass.
One of:
  - "Zero <ERROR_LOG_PATTERN> log lines during a 50-decision simulation run"
  - "pytest tests/ passes with N tests passing (was N-K before this prompt)"
  - "GET <endpoint> returns <exact shape> confirmed via curl"
  - "Visual: <tab> shows <specific element> with <specific data>"
Never: "looks good" / "seems to work" / "tests pass" (too vague)
```

### 1.2 Why Each Section Matters

**READ FIRST** prevents the most common class of bug: writing code that contradicts
existing code. In this codebase specifically: IKS was written as a class in the design
doc but was already implemented as module-level functions. A prompt that skipped READ
FIRST would have instantiated a class that didn't exist.

**Numbered change list** prevents scope creep. Each number is a transaction: if it
can be removed without breaking the others, it should be a separate prompt. The VIS-2
session found 7 bugs by working through the change list one item at a time rather than
shipping everything and debugging the resulting state.

**Explicit test names** force the agent to think about failure modes before writing
production code. Agents that write tests after code tend to write tests that confirm
the implementation rather than test the specification.

**Single acceptance criterion** prevents the completion illusion: a session that ends
with "tests pass but the UI still shows 'cat_0'" has not met its goal. The acceptance
criterion is the contract.

---

## Part 2: Constraints Blocks — Copy-Paste for Each Repo

These blocks go into Section 1 of every prompt for the named repo.
Do not abbreviate them. An agent that doesn't see these constraints will violate them.

### 2.1 GAE Constraints Block

```
CONSTRAINTS — GAE REPO:
- Zero SOC-specific code in any gae/ file. Domain config via protocol only.
- ProfileScorer IS the scoring mechanism. ScoringMatrix is DEPRECATED (TD-029).
- All τ defaults = 0.1 (V3B validated, ECE=0.036). Never use 0.25. Never override without
  explicit experiment result justifying the change.
- All centroid updates MUST clip to [0.0, 1.0] after every update. V2 validated — without
  clipping, centroids escape to 4,608× norms by decision 200.
- ProfileScorer.update() has NO synthesis parameter. σ NEVER flows into update().
  Loop 4 / σ is PROPOSAL — gated by EXP-S1–S8. Never add σ to update().
- numpy-only for gae/ core. No scipy, no sklearn, no external ML deps.
- Type hints everywhere. Python 3.11+. mypy --strict must pass.
- Public API (everything in gae/__init__.py) must remain backward-compatible within 0.x.
- Do NOT use git. User handles all git operations.
- Do NOT start the debugger. Log-based debugging only.
- Run pytest tests/ before declaring done. Count must be ≥ current count (246 as of v5.0 post-WIRING-1).
```

### 2.2 SOC Copilot Constraints Block

```
CONSTRAINTS — SOC REPO:
- Repo boundary is absolute: this session modifies SOC files only.
  GAE is an imported library — interact only via: 
    from gae.profile_scorer import ProfileScorer, build_profile_scorer
    from gae.hooks import DecisionRecord, OutcomeRecord, ProfileSnapshot
  Never modify any file under a gae/ directory.
  
- IKS service is module-level functions, NOT a class:
    from app.services.iks import compute_iks, interpret
  Never write: iks_service = IKSService() — this class does not exist.
  
- centroid-evolution endpoint returns flat array [], NOT {evolution: []}
  Frontend state must be: useState<CentroidEvolutionEntry[]>([])
  Assigning to {evolution: []} shape will cause a crash in Tab-2 and Tab-4.
  
- ProfileScorer shape: (C=5, A=5, d=6). Never hardcode A=4. A=5 includes refer_to_analyst.
  Categories (C=5, ORDER IS PERMANENT):
    0: credential_access  1: lateral_movement  2: insider_threat
    3: data_exfiltration  4: cloud_infrastructure
  
- SOC_FACTORS is defined in config.py and is the single source of truth for factor names.
  Never fork SOC_FACTORS. Never create a parallel factors list in another file.
  Canonical factor name: threat_intel_enrichment (NOT threat_intel — the shorter name
  will silently produce wrong factor lookups).
  
- Mandatory data hooks — skip any of these and GATE-R, IKS, and TD-033 rollback break:
    DecisionRecord on EVERY score() call (including shadow mode)
    OutcomeRecord on EVERY update() call
    ProfileSnapshot EVERY 50 decisions AND on every operator start
    
- Language: "product" not "demo" in all comments, docstrings, and UI text.
  
- EvaluationReport.by_category — never by_technique (that field was renamed; using
  the old name silently returns None in Python, causing invisible accuracy failures).
  
- confidence floor for refer_to_analyst = 0.70 IS A DESIGN ESTIMATE, labeled as such.
  Do not treat it as a validated constant until PROD-4 runs.
  
- τ = 0.1 in all configs. This was calibrated on synthetic data (V3B, ECE=0.036).
  Before first customer deployment: recalibrate on real alerts. Do not lock τ at 0.1
  for production without a recalibration experiment.
  
- PowerShell environment: no backslash line continuation. Use separate git add commands.
  
- Do NOT use git. User handles all git operations.
- Do NOT start the debugger. Log-based debugging only.
- Run pytest tests/ before declaring done. Count must be ≥ 78 (v5.0 baseline).
```

### 2.3 cross-graph-experiments Constraints Block

```
CONSTRAINTS — EXPERIMENTS REPO:
- Regime discipline: every result must state which regime it belongs to.
  CENTROIDAL (synthetic, GT profiles, oracle routing): 97.89% / 98.2%
  REALISTIC 50-SEED (power-law users, Bernoulli oracle, realistic noise): 71.7% / 78.9%
  Never mix regime numbers in the same sentence without labeling both.
  
- Statistical reporting minimum: all accuracy numbers must include 95% bootstrap CI.
  Format: mean [CI_low, CI_high] (N seeds). Never report a single point estimate.
  
- T_recovery reporting: survival curves and Kaplan-Meier fractions only.
  Never use mean ± std for recovery time (distribution is right-skewed and bimodal;
  mean ± std is statistically wrong and will be challenged).
  
- Gate pass/fail is binary and pre-declared. Never adjust the gate threshold after
  seeing the result. If the threshold needs to change, document the reasoning and
  get design approval before re-running.
  
- GATE-M requires ALL FOUR conditions: EXP-S2-REPRO (all arms), EXP-S1 (Δ≥3pp,
  p<0.0083), EXP-S3 (≤5% divergence), EXP-S4 (λ plateau ≥0.05 wide).
  One failure → σ display-only, not live in scoring pipeline. No partial gates.
  
- σ_max = q10 of empirical L2 margin distribution (from FX-1-PROXY-REAL).
  Do NOT use σ_max=1.0 placeholder in any experiment that depends on σ injection.
  
- Do NOT use git. User handles all git operations.
- Output all results to paper_figures/ (PNG + PDF) and results/summary.json.
- Every experiment script must be reproducible: fixed random seed, documented parameters.
```

---

## Part 3: The Bugs We Actually Hit — Anti-Pattern Catalogue

These are real bugs from the v5.0 sprint and VIS-2 visual validation session.
Each entry is a pattern to recognize and avoid.

### 3.1 Shape Contract Violations

**Bug:** Frontend expected `{evolution: []}`, backend returned `[]`.
**Result:** Tab-2 and Tab-4 crashed. 15 references required fixing.
**Root cause:** The endpoint was designed in chat as returning `{evolution: []}` but
the implementation returned a flat array. Neither was wrong at the time of writing —
the contract was ambiguous.

**Prevention pattern — always specify shape in the prompt:**
```
# In Section 3 (MODIFY), for every endpoint:
# Return type: EXACTLY flat array [] of CentroidEvolutionEntry objects.
# NOT {evolution: []}, NOT {data: []}, NOT {items: []}.
# Frontend useState: useState<CentroidEvolutionEntry[]>([])
# If the frontend has useState<{evolution: CentroidEvolutionEntry[]}>, that is WRONG.
# Fix it as part of this prompt.
```

**Test pattern:**
```python
def test_centroid_evolution_returns_flat_array():
    resp = client.get("/api/soc/centroid-evolution")
    data = resp.json()
    assert isinstance(data, list), f"Expected list, got {type(data)}"
    # NOT: assert "evolution" in data
```

---

### 3.2 The Silent Default / Fallback Bug

**Bug:** Alert type → category mapping had ~30 entries out of ~200+ needed.
Unrecognized alert types silently routed to a default category. No error logged.
**Result:** ~20% of alerts misrouted. GATE-R cannot run. Accuracy numbers are wrong.
**Root cause:** The code had `category = mapping.get(alert_type, "credential_access")`
with no logging. The bug was invisible during development.

**Prevention pattern — make silent defaults loud:**
```python
# WRONG:
category = mapping.get(alert_type, "credential_access")

# RIGHT:
category = mapping.get(alert_type)
if category is None:
    logger.error(
        f"ROUTING_FAILURE: alert_type='{alert_type}' has no mapping. "
        f"Using fallback '{DEFAULT_CATEGORY}'. Add to ALERT_TYPE_CATEGORY_MAP."
    )
    category = DEFAULT_CATEGORY
```

**In prompt Section 4, always include:**
```
- test_unrecognized_alert_type_emits_error_log():
    Pass "completely_unknown_type_xyz" → assert logger.error was called
    assert "ROUTING_FAILURE" in captured log output
- test_zero_routing_failures_in_simulation():
    Run 50 decisions → assert no "ROUTING_FAILURE" in log
```

---

### 3.3 The Scattered Literal Anti-Pattern

**Bug:** `ALERT-7823` appeared as a hardcoded literal in 3+ files.
**Result:** Any refactor broke one but not all occurrences. The displayed alert ID
was stale when the underlying data changed.

**Prevention pattern — centralize every configurable literal:**
```typescript
// WRONG: alert_id = "ALERT-7823" in triage.py AND RuntimeEvolutionTab.tsx

// RIGHT: One canonical location
// frontend/src/domain.ts:
export const DEFAULT_ALERT_ID = 'ALERT-7823';
export const CANONICAL_CATEGORIES = [
    'credential_access', 'lateral_movement', 'insider_threat',
    'data_exfiltration', 'cloud_infrastructure'
] as const;

// All other files import from domain.ts
// import { DEFAULT_ALERT_ID } from '../domain';
```

**In the prompt:**
```
Step 0 (always): Before modifying any logic, grep for the literal being changed.
    grep -rn "ALERT-7823" frontend/src/
    grep -rn "ALERT-7823" backend/app/
All occurrences must be replaced by the constant in the same prompt.
```

---

### 3.4 The Design-Document-as-Class Bug

**Bug:** The design doc for IKS described an `IKSService` class.
The implementation used module-level functions.
**Result:** The next session's prompt instantiated `IKSService()` — class does not exist.
Import succeeded (the module existed), instantiation failed at runtime. Error only
visible on first IKS-triggered API call.

**Prevention pattern — READ FIRST is not optional:**
```
# Section 2 of every prompt that touches an existing service:
READ FIRST:
  backend/app/services/iks.py
  Question: Is IKS a class or module-level functions?
  If class: use IKSService()
  If module-level: use from app.services.iks import compute_iks, interpret
  
  The design doc (soc_copilot_design_v5_4 §22.3) says "class".
  The implementation is module-level functions. 
  The IMPLEMENTATION is authoritative. Fix §22.3 if there is a discrepancy.
```

**General rule:** When design doc and code disagree, the code is the truth.
Update the design doc, not the code (unless the code has the bug).

---

### 3.5 The ID Mismatch Bug

**Bug:** Tab-3 stored a UUID in sessionStorage when submitting triage feedback.
Tab-2's Section A queried `centroid-evolution` which returned `DEC-XXXX` formatted IDs.
UUID and DEC-XXXX never matched.
**Result:** Section A always showed "no matching decision" even after a real outcome.

**Root cause:** Two parts of the UI used different ID schemas for the same entity.
No test connected the two.

**Prevention pattern — cross-component ID contracts:**
```
# In Section 3 of any prompt that creates or reads IDs across components:
ID contract (must be explicit):
  Written by: Tab-3 triage submission → stores in sessionStorage as: <id format>
  Read by: Tab-2 Section A → reads from centroid-evolution as: <id format>
  These MUST be the same format. If they differ, add an id field to the source
  type that uses the canonical format and update all consumers in this prompt.

# Option A pattern (add canonical id to the response):
class CentroidEvolutionEntry(BaseModel):
    id: str          # DEC-XXXX — this is the match key
    uuid: str        # internal UUID — do not use as match key
    # ... other fields

# Frontend stores and matches on `id`, not `uuid`.
```

---

### 3.6 The Category Name Bug

**Bug:** `ProfileScorer` was constructed without passing `categories=` argument.
**Result:** Internal category names defaulted to `cat_0`, `cat_1`, etc.
UI showed `cat_0` instead of `credential_access` everywhere.

**Root cause:** The default was valid Python; nothing raised an error.
The wrong display name propagated through every API response silently.

**Prevention pattern — always verify constructor kwargs:**
```python
# WRONG (uses default cat_0, cat_1, ... naming):
scorer = ProfileScorer(n_cat=5, n_act=5, d=6, tau=0.1)

# RIGHT (uses canonical names):
scorer = ProfileScorer(
    n_cat=5, n_act=5, d=6, tau=0.1,
    categories=list(SOC_CATEGORIES),   # from config.py — the single source of truth
    actions=list(SOC_ACTIONS),
)

# Test: always assert category names in any test that touches the scorer:
def test_scorer_uses_canonical_category_names():
    assert scorer.categories[0] == "credential_access"
    assert "cat_0" not in scorer.categories
```

---

### 3.7 The Double Prefix Bug

**Bug:** Tab-4 Recent Evolution Events displayed `DEC-DEC-XXXX`.
**Root cause:** The `id` field in the Evolution node already contained `DEC-XXXX`.
The frontend prepended `DEC-` again: `const displayId = 'DEC-' + entry.id`.

**Prevention pattern — never prefix IDs in display code:**
```typescript
// WRONG:
const displayId = `DEC-${entry.id}`;   // entry.id is already "DEC-7823"

// RIGHT:
const displayId = entry.id;             // trust the source

// Or, if you need to normalize:
const displayId = entry.id.startsWith('DEC-') ? entry.id : `DEC-${entry.id}`;
```

**General rule:** Display IDs verbatim from the API. Only prefix/transform at the
write end (where the ID is created), not the read end (where it is displayed).

---

### 3.8 The CSS Invisible Element Bug

**Bug:** Bridge link pill was styled with `text-xs text-purple-300` on a near-transparent
background. Visible in Tailwind's dark mode previews but effectively invisible
against the actual background color.

**Prevention pattern — specify visual acceptance in the prompt:**
```
Section 5 (ACCEPTANCE): Visual check required.
The bridge link pill must be VISIBLE against its background:
- Minimum contrast: solid border, non-transparent background, at minimum sm text
- Correct style: bg-purple-900/40 border border-purple-500/60 text-purple-200 text-sm
  (not text-xs — too small for inline elements)
- Test: screenshot or live inspection. "Element exists in DOM" is NOT sufficient.
  The element must be readable at normal monitor zoom (100%).
```

---

### 3.9 The Nullish Coalescing vs. OR Bug

**Bug:** Bridge link ID check used `||` (OR operator).
`const decisionId = sessionStorage.getItem('lastDecisionId') || null`
Empty string `""` is falsy, so a valid (empty) session value was treated as absent.

**Prevention pattern:**
```typescript
// WRONG for optional values that may be legitimately empty:
const decisionId = sessionStorage.getItem('lastDecisionId') || null;
// "" || null → null (loses the value)

// RIGHT — use nullish coalescing for optional values:
const decisionId = sessionStorage.getItem('lastDecisionId') ?? null;
// "" ?? null → "" (preserves the value)

// Rule: || is for falsy coalescing (treat 0, "", false as absent)
//       ?? is for nullish coalescing (only treat null, undefined as absent)
// For IDs, timestamps, and strings from storage: always use ??
```

---

## Part 4: Prompt Writing Patterns That Work

### 4.1 The "Read First, State What You Found" Pattern

Before writing any production code, require the agent to state what it found:

```
READ FIRST and REPORT:
  1. Open backend/app/services/iks.py
     State: Is IKS implemented as a class or as module-level functions?
     State: What are the exact function signatures (names + parameters)?
  
  2. Open backend/app/config/soc_domain_config.py
     State: How many entries are in get_alert_category_mapping()?
     State: Is there a silent default? (look for mapping.get(key, default))

Do NOT write any code until you have stated these findings.
If the findings contradict this prompt's assumptions, state the contradiction
before proceeding. The contradiction takes priority over the plan.
```

This pattern catches the most common class of bug: writing code that contradicts
existing code because the agent assumed rather than verified.

---

### 4.2 The "Explicit Non-Goal" Pattern

Every prompt should state what it does NOT do, to prevent scope creep:

```
THIS PROMPT DOES NOT:
- Fix the DEC-DEC- double prefix in Tab-4 (TD-034 — deferred to v5.5)
- Implement the NL template engine (Phase 2, separate prompt)
- Modify any GAE files (repo boundary — separate prompt in GAE session)
- Change the confidence threshold (design estimate pending PROD-4)

If you find a related bug while working, add a TODO comment with the TD number
and move on. Do not fix it in this prompt.
```

Without explicit non-goals, agents tend to "fix nearby things" which creates
unreviewed changes, breaks the acceptance criterion, and makes the git diff unreadable.

---

### 4.3 The "Contract at the Boundary" Pattern

For every interaction between two components (API endpoint ↔ frontend, service ↔ service),
the prompt must state the exact contract at that boundary:

```
API CONTRACT (must be exact — changes here require changes in all consumers):
  Endpoint: GET /api/soc/centroid-evolution
  Response type: List[CentroidEvolutionEntry]   # flat array, not wrapped
  CentroidEvolutionEntry fields:
    id: str          # "DEC-XXXX" — canonical match key
    category: str    # "credential_access" (not "cat_0")
    action: str      # "escalate" (not "action_0")
    delta_norm: float
    outcome: str     # "correct" | "incorrect"
    timestamp: str   # ISO 8601

SERVICE CONTRACT (IKS module):
  compute_iks(centroids: np.ndarray, mu0: np.ndarray, n_decisions: int) -> float
  interpret(iks_score: float) -> str
  # No class. No instantiation. Direct function calls only.
```

---

### 4.4 The "Failure Mode First" Test Pattern

Write the failure test before the happy path test. If you can't write the failure test,
you don't understand the failure mode:

```python
# Pattern: write failure tests first, they drive the implementation

# Failure tests (write first):
def test_routing_failure_logs_error_for_unknown_type():
    """Unknown alert_type must log an ERROR — never silently default."""
    with pytest.raises(AssertionError) or caplog check:
        result = route_alert("totally_unknown_type_xyz")
    assert "ROUTING_FAILURE" in caplog.text
    assert result == DEFAULT_CATEGORY   # fails gracefully, but loudly

def test_centroid_update_clips_to_unit_interval():
    """Centroid values MUST stay in [0.0, 1.0] even with adversarial inputs."""
    scorer = build_test_scorer()
    scorer.update(f=np.array([2.0, -1.0, 3.0, 0.5, 0.5, 0.5]), c=0, a=0, correct=True)
    assert np.all(scorer.centroids >= 0.0)
    assert np.all(scorer.centroids <= 1.0)

# Happy path tests (write second, after failure tests are green):
def test_routing_maps_brute_force_login_to_credential_access():
    assert route_alert("brute_force_login") == "credential_access"
```

---

### 4.5 The "Verify, Don't Assume" Endpoint Test Pattern

For FastAPI endpoints, always test the actual response shape, not just status code:

```python
def test_centroid_evolution_response_shape():
    """Shape contract: flat array, not wrapped object."""
    response = client.get("/api/soc/centroid-evolution")
    assert response.status_code == 200
    
    data = response.json()
    
    # Shape contract
    assert isinstance(data, list), (
        f"centroid-evolution must return list, got {type(data)}. "
        f"If wrapped in {{evolution: []}}, all frontend consumers will crash."
    )
    
    # Field contract (if data is non-empty)
    if len(data) > 0:
        entry = data[0]
        assert "id" in entry, "Missing 'id' field — frontend UUID/DEC mismatch will occur"
        assert "category" in entry
        assert entry["category"] != "cat_0", (
            "category='cat_0' means ProfileScorer was built without categories= arg"
        )
        assert not entry["id"].startswith("DEC-DEC-"), "Double DEC- prefix detected"
```

---

### 4.6 The Codex-Specific Prompt Pattern

Codex works best with complete, self-contained prompts. Unlike Claude Code, it does
not maintain context across file reads well. Structure Codex prompts as:

```
[CODEX PROMPT STRUCTURE]

Context (paste inline — do not assume Codex will read files):
"""
<paste the relevant function/class here — 50-100 lines max>
"""

Task: <single, bounded transformation of the above code>

Constraints:
- <constraint 1>
- <constraint 2>

Return only the modified function/class. No explanation. No imports unless new ones needed.

Test that must pass:
def test_<name>():
    <paste the test inline>
```

**Codex anti-patterns:**
- "Read file X and modify it" — Codex doesn't reliably read files; paste the content
- "Fix the bug in the routing module" — too vague; paste the specific function
- "Implement the IKS service per the design doc" — Codex doesn't read design docs;
  paste the spec inline
- Any task requiring understanding of more than 2-3 existing files

**When to stop using Codex and switch to Claude Code:**
- The task requires reading more than 3 files to understand context
- The output requires modifying more than 2 files
- The task involves TypeScript generics or complex React patterns
- The task has a design doc dependency

---

## Part 5: Architecture-Specific Prompt Rules

### 5.1 The Three-Repo Stack Rule

The dependency direction is absolute and flows one way:

```
soc-copilot          ← imports from ↓
ci-platform          ← imports from ↓
graph-attention-engine

RULE: Higher layers import from lower layers. Never the reverse.
IMPLEMENTATION: Each Claude Code session touches exactly ONE repo.
                Cross-repo changes are sequenced across sessions.

For any prompt that requires changes in two repos:
  Session 1: GAE change (e.g., add CentroidUpdate return type)
  User commits Session 1 to git
  Session 2: SOC change (e.g., wire centroid_delta_norm from CentroidUpdate)

Never attempt both in one session. The git boundary IS the session boundary.
```

### 5.2 The IKS Module Pattern (Never a Class)

```python
# iks.py — module-level functions only
# This is NOT an accident. It is canonical design.

def compute_iks(
    centroids: np.ndarray,      # shape: (C, A, d)
    mu0: np.ndarray,            # shape: (C, A, d) — from iks_bootstrap_soc.json
    n_decisions: int,
) -> float:
    """Institutional Knowledge Score: normalized Frobenius distance from μ₀."""
    ...

def interpret(iks_score: float) -> str:
    """Human-readable interpretation of an IKS value."""
    ...

# CORRECT usage:
from app.services.iks import compute_iks, interpret
score = compute_iks(scorer.centroids, mu0, n_decisions)

# WRONG — this class does not exist:
iks_service = IKSService()  # ImportError or AttributeError
score = iks_service.compute(...)
```

**μ₀ sidecar (iks_bootstrap_soc.json):**
The reference point for IKS drift measurement. Written once by `write_mu_zero_sidecar.py`
after bootstrap completes. Shape: `[C, A, d]` = `[6, 4, 6]` (note: shape reflects the
post-bootstrap tensor including healthcare category from simulation).
**Do not delete, move, or regenerate this file without running bootstrap.py again.**
Every `compute_iks()` call reads this file. If the path changes, update the IKS service.

### 5.3 The ProfileScorer Instantiation Rule

```python
# ALWAYS pass categories= and actions= to ProfileScorer.
# Without them, category names default to cat_0, cat_1, ... which is wrong.

# WRONG — produces cat_0, cat_1, ... in all API responses:
scorer = ProfileScorer(n_cat=5, n_act=5, d=6, tau=0.1)

# RIGHT:
from app.config.soc_domain_config import SOC_CATEGORIES, SOC_ACTIONS
scorer = ProfileScorer(
    n_cat=5, n_act=5, d=6, tau=0.1,
    categories=list(SOC_CATEGORIES),
    actions=list(SOC_ACTIONS),
)

# The SOC_CATEGORIES and SOC_ACTIONS constants live in config.py.
# They are the single source of truth.
# Never define them inline in the scorer construction.
```

### 5.4 The Hook Obligation Pattern

These three hooks are data contracts, not optional logging. If any is missing,
downstream features (IKS, GATE-R, TD-033 rollback) break silently:

```python
# Pattern for every score() call:
def score_alert(alert: Alert, ...) -> JudgmentResult:
    result = scorer.score(f=factor_vector, c=category_index)
    
    # HOOK 1: mandatory, every score() call
    decision_record = DecisionRecord(
        id=generate_dec_id(),
        alert_id=alert.id,
        factor_vector=factor_vector.tolist(),
        category=category_name,           # string, not index
        recommended_action=result.action,
        confidence=result.confidence,
        source="operational",             # or "shadow" | "bootstrap" | "simulation"
        shadow_mode=is_shadow_mode,
        timestamp=datetime.utcnow().isoformat(),
    )
    neo4j_session.write_decision_record(decision_record)
    
    return result

# Pattern for every update() call:
def record_outcome(decision_id: str, analyst_action: str, ...) -> CentroidUpdate:
    update = scorer.update(f=factor_vector, c=category_index, a=analyst_index, 
                           correct=(analyst_action == recommended_action))
    
    # HOOK 2: mandatory, every update() call
    outcome_record = OutcomeRecord(
        decision_id=decision_id,
        analyst_action=analyst_action,
        outcome_correct=update.outcome == "correct",
        centroid_delta_norm=update.delta_norm,
        timestamp=datetime.utcnow().isoformat(),
    )
    neo4j_session.write_outcome_record(outcome_record)
    
    # HOOK 3: conditional, every 50 decisions
    if decision_count % 50 == 0:
        snapshot = ProfileSnapshot(
            decision_count=decision_count,
            centroids=scorer.centroids.tolist(),
            timestamp=datetime.utcnow().isoformat(),
        )
        neo4j_session.write_profile_snapshot(snapshot)
    
    return update
```

---

## Part 6: Session Management Rules

### 6.1 Session Start Protocol

```
Before writing any code in a new session:
1. Run: pytest tests/ -q
   Record the count. This is the floor — no regressions allowed.
   
2. Check: git status
   No uncommitted changes from a previous session should be present.
   If there are: understand them before proceeding.
   
3. Read: the acceptance criterion from the previous session's prompt.
   Was it actually verified? If not, verify it now before starting new work.
   
4. Check: the master execution state table (project_status_and_plan_v3_part1 §4.4)
   Find the first incomplete row. That's the starting point.
   Do not skip rows.
```

### 6.2 Session End Protocol

```
Before ending any session:
1. Run: pytest tests/ -q
   Confirm count ≥ session start count.
   
2. Verify the acceptance criterion from this session's prompt.
   Binary: pass or fail. If fail, fix it before ending the session.
   
3. Update the master execution state table:
   Mark completed items ✅ with date.
   Add any new known gaps found during the session.
   
4. If any new bugs were found but not fixed:
   Add them to the tech debt table with ID, severity, and target version.
   Do NOT silently defer without documenting.
   
5. Update session_log_v55.md with:
   - What was built/changed
   - What tests were run (count before → count after)
   - What was found but deferred (with TD number)
   - First action for next session
```

### 6.3 The "One Concern Per Prompt" Rule in Practice

**Wrong decomposition (two concerns in one prompt):**
```
Task: Fix alert routing (G-L1-1) AND add bootstrap DecisionRecords (G-L2-3)
```

**Right decomposition (each prompt is one concern):**
```
Prompt CORR-1: Fix alert routing (G-L1-1)
  → Acceptance: Zero ROUTING_FAILURE log lines in 50-decision run

Prompt CORR-2: Add bootstrap DecisionRecords (G-L2-3)
  → Acceptance: 1,200 DecisionRecord nodes with source='bootstrap' in Neo4j after reset
```

Why this matters: CORR-1 might fail. If CORR-1 and CORR-2 are in the same prompt,
you can't tell which change caused the failure. The git diff is unreadable. The
acceptance criterion is ambiguous. Roll-back requires reverting both changes.

**Rule of thumb for decomposition:**
A prompt is too large if: the acceptance criterion has an AND in it.
Split at the AND.

---

## Part 7: Experiment Prompt Patterns

Experiments have different structure than code prompts. The key difference:
experiments must declare gates before running, not after seeing results.

### 7.1 Experiment Prompt Structure

```
[EXPERIMENT PROMPT STRUCTURE]

EXPERIMENT: <ID> — <Name>
Repo: cross-graph-experiments
Location: experiments/<path>/

READ FIRST:
  <reference implementation files or prior experiment for scaffolding>
  
SETUP:
  Parameters (all fixed before running):
    N_seeds: <number>
    N_decisions: <number>
    tau: 0.1     # always — never use 0.25
    noise_rate: <number>
    <other parameters>
  Random seed: <fixed integer>
  
GATE (declare before running):
  Pass condition: <precise binary criterion>
  Fail condition: <what happens if it fails>
  Do NOT adjust the pass condition after seeing results.
  If the pass condition needs changing: document why and get sign-off first.
  
OUTPUTS (required):
  paper_figures/<experiment_id>_<description>.png (+ .pdf)
  results/summary.json with fields:
    { "mean": float, "ci_low": float, "ci_high": float,
      "n_seeds": int, "gate_verdict": "PASS" | "FAIL",
      "regime": "centroidal_synthetic" | "realistic_50_seed" }
  
STATISTICAL REQUIREMENTS:
  - Bootstrap CI: N=1000 bootstrap samples, α=0.05
  - Report format: mean [CI_low, CI_high] (N seeds)
  - T_recovery (if applicable): median, IQR, Kaplan-Meier survival curve,
    fraction unrecovered at horizon. NOT mean ± std.
  
ACCEPTANCE:
  summary.json exists with gate_verdict field.
  paper_figures/ contains at minimum: <list the specific charts>.
  All figures have axis labels, legend, and title.
```

### 7.2 The Regime Label Rule in Experiments

Every table, chart title, and summary.json in an experiment must carry the regime label:

```python
# summary.json — always include regime:
results = {
    "mean_accuracy": 97.89,
    "ci_low": 97.45,
    "ci_high": 98.23,
    "n_seeds": 50,
    "regime": "centroidal_synthetic",   # NEVER omit this field
    "gate_verdict": "PASS",
}

# Chart titles — always include regime:
plt.title(
    f"L2 vs Dot Product Accuracy\n"
    f"(Centroidal synthetic regime, {N_seeds} seeds)"   # regime in title
)

# Log output — always label:
print(f"Accuracy: {mean:.2f}% [{ci_low:.2f}%, {ci_high:.2f}%]"
      f" — CENTROIDAL SYNTHETIC (not production estimate)")
```

---

## Part 8: The Claims Discipline in Code

The claims discipline that governs external communications also applies inside code.
Some bugs in this project came from code that made false implicit claims.

### 8.1 No Implicit Accuracy Claims in Code

```python
# WRONG — this comment makes a false claim (97.89% is centroidal, not production):
# This scorer achieves 97.89% accuracy on alert triage
scorer = ProfileScorer(...)

# RIGHT — accurate qualifier in any accuracy-related comment:
# Centroidal synthetic accuracy: 97.89% (EXP-C1)
# Realistic 50-seed accuracy: 71.7% baseline → 78.9% at 1,000 decisions
# Production accuracy: unknown until FX-1 (real SOC data)
scorer = ProfileScorer(...)
```

### 8.2 Placeholder vs. Validated Constants

```python
# Every placeholder constant must be labeled as such:

# WRONG:
CONFIDENCE_FLOOR_REFER = 0.70

# RIGHT:
CONFIDENCE_FLOOR_REFER = 0.70  # DESIGN ESTIMATE — pending PROD-4 calibration.
                                # Do not treat as validated until PROD-4 runs.
                                # Replace with per-category threshold table from PROD-4.

SIGMA_MAX = 1.0  # PLACEHOLDER — replace with q10 of L2 margin distribution
                 # from FX-1-PROXY-REAL experiment. Using 1.0 is unsafe for
                 # production σ injection.
```

### 8.3 The "Forbidden Until Gate" Pattern

```python
# σ activation is gated by GATE-M. Code that ships before GATE-M passes
# must enforce λ=0 structurally, not just by configuration:

def score(self, f: np.ndarray, c: int, sigma: Optional[float] = None) -> ScoringResult:
    if sigma is not None and not GATE_M_PASSED:
        # This is not a warning. This is an error.
        # GATE-M has not passed. σ must not influence scoring.
        logger.error(
            "GATE_M_VIOLATION: σ passed to score() before GATE-M has passed. "
            "σ ignored. Set lambda=0 or wait for GATE-M. "
            "See operator_framework_v2_post_judge §III for operative window."
        )
        sigma = None  # enforce λ=0
    ...
```

---

## Quick Reference Card

```
┌─────────────────────────────────────────────────────────────────────┐
│ BEFORE EVERY PROMPT                                                   │
│ □ pytest tests/ → record count                                        │
│ □ Read Section 2 (READ FIRST) before writing any code                 │
│ □ State what you found before proceeding                              │
│ □ Check master execution state table §4.4                             │
├─────────────────────────────────────────────────────────────────────┤
│ CONSTRAINTS CHECKLIST (SOC REPO)                                      │
│ □ IKS: module-level functions, not a class                            │
│ □ centroid-evolution: flat array [], not {evolution:[]}               │
│ □ ProfileScorer: categories= and actions= always passed               │
│ □ Factor name: threat_intel_enrichment (not threat_intel)             │
│ □ SOC_FACTORS: never fork, always import from config.py               │
│ □ Hooks 1/2/3: DecisionRecord, OutcomeRecord, ProfileSnapshot all present │
│ □ τ = 0.1. Never 0.25.                                                │
│ □ Centroids clip to [0.0, 1.0]                                        │
│ □ "product" not "demo" in all text                                    │
│ □ Never git. Never debugger.                                           │
├─────────────────────────────────────────────────────────────────────┤
│ BUG PATTERNS TO AVOID                                                 │
│ □ Silent defaults → make them loud (ROUTING_FAILURE log)              │
│ □ Scattered literals → centralize in domain.ts / config.py           │
│ □ Shape contracts → test isinstance(data, list) not just status 200  │
│ □ ID schema mismatch → state cross-component ID contracts in prompt   │
│ □ Double prefix → display IDs verbatim, never re-prefix               │
│ □ || vs ?? → use ?? for nullable values from storage                  │
├─────────────────────────────────────────────────────────────────────┤
│ AFTER EVERY PROMPT                                                    │
│ □ pytest tests/ → count ≥ start count                                 │
│ □ Acceptance criterion: binary pass/fail, not "looks good"            │
│ □ New bugs found but not fixed → add to tech debt table with TD-###  │
│ □ Update session_log_v55.md before closing                            │
└─────────────────────────────────────────────────────────────────────┘
```

---

*Coding Guidelines v1.0 · March 13, 2026*
*Derived from: 29 v5.0 sprint prompts, 7 VIS-2 bugs, LLM judge synthesis, operator framework review.*
*Every rule here was either validated by experience or created to prevent a class of bug we actually hit.*
*Update this document when a new class of bug is found. Add it to Part 3 with: Bug, Result, Root cause, Prevention pattern.*
