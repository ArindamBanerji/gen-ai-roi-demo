# SOC Copilot — Production Deployment Strategy

**Version:** 3.0
**Date:** February 26, 2026
**Replaces:** `deployment_strategy_v2_1.md`
**Feeds:** v4.0 Phase 5 (compounding proof), v4.5 (cross-domain discovery), v5.0–v7.5 design documents
**Prerequisites:** v3.2 tagged · v4.0 in build (includes value features F1–F4, F6) · v4.5 follows after v4.0 tagged

> **Changes from v2.1:**
> (1) New Part 1.5: Progressive Realism Philosophy — the principle that each version makes the
> system incrementally more "real" rather than treating realism as a cliff between demo and production.
> (2) New deployment tier: **Hosted Demo (VPS)** — bridges the gap between "runs on my laptop" and
> "cloud pilot with real data." v4.0 and v4.5 are hosted on a VPS for prospect self-service access.
> (3) v4.0 scope updated to include Phase 5 (compounding proof, trust curve, narrative) and
> value features F1 (ATT&CK) + F2 (alert corpus). 33 prompts, 11 sessions.
> (4) v4.5 scope updated to include F5 (cross-domain discovery moment). 18 prompts, 7 sessions.
> (5) Version map expanded with deployment state for each version.
> (6) New VPS hosting section with provider evaluation, setup prompts, demo reset strategy,
> access control for prospects, and cost analysis.
> (7) New Part 5: "What Makes Each Version More Real" — explicit realism increments per version.
> (8) Capability traceability updated with value features and VPS tier.
> (9) Decisions table updated with VPS and hosting decisions.

---

## Part 1: The Deployment Problem

The demo proves the architecture. It does not prove the infrastructure.

The gap between demo and production is a sequence-of-decisions problem, not a code problem:

**Data** — Synthetic alerts to customer data. Requires data agreements, schema mapping, and privacy controls before a single real IOC enters the system.

**Scale** — 20 demo alerts to 1.5TB/day at INOVA. Requires streaming infrastructure, horizontal scaling, and SLA commitments that do not exist in the demo stack.

**Compliance** — No PHI in the demo to HIPAA-covered operations. Requires BAAs, encryption, audit controls, and breach notification procedures.

**Tenancy** — One demo instance to multiple customers. Requires graph isolation, credential management, and cost attribution.

**Operations** — Developer-run to customer-operated. Requires monitoring, alerting, runbooks, and support SLAs.

None of these are solved by writing more demo code. This document maps the decisions to the version roadmap, version by version.

---

## Part 1.5: Progressive Realism [New in v3.0]

### The Principle

The traditional startup approach treats "demo" and "production" as two distinct states with a cliff between them. We reject this. Instead, every version makes the system incrementally more real along multiple dimensions:

| Dimension | What "More Real" Means |
|---|---|
| **Data** | Synthetic → curated realistic → anonymized real → real with redaction → real in production |
| **Infrastructure** | Local → Docker → VPS → Cloud Run (single) → Cloud Run (HA) → Multi-region |
| **Access** | Developer laptop → shared URL → prospect login → customer SSO → production auth |
| **Persistence** | In-memory → Neo4j local → Neo4j on VPS → Aura Professional → Aura Enterprise |
| **Compliance** | None → audit trail exists → HIPAA framing → BAA signed → compliance audited |
| **Operations** | Manual start → Docker Compose → systemd service → managed containers → SLA-backed |
| **Connectivity** | 1 source → 3 sources → 5 sources → customer's actual stack |

### Why This Matters

**For prospects:** each increment gives them something new to evaluate without requiring them to commit to a production deployment. A CISO can play with the hosted demo before signing a data agreement.

**For us:** each increment is testable, deployable, and fundable independently. We never need to bet the company on a single "production launch" — we can find paying customers at the hosted demo stage.

**For partners:** an MSSP can show the hosted demo to their clients today, without waiting for multi-tenant infrastructure.

### The Deployment Ladder

```
v3.0/v3.2:  LOCAL DEMO
              Runs on developer laptop. Single audience member. Developer operates.
              Realism: proves the intelligence. Nothing else.
                |
v4.0:       DOCKER + HOSTED DEMO (VPS)
              Docker Compose on a $20-40/month VPS. Prospects access via URL.
              Realism: proves Docker works. Proves the system runs unattended.
              Daily reset. No real data. No auth (basic HTTP auth or link-sharing).
                |
v4.5:       HOSTED DEMO (CUSTOMER-SPECIFIC INSTANCES)
              Same VPS, multiple Docker Compose stacks (one per prospect).
              Healthcare instance with INOVA-specific seed data.
              Realism: prospect sees their vertical. Still synthetic data.
                |
v5.0:       CLOUD PILOT (REAL DATA)
              Cloud Run / ECS. Real customer data with PHI redaction.
              Okta SSO. Secret Manager. Cloud monitoring.
              Realism: real data, real auth, real cloud. Not SLA-backed.
                |
v6.0:       PRODUCTION (SINGLE TENANT)
              HA, DR, SLAs, ServiceNow integration.
              Realism: the system is part of daily operations.
                |
v6.5+:      FULL PRODUCTION + STREAMING
              Flash Tier, multi-tenant, partner network.
              Realism: enterprise-grade at scale.
```

Each rung of the ladder is a deployable, demonstrable, and potentially fundable state.

---

## Part 2: Deployment Roadmap

### Version Map

| Version | Theme | Deployment State | Data | Auth | Infrastructure | Key Gate |
|---|---|---|---|---|---|---|
| v3.0 | Three loops | Local demo | Synthetic (5 alerts) | None | Laptop | — |
| v3.2 | Platform core | Local demo | Synthetic (5 alerts) | None | Laptop | — |
| **v4.0** | **Your tools. Compounding proved.** | **Docker + VPS** | **Synthetic (15-20 alerts)** | **Basic (HTTP auth)** | **VPS ($20-40/mo)** | **Docker + VPS live** |
| **v4.5** | **INOVA MVP + Discovery** | **VPS (multi-instance)** | **Synthetic (healthcare)** | **Basic + link sharing** | **VPS (same host)** | **Discovery moment live** |
| **v5.0** | **Validated POC — real data** | **Cloud pilot** | **Real (redacted)** | **Okta SAML** | **Cloud Run + Aura Pro** | **BAA + data agreement** |
| **v6.0** | **Production — single tenant** | **Production (SLA)** | **Real** | **Okta SAML** | **Cloud Run HA + Aura Enterprise** | **SLA + HIPAA audit** |
| **v6.5** | **Flash Tier + streaming** | **Full production** | **Real (1.5TB/day)** | **Okta SAML** | **+ Pub/Sub or Kinesis** | **30-day baseline** |
| **v7.0** | **Multi-tenant platform** | **Multi-tenant** | **Real (per-tenant)** | **Per-tenant SSO** | **Tenant-isolated** | **Tenancy isolation** |
| **v7.5** | **Partner network** | **Partner-deployed** | **Client-owned** | **Partner portal** | **Docker bundle** | **Partner portal** |

---

### v4.0 — Docker + Hosted Demo (VPS)

**Deployment goal:** The system runs unattended on a VPS. Prospects access a live demo via URL without installing anything locally. This is the first time someone other than the developer can experience the system independently.

#### VPS Hosting Strategy

**Provider evaluation (cost-optimized for bootstrapped startup):**

| Provider | Spec | Monthly Cost | Notes |
|---|---|---|---|
| **Hetzner Cloud** | CX31 (4 vCPU, 8GB RAM, 80GB SSD) | ~€8.50 (~$9) | Best value. EU and US-East DCs. |
| **DigitalOcean** | Droplet (4 vCPU, 8GB RAM, 160GB SSD) | $48 | Good DX. App Platform alternative. |
| **Linode (Akamai)** | Dedicated 4GB | $36 | Reliable. US presence. |
| **Oracle Cloud** | ARM A1 (4 OCPU, 24GB RAM) | **Free tier** | Always-free eligible. ARM requires testing. |

**Recommendation:** Start with **Hetzner CX31** ($9/month). If ARM works, Oracle Cloud free tier is the fallback for zero-cost hosting. Move to DigitalOcean or GCP if prospect volume warrants it.

**Why not GCP/AWS for the demo?** Cloud Run + Aura would cost $50-100/month minimum for something that runs 24/7. The VPS is a fixed cost with predictable billing. We move to managed services at v5.0 when a customer is paying.

#### VPS Architecture

```
VPS (Hetzner CX31 or equivalent)
├── Docker Compose
│   ├── soc-copilot-backend (FastAPI, port 8001)
│   ├── soc-copilot-frontend (nginx serving Vite build, port 80/443)
│   └── neo4j (community edition, port 7687)
├── Caddy or nginx reverse proxy
│   ├── demo.dakshineshwari.net → frontend
│   ├── demo.dakshineshwari.net/api → backend
│   └── Auto-TLS via Let's Encrypt
├── Cron job: daily reset
│   ├── docker-compose down
│   ├── docker volume prune (reset Neo4j data)
│   ├── docker-compose up -d
│   └── curl POST /api/graph/seed (re-seed demo data)
└── Basic access control
    ├── Option A: HTTP Basic Auth via Caddy (username/password shared with prospects)
    ├── Option B: Unique URL tokens (/demo/{token} → same app, token logged)
    └── Option C: No auth, daily reset means no data liability
```

#### VPS Setup Prompts (added to v4.0 build sequence)

These are run AFTER the Docker package (Phase 2, D1-D5) is complete and tested locally.

**Prompt VPS-1 — Infrastructure: Docker Compose Production Profile**
**Scope:** Create a `docker-compose.prod.yml` override for VPS deployment
**Files touched:**
- `docker-compose.prod.yml` (new)
- `Caddyfile` (new)
- `.env.production.example` (new)

**What to build:**

Production compose override that:
- Pins image versions (no `:latest` in production)
- Sets restart policies (`restart: unless-stopped` on all services)
- Binds Neo4j data volume to a named volume (survives container recreation)
- Exposes only ports 80 and 443 through Caddy reverse proxy
- Backend and Neo4j ports are internal only (not exposed to host network)
- Environment variables read from `.env.production`
- Health checks on all three services

Caddy reverse proxy:
```
demo.dakshineshwari.net {
    handle /api/* {
        reverse_proxy backend:8001
    }
    handle {
        reverse_proxy frontend:80
    }
}
```

Caddy handles TLS automatically via Let's Encrypt. No manual certificate management.

`.env.production.example`:
```
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=<generate-strong-password>
PULSEDIVE_API_KEY=<your-key>
GREYNOISE_API_KEY=<your-key>
DEMO_MODE=true
DEMO_RESET_ENABLED=true
```

**Verification test:**
```
1. docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
2. curl https://demo.dakshineshwari.net → frontend loads
3. curl https://demo.dakshineshwari.net/api/health → backend healthy
4. Neo4j port 7687 NOT accessible from outside the Docker network
```

---

**Prompt VPS-2 — Backend: Demo Reset Endpoint + Seed Script**
**Scope:** Endpoint that resets the demo to clean state
**Files touched:**
- `backend/app/routers/admin.py` (new)
- `backend/seed_neo4j.py` (modify — make callable from API, not just CLI)
- `scripts/daily-reset.sh` (new)

**What to build:**

1. `POST /api/admin/reset-demo` (protected by ADMIN_TOKEN environment variable):
   - Clears all Neo4j nodes and relationships
   - Re-runs seed script (all 15-20 alerts, threat intel, org graph, etc.)
   - Resets weight matrix to baseline
   - Resets trust scores to 0.5
   - Resets decision counter to 0
   - Returns: `{"status": "reset_complete", "alerts_seeded": 16, "graph_nodes": 47}`

2. `scripts/daily-reset.sh`:
   ```bash
   #!/bin/bash
   # Called by cron at 04:00 UTC daily
   curl -X POST https://demo.dakshineshwari.net/api/admin/reset-demo \
     -H "Authorization: Bearer ${ADMIN_TOKEN}"
   echo "Demo reset at $(date)" >> /var/log/demo-reset.log
   ```

3. Cron entry: `0 4 * * * /opt/soc-copilot/scripts/daily-reset.sh`

**Verification test:**
```
1. Process several alerts, give feedback, change weights
2. POST /api/admin/reset-demo with ADMIN_TOKEN
3. All alerts back to seed state, weights at baseline, decision count 0
```

---

**Prompt VPS-3 — Frontend: Demo Mode Banner + Welcome Screen**
**Scope:** When DEMO_MODE=true, show demo-specific UI elements
**Files touched:**
- `frontend/src/components/DemoBanner.tsx` (new)
- `frontend/src/components/WelcomeModal.tsx` (new)
- `frontend/src/App.tsx` (modify — add banner and modal)
- `frontend/src/lib/api.ts` (modify — add config endpoint)

**What to build:**

1. **Demo banner** (top of page, dismissible):
   ```
   🎯 LIVE DEMO — SOC Copilot v4.0 | This instance resets daily at 04:00 UTC
   Process alerts, give feedback, watch the compounding curve develop.
   Questions? arindam@dakshineshwari.net
   ```

2. **Welcome modal** (shown once per session, stored in sessionStorage):
   - Brief explanation: "This is a live instance of the SOC Copilot platform."
   - Suggested walkthrough: "Try Tab 3 (triage an alert) → give feedback → watch Tab 4 (compounding curve)"
   - Link to blog post / Loom video
   - "Get Started" button closes modal

3. Backend: `GET /api/config` returns `{"demo_mode": true, "version": "4.0", "reset_time": "04:00 UTC"}`

**Verification test:**
```
1. Load demo URL → welcome modal appears
2. Close modal → not shown again in same session
3. Demo banner visible at top
4. Banner shows correct version and reset time
```

---

#### VPS Build Sequence (integrated into v4.0)

```
PHASE 2 (Docker) completes D1-D5 → Docker works locally

PHASE 2.5 (VPS) — Session 6b or Session 7 extension:
  VPS-1 (prod compose + Caddy) + VPS-2 (reset endpoint) + VPS-3 (demo banner)
  TEST: demo.dakshineshwari.net accessible. Daily reset working. Demo banner visible.

Human work (not Claude Code):
  - Provision VPS (Hetzner CX31)
  - Point demo.dakshineshwari.net DNS to VPS IP
  - SSH into VPS, clone repo, copy .env.production, docker-compose up
  - Set up cron for daily reset
  - Test from phone/tablet (different network)
```

**Total VPS prompts: 3 (added to v4.0 build sequence). Total v4.0 prompts: 36 (33 + 3 VPS).**

#### v4.0 Deployment Gate Criteria

- [ ] Docker Compose starts all three services with one command
- [ ] `demo.dakshineshwari.net` loads frontend over HTTPS
- [ ] API calls work through reverse proxy
- [ ] Daily reset cron runs and restores clean demo state
- [ ] Demo banner and welcome modal visible
- [ ] Neo4j port NOT accessible from outside Docker network
- [ ] Compounding curve visible after processing 5+ alerts
- [ ] Share URL with 2 people — they can access and use independently
- [ ] Loom v3 can be recorded against this hosted instance

---

### v4.5 — Hosted Demo (Customer-Specific Instances)

**Deployment goal:** Multiple prospect-specific demo instances on the same VPS. INOVA sees healthcare seed data. A generic prospect sees the standard corpus. Each instance is isolated.

#### Multi-Instance Strategy

```
VPS (same Hetzner CX31 — 8GB RAM is enough for 2-3 instances)
├── Instance: default (demo.dakshineshwari.net)
│   ├── docker-compose -p soc-default ...
│   ├── Standard seed data (15-20 alerts, 5 types)
│   └── Port range: 8001-8010
├── Instance: inova (inova-demo.dakshineshwari.net)
│   ├── docker-compose -p soc-inova ...
│   ├── Healthcare seed data (HIPAA alerts, Health-ISAC, CISA KEV)
│   └── Port range: 8011-8020
├── Caddy routes by subdomain
└── Each instance has its own Neo4j volume + daily reset
```

**Memory budget:** Each instance needs ~2GB (FastAPI ~500MB + Neo4j ~1GB + frontend ~200MB + headroom). 8GB VPS supports 3 instances comfortably. Upgrade to 16GB (~$18/month on Hetzner) if more prospects need dedicated instances.

#### Additional VPS Prompts for v4.5

**Prompt VPS-4 — Infrastructure: Multi-Instance Compose Script**
**Scope:** Script to spin up/down named instances with per-instance config
**Files touched:**
- `scripts/instance-manager.sh` (new)
- `docker-compose.instance.yml` (new template)
- `configs/` directory with per-instance `.env` files

**What to build:**

```bash
# Create a new instance
./scripts/instance-manager.sh create inova --seed healthcare --domain inova-demo.dakshineshwari.net

# Stop/start an instance
./scripts/instance-manager.sh stop inova
./scripts/instance-manager.sh start inova

# Reset a specific instance
./scripts/instance-manager.sh reset inova

# List running instances
./scripts/instance-manager.sh list
```

Each instance gets:
- Its own Docker Compose project name (`soc-inova`, `soc-acme`, etc.)
- Its own Neo4j data volume
- Its own `.env` file (different seed profile, same API keys)
- Its own Caddy route (subdomain → instance ports)

**Verification test:**
```
1. Create default + inova instances
2. demo.dakshineshwari.net shows standard alerts
3. inova-demo.dakshineshwari.net shows healthcare alerts
4. Reset one instance — other unaffected
```

#### v4.5 Deployment Gate Criteria

- [ ] Two instances running simultaneously on same VPS
- [ ] Each instance has distinct seed data visible in Tab 3
- [ ] Cross-domain discovery (F5) working on INOVA instance
- [ ] HIPAA evidence ledger export working on INOVA instance
- [ ] Instance reset is per-instance, not global
- [ ] VPS stays within memory budget (< 80% utilization with 2 instances)
- [ ] Share INOVA-specific URL with healthcare prospect

---

### v5.0 — Validated POC

**Theme:** "First real customer data processed safely."
**Deployment state:** INOVA running the system against a controlled subset of real data in a pre-production environment. Not SLA-backed. Not HA. Purpose: prove the architecture holds on real data without compliance exposure.

#### Blocking gates

- HIPAA BAA signed with Anthropic LLM vendor (INOVA Open Item OI-01)
- Data Processing Agreement with INOVA covering SOC alert data
- PII/PHI redaction layer designed and audited before any real data enters

#### Infrastructure target

```
VPS (v4.0/v4.5 demo)     ->  v5.0 target
--------------------------------------------------------------
Docker Compose on VPS     ->  Cloud Run (single container, GCP)
                               — or ECS Fargate (AWS) if INOVA mandates
Neo4j (Docker on VPS)     ->  Neo4j Aura Professional
Caddy reverse proxy       ->  Cloud Load Balancing
.env file on VPS          ->  Google Secret Manager
                               — or AWS Secrets Manager
HTTP Basic Auth / tokens  ->  Okta SAML (INOVA requirement OI-03)
No monitoring             ->  Cloud Monitoring + Cloud Logging
                               — or CloudWatch
Daily cron reset          ->  No reset — data accumulates (this is the point)
```

**Important:** The VPS demo instances (v4.0/v4.5) continue running alongside v5.0. The VPS is for prospects. v5.0 is for INOVA's real data. They are separate environments serving separate purposes.

GCP is the lower-friction first deployment since the stack is partially there: Cloud Run requires no code changes from local FastAPI, stays inside the same VPC as Neo4j Aura, and eliminates cross-cloud networking overhead. AWS remains valid if INOVA's enterprise requirements mandate it — the FastAPI container is cloud-agnostic.

#### v5.0 prompts

**Prompt P5-1 — Backend: PII/PHI Redaction Middleware**
Config-driven redaction (`PHI_FIELDS` in Secret Manager) applied before any graph write or LLM call. Audit log: every redaction event logged with field name (not value) and timestamp. Verification: no PHI field value in Neo4j; LLM context payloads inspectable via debug endpoint.

**Prompt P5-2 — Backend: Splunk HEC Ingest Endpoint**
`POST /api/ingest/splunk-hec` accepts Splunk HTTP Event Collector format, normalizes to canonical alert schema, routes to existing triage pipeline. Verification: test Splunk event appears in Tab 3 queue.

**Prompt P5-3 — Backend: Auth Middleware (Okta SAML)**
Token validation with role mapping: SOC Analyst, Manager, CISO. All API endpoints require valid token except `/health`. Frontend redirects to Okta login if unauthenticated.

**Prompt P5-4 — Backend: Secret Manager Integration**
Replace all `os.environ` API key reads with Secret Manager calls (GCP or AWS). Local dev falls back to `.env` when `SECRET_MANAGER_ENABLED=false`.

**Prompt P5-5 — Frontend: Production Build**
`vite build` to Cloud Storage bucket + CDN. `VITE_API_URL` points to Cloud Run service URL. Verification: CDN URL loads app; API calls succeed end-to-end.

**Prompt P5-6 — Backend: ATT&CK Coverage Heatmap (F7)**
Aggregate which MITRE techniques the system has triaged, with what confidence and outcome distribution. New endpoint: `GET /api/metrics/attack-coverage`. Tab 4 panel: heatmap grid showing technique coverage. SOC maturity metric for the board.

**Prompt P5-7 — Backend: Shift Handoff Intelligence (F8)**
Track what changed since a given timestamp. New endpoint: `GET /api/handoff/since?timestamp=...`. Returns: new alerts triaged, weight changes, discoveries, trust changes, policy updates. Tab 4 panel: "Since your last shift" summary. Institutional knowledge survives shift changes.

#### v5.0 gate criteria

- [ ] BAA signed
- [ ] PHI redaction verified (manual audit or pen test)
- [ ] Okta auth working end-to-end with real INOVA user accounts
- [ ] 100+ real INOVA alerts processed without compliance incident
- [ ] INOVA SOC team present for live walkthrough on real data
- [ ] ATT&CK heatmap shows coverage from real alert processing
- [ ] Shift handoff summary working across shift boundary

---

### v6.0 — Production. Single Tenant.

**Theme:** "INOVA SOC, live."
**Deployment state:** Production-grade, single tenant. SLAs apply. HA, DR, monitoring, on-call.

#### Blocking decisions before v6 build begins

**Neo4j deployment model:**
- Neo4j Aura Enterprise (managed, HIPAA-eligible — preferred if INOVA funds it)
- Self-managed on GCE instances, multi-zone (full control, operational burden)
- Self-managed on EC2 Multi-AZ (if AWS-mandated)

**Human authority gate scope:** What actions can the system take autonomously at 90% confidence? Block IP, create ServiceNow ticket, notify analyst, escalate to CISO — each action type needs explicit approval from INOVA CISO before v6 build, not during it.

**Incident response boundary:** Threshold must be configurable per alert type (not hardcoded) and every threshold change must be auditable.

#### v6.0 infrastructure (GCP-primary)

```
Cloud Load Balancing
        |
Cloud Run (multi-region, min 2 instances)
  FastAPI (web) + APScheduler (discovery sweep)
        |                    |
Neo4j Aura Enterprise    Cloud SQL PostgreSQL
(context graph)          (audit log, evidence ledger,
                          policy history)

Supporting: Secret Manager · Cloud Monitoring · Cloud Audit Logs
            Cloud Storage (audit exports, hash chain backups)
```

AWS equivalent: ALB, ECS Fargate, RDS PostgreSQL, S3, AWS Secrets Manager, CloudWatch. Architecture is identical — only managed service names change. IaC (Terraform) can target either; the choice is a variable, not a structural difference.

#### v6.0 prompts

**Prompt P6-1 — Infrastructure: IaC Base**
Terraform (or Cloud Deployment Manager) for VPC, Cloud Run service, Neo4j Aura connection config, Cloud SQL instance, Cloud Storage buckets. Generate IaC files — human applies. No git commands.

**Prompt P6-2 — Backend: HA Startup + Health Checks**
`GET /health` returns per-dependency status: Neo4j, Cloud SQL, each connector, Secret Manager. Graceful shutdown: in-flight requests complete before container stops. Startup guard: refuse to start if PHI redaction config missing.

**Prompt P6-3 — Backend: ServiceNow Integration (Real)**
Replace mock with real ServiceNow API call (OAuth 2.0, credentials in Secret Manager). Idempotency: same `alert_id` never creates duplicate tickets. Ticket creation logged in Evidence Ledger.

**Prompt P6-4 — Backend: Configurable Confidence Thresholds**
Move hardcoded 0.90 threshold to per-alert-type table in Cloud SQL. CISO role adjusts via Tab 4 settings panel. Every change audited: actor, timestamp, old value, new value.

**Prompt P6-5 — Backend: Rate Limiting + Circuit Breakers**
Rate limiting on all ingest endpoints. Circuit breaker on each connector: 3 consecutive failures marks connector unhealthy, falls back to cached data, alerts on-call.

#### v6.0 gate criteria

- [ ] 99.5% uptime SLA signed with INOVA
- [ ] DR tested: Neo4j restore < 30 minutes RTO
- [ ] Human authority gate tested: zero autonomous actions above threshold
- [ ] ServiceNow live and creating real tickets
- [ ] HIPAA audit review passed
- [ ] INOVA SOC team using the system daily for one full month

---

### v6.5 — Flash Tier + Streaming

**Theme:** "Pre-ingestion intelligence at 1.5TB+/day."
**Deployment state:** Full INOVA streaming architecture. Flash Tier concept validated at v4.5 via mimic — this is the infrastructure investment that follows that validation.

v6.5 is a separate increment from v6.0 because Flash Tier is a streaming pipeline, not a request/response API. Building it into v6.0 would delay production by months. The right sequence: ship v6.0, prove value, add Flash Tier once the baseline is established.

#### Cloud transport decision (must be made before v6.5 design)

**GCP Pub/Sub + Cloud Functions Gen2 (preferred if stack remains on GCP)**

- No shard management — Pub/Sub auto-scales to any throughput without pre-provisioning
- Cloud Functions trigger on Pub/Sub push — Python scoring code is identical to local version
- Stays inside the same VPC as Cloud Run (FastAPI) and Neo4j Aura
- No cross-cloud networking, no VPN tunnels, no egress charges
- Cloud Storage serves as the suppression bucket (same role as S3, identical SDK patterns)
- Estimated infrastructure for 1.5TB/day: 2-3 Cloud Functions instances, auto-scaling

**AWS Kinesis + Lambda (if INOVA mandates AWS production environment)**

- 15 Kinesis shards baseline at 1.5TB/day (1MB/sec per shard), auto-scale to 120
- Lambda triggers on Kinesis stream records — same Python scoring code
- S3 suppression bucket with 30-day retention

**Transport abstraction — implement from day one regardless of cloud choice:**

```python
class StreamingTransport(ABC):
    async def publish(self, raw_alert: RawAlert) -> str: ...
    async def subscribe(self, handler: Callable) -> None: ...

class PubSubTransport(StreamingTransport):   # GCP implementation
    ...

class KinesisTransport(StreamingTransport):  # AWS implementation
    ...
```

All Flash Tier scoring code calls `StreamingTransport` — never GCP or AWS SDK directly. Switching clouds is a config change (`STREAMING_BACKEND=pubsub|kinesis`), not a code change.

#### v6.5 data flow

```
Splunk HEC -> Pub/Sub topic (or Kinesis stream)
                  |
           Cloud Function (or Lambda)
           PIR enforcement: strip PHI/PII fields here, before any write
           Forensic scoring: signal_fidelity + asset_risk + ttl_match + event_confidence
           Score >= suppress_threshold  -> UCL staging -> triage queue -> analyst queue
           Score <  suppress_threshold  -> Cloud Storage suppression bucket (30-day retention)
                  |
           TRIGGERED_EVOLUTION write-back when analyst correction fires downstream
           (same mechanism as INOVA-2 — named graph relationship, not a config file update)
```

The suppression bucket is not a discard bin. Every suppressed alert is logged with full context and retrievable for 30 days. When an analyst correction implicates a suppressed alert, it is retrieved and routed to the triage queue with a FLASH_TIER_OVERRIDE flag.

#### v6.5 gate criteria

- [ ] v6.0 in production for minimum 30 days (establishes suppression accuracy baseline)
- [ ] 60% volume reduction demonstrated over 30-day window post-v6.5 deployment
- [ ] Write-back chain tested: 10 analyst corrections measurably improve Flash Tier scoring
- [ ] False negative rate no higher than v6.0 baseline
- [ ] Cloud Storage suppression bucket retention and retrieval verified
- [ ] PHI/PII stripping verified at Cloud Function layer (before graph write)

---

### v7.0 — Multi-Tenant Platform

**Theme:** "One platform, multiple customers, compounding across the network."
**Deployment state:** 2-3 customers, isolated graphs, self-service tenant portal.

#### Tenancy isolation models

**Model A: Separate Neo4j Aura instance per tenant**
Physical isolation. FastAPI routing: `tenant_id` in JWT maps to Aura connection string in Secret Manager (`/inova/neo4j_uri`, `/acme/neo4j_uri`). Cost: highest. Risk: lowest. **Recommended for HIPAA-covered tenants.**

**Model B: Single Neo4j, tenant-scoped namespaces**
Every node carries `tenant_id`; all queries filter by it. Cost: lowest. Risk: highest (one query bug equals a data leak). **Do not use for HIPAA-covered tenants.**

**Model C: Single Neo4j, separate named databases per tenant**
Database-level isolation via `USE inova MATCH...`. Cost: middle. Risk: low. **Recommended for non-HIPAA tenants.**

Decision: Model A for INOVA. Model C for others. Never Model B for production.

#### v7.0 prompts

**Prompt P7-1 — Backend: Tenant Management Service**
Provision new tenant: create Aura instance (or named database), seed base schema, register connectors, configure thresholds. JWT validation carries `tenant_id` claim. Secret Manager paths scoped per tenant.

**Prompt P7-2 — Frontend: Tenant Onboarding Portal**
Self-service connector configuration, threshold setup, user management, usage dashboard (alerts processed, cost avoided, decisions made, billed separately).

**Prompt P7-3 — Backend: Meta-Graph (Cross-Tenant Patterns, Anonymized, Opt-In)**
If two tenants both discover the same threat actor correlation, the anonymized pattern enriches both graphs. No raw IOC sharing — pattern metadata only. Requires explicit opt-in and separate data processing agreement per tenant. This is the network effect moat: the platform compounds across the customer network, not just within each customer.

#### v7.0 gate criteria

- [ ] 2 customers live simultaneously with zero cross-tenant data leakage verified
- [ ] Tenant provisioning time < 2 hours, self-service, no engineering involvement
- [ ] Per-tenant cost tracked and attributable in billing system
- [ ] Meta-graph opt-in working with at least 1 pattern shared across 2 consenting tenants

---

### v7.5 — Partner Network

**Theme:** "MSSP-ready. Partner-deployed. Self-service."
**Deployment state:** MSSPs and consulting partners deploy for their clients. Client data never leaves client environment.

The v4.0 Docker package (D1-D5) is the foundation. v7.5 makes it tenant-aware and partner-instrumented:

```
MSSP Partner receives:
  - Docker Compose bundle (v7-tenant-aware base)
  - Connector credential template (client fills in API keys)
  - PARTNER_README (step-by-step, no engineering required)
  - Partner portal API key (calls back to meta-graph opt-in)

MSSP deploys per client: docker-compose up
Client data stays in client environment.
Partner sees anonymized performance metrics (opt-in).
Meta-graph enriches across MSSP client base (opt-in).
```

**Pricing model decision — must be made before v7.5 build:**
Per-tenant monthly fee, per-alert metered, partner revenue share, or enterprise license. The choice determines: metering infrastructure (P7.5-1), partner portal (P7.5-2), usage reporting in Tab 4 (P7.5-3).

#### v7.5 gate criteria

- [ ] v7.0 multi-tenant working with 2+ customers
- [ ] Partner portal MVP: provision a client, see usage, configure connectors
- [ ] Pricing model defined and billing infrastructure live
- [ ] First MSSP partner onboarded and deploying for at least one client

---

## Part 3: Version-to-Capability Traceability

| Capability | Demo Proof | Hosted Demo | Production Gate |
|---|---|---|---|
| UCL connector pattern | v4.0 C1-C5 | v4.0 VPS | v5.0 (real connectors) |
| MITRE ATT&CK alignment | v4.0 F1a/F1b | v4.0 VPS | v5.0 (real alerts) |
| Realistic alert corpus (15-20 alerts) | v4.0 F2a/F2b/F2c | v4.0 VPS | v5.0 (real alerts) |
| Investigation narrative | v4.0 F3a/F3b | v4.0 VPS | v5.0 |
| Compounding curve (weight evolution + confidence) | v4.0 F4a-F4d | v4.0 VPS | v5.0 (real data curve) |
| Asymmetric trust curve (20:1) | v4.0 F6a/F6b | v4.0 VPS | v5.0 |
| Docker deployment | v4.0 D1-D5 | v4.0 VPS-1 | v7.5 (partner bundle) |
| Demo reset + daily cron | — | v4.0 VPS-2 | N/A (production accumulates) |
| Demo mode banner + welcome | — | v4.0 VPS-3 | N/A |
| Multi-instance hosting | — | v4.5 VPS-4 | v7.0 (multi-tenant) |
| UCL entity resolution | v4.5 INOVA-1a/1b | v4.5 VPS | v5.0 (real customer data) |
| TRIGGERED_EVOLUTION traversal | v4.5 INOVA-2 + evolution trace modal | v4.5 VPS | v5.0 (compliance audit) |
| Cross-graph discovery sweep | v4.5 INOVA-4a/b/c | v4.5 VPS | v6.0 (weekly scheduled sweep) |
| Cross-domain discovery moment (F5) | v4.5 F5a/F5b/F5c | v4.5 VPS | v5.0 (real data discovery) |
| Loop 3 governing signal | v4.5 INOVA-5 (labeling) | v4.5 VPS | v5.0 (production RL signal) |
| HIPAA evidence ledger + compliance export (F9) | v4.5 INOVA-6 (framing) | v4.5 VPS | v5.0 (Cloud SQL, BAA) |
| Flash Tier pre-filter — validated | v4.5 FT-MIMIC-1 through -4 | v4.5 VPS | — |
| Flash Tier pre-filter — production | — | — | v6.5 (Pub/Sub or Kinesis) |
| Healthcare connectors | v4.5 INOVA-3a/b | v4.5 VPS | v5.0 (Health-ISAC TAXII agreement) |
| ATT&CK coverage heatmap (F7) | — | — | v5.0 P5-6 |
| Shift handoff intelligence (F8) | — | — | v5.0 P5-7 |
| Auth (Okta SAML) | Not in demo | Not in hosted demo | v5.0 (blocking gate) |
| PHI redaction layer | Not in demo | Not in hosted demo | v5.0 (blocking gate) |
| Multi-tenant isolation | Not in demo | Primitive (separate Docker stacks) | v7.0 (Aura per HIPAA tenant) |
| Partner Docker deployment | v4.0 D1-D5 | v4.0 VPS | v7.5 (partner portal + metering) |
| Meta-graph (cross-tenant) | Not in demo | Not in hosted demo | v7.0 opt-in |
| S2P domain copilot | v3.2 domain framework ready | — | v7.0 (domain module + domain graph) |

---

## Part 4: Decisions Not to Defer

These are business, legal, and architectural commitments — not code decisions. Each blocks a specific version and must be resolved before the corresponding design document is written.

| Decision | Blocks | Who Decides | Deadline |
|---|---|---|---|
| **VPS provider selection (Hetzner vs Oracle vs DO)** | **v4.0 VPS deployment** | **Founder** | **Before Phase 2.5 build** |
| **DNS: demo.dakshineshwari.net subdomain** | **v4.0 VPS deployment** | **Founder** | **Before Phase 2.5 build** |
| **Demo access model: HTTP auth vs token vs open** | **v4.0 VPS-1** | **Founder** | **Before Phase 2.5 build** |
| BAA with Anthropic (LLM vendor) | v5.0 build | Anthropic legal + INOVA legal | Before v5 build |
| Cloud choice for v5.0/v6.0: GCP or AWS? | v5.0 P5-1 infra | Founder + INOVA IT | Before v5 build |
| Flash Tier transport: GCP Pub/Sub or AWS Kinesis? | v6.5 design | Follows cloud decision above | Before v6.5 design |
| Neo4j deployment: Aura Enterprise, GCE, or EC2? | v6.0 P6-1 | Commercial (cost vs. ops) | Before v6 design |
| Human authority gate scope: which actions are autonomous at 90%? | v6.0 P6-4 | INOVA CISO | Before v6 build |
| Pricing model: per-alert, per-seat, platform fee, or enterprise? | v7.5 build | Commercial | Before v7.5 design |
| Tenancy isolation: Model A vs Model C? | v7.0 P7-1 | Architecture + legal | Before v7 design |
| Meta-graph legal basis: DPA template for cross-tenant sharing | v7.0 P7-3 | Legal | Before v7 design |
| Health-ISAC TAXII: institutional membership required for production feed | v5.0 (real feed) | Founder + INOVA | Before v5 build |

---

## Part 5: What Makes Each Version More Real [New in v3.0]

This is the explicit accounting of what changes between versions to make the system progressively more credible, deployable, and production-worthy.

| Transition | Data Gets More Real | Infra Gets More Real | Access Gets More Real | Operations Get More Real |
|---|---|---|---|---|
| **v3.2 → v4.0** | 5 alerts → 15-20 alerts, 5 types, ATT&CK taxonomy. Compounding visible. | Laptop → Docker → VPS. First unattended deployment. | Developer-only → URL sharing with prospects. | Manual start → Docker Compose + daily reset cron. |
| **v4.0 → v4.5** | Standard → healthcare-specific seed data. Cross-domain discovery scenario. | Single instance → multi-instance on same VPS. | One URL → per-prospect subdomains. | One reset script → per-instance management. |
| **v4.5 → v5.0** | Synthetic → **real customer data** (redacted). | VPS → **cloud-managed** (Cloud Run + Aura Pro). | Token/HTTP auth → **Okta SSO**. | Cron reset → **data accumulates** (this is the point). |
| **v5.0 → v6.0** | Pre-production → **production** data flows. | Single instance → **HA multi-region**. | INOVA SOC team → **daily operational use**. | Best-effort → **SLA-backed (99.5%)**. |
| **v6.0 → v6.5** | Batch → **streaming (1.5TB/day)**. | Request/response → **event-driven pipeline**. | Same. | + Streaming monitoring + suppression audit. |
| **v6.5 → v7.0** | One customer → **multiple isolated graphs**. | Single tenant → **multi-tenant** infra. | One org → **per-tenant SSO**. | + Tenant provisioning + billing. |
| **v7.0 → v7.5** | Direct → **partner-deployed** in client environment. | Managed → **Docker bundle for partners**. | Self-service → **partner portal**. | + Partner certification + support tiers. |

**Key insight:** The VPS hosted demo (v4.0/v4.5) is not a throwaway. It continues running alongside cloud deployments. The VPS serves prospects and partners. The cloud serves production customers. They coexist permanently — different audiences, different purposes, different cost profiles.

---

## Appendix: Cost Model (Bootstrapped)

| Phase | Monthly Cost | What You Get |
|---|---|---|
| v3.0–v3.2 (local) | $0 | Laptop demo |
| v4.0–v4.5 (VPS) | $9–18 (Hetzner) | Hosted demo, 2-3 instances, HTTPS, daily reset |
| v5.0 (cloud pilot) | $50–150 (Cloud Run + Aura Pro) | Real data, SSO, cloud monitoring |
| v6.0 (production) | $300–800 (HA + Aura Enterprise) | SLA-backed, DR, ServiceNow |
| v6.5 (streaming) | +$200–500 (Pub/Sub + Functions) | Flash Tier at scale |
| v7.0+ (multi-tenant) | Per-customer Aura instance cost | Revenue should cover this |

**The VPS tier ($9-18/month) is the most important investment.** It turns the demo from a developer artifact into a prospect-accessible product with near-zero cost. Every dollar spent here has the highest leverage of any infrastructure investment in the roadmap.

---

## Appendix: Version History

| Version | Date | Changes |
|---|---|---|
| **1.0** | **Feb 24, 2026** | Initial deployment strategy. |
| **2.0** | **Feb 25, 2026** | GCP primary, Flash Tier specs moved to v4.5 design, v3.2 added. |
| **2.1** | **Feb 26, 2026** | Sequential build confirmed. v4.0/v4.5 prerequisites updated. |
| **3.0** | **Feb 26, 2026** | **Progressive Realism philosophy. Hosted Demo (VPS) tier added. VPS prompts (VPS-1 through VPS-4). Multi-instance strategy for v4.5. Cost model. "What Makes Each Version More Real" table. v4.0 updated to 36 prompts (33 + 3 VPS). v5.0 updated with F7/F8 prompts. Capability traceability expanded.** |

---

*SOC Copilot — Production Deployment Strategy v3.0 | February 26, 2026*
*Feeds: v4.0 (36 prompts), v4.5 (18 prompts), v5.0–v7.5 design documents*
*New: VPS Hosted Demo tier · Progressive Realism · Multi-instance hosting*
*Prerequisites: v3.2 tagged · v4.0 in build · v4.5 follows after v4.0 tagged*
