# Gen-AI ROI Demo: Bootstrap Sequence v5

**Your Current State:** 
- âœ… GCP account created
- âœ… Claude Code installed
- âœ… Project directory created with CLAUDE.md and docs/vc_demo_build_spec_v6.md

**End State:** Ready to start building with Claude Code

**Key Changes from v4:**
1. **Simplified agent architecture** â€” Rule-based decision engine with LLM narration (~200 lines total)
2. **Accelerated timeline** â€” 4-week build â†’ 2-week build due to simpler backend
3. **Updated file references** â€” setup_notebook_v4.py, build_spec_v6.md, CLAUDE_v6.md

**Key Changes from v3 (retained):**
1. **Neo4j compatibility** â€” Schema includes CAUSED and PRECEDENT_FOR relationships
2. **AuraDS note** â€” FastRP embeddings require paid tier (we use semantic embeddings instead)
3. **Reference implementation** â€” Link to Neo4j's context-graph-demo

**Key Changes from v2 (retained):**
1. **Decision Trace schema added from Day 1** â€” The TRIGGERED_EVOLUTION relationship is our key differentiator
2. **Tab 2 scaffolding starts in Week 1** â€” It's THE money shot, not "one feature among many"
3. **Two-loop visual verification gate** â€” Added as Week 3 checkpoint

---

## Overview

```
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚                     BOOTSTRAP SEQUENCE v4                                   â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚                                                                             â”‚
â”‚  ALREADY DONE:                                                              â”‚
â”‚  âœ… Phase 1: GCP Account                                                    â”‚
â”‚                                                                             â”‚
â”‚  TO DO:                                                                     â”‚
â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”   â”‚
â”‚  â”‚ Phase 2: Anthropic API Credits â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ 5 min        â”‚   â”‚
â”‚  â”‚          Buy $50 at console.anthropic.com                           â”‚   â”‚
â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜   â”‚
â”‚                          â”‚                                                  â”‚
â”‚                          â–¼                                                  â”‚
â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”   â”‚
â”‚  â”‚ Phase 3: Local Tools â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ 20 min       â”‚   â”‚
â”‚  â”‚          Python 3.11+, Node 20+, gcloud CLI                         â”‚   â”‚
â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜   â”‚
â”‚                          â”‚                                                  â”‚
â”‚                          â–¼                                                  â”‚
â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”   â”‚
â”‚  â”‚ Phase 4: Neo4j Aura Account â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ 10 min       â”‚   â”‚
â”‚  â”‚          Create free account + database                             â”‚   â”‚
â”‚  â”‚          â˜… NOTE: For FastRP embeddings, use AuraDS (paid)          â”‚   â”‚
â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜   â”‚
â”‚                          â”‚                                                  â”‚
â”‚                          â–¼                                                  â”‚
â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”   â”‚
â”‚  â”‚ Phase 5: Colab Infrastructure Setup â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ 30 min       â”‚   â”‚
â”‚  â”‚          Run setup_notebook_v4.py in Colab Pro                      â”‚   â”‚
â”‚  â”‚          Creates: BigQuery, Firestore, Neo4j graph, seed data       â”‚   â”‚
â”‚  â”‚          â˜… Includes Decision, DecisionContext, EvolutionEvent       â”‚   â”‚
â”‚  â”‚          â˜… Creates TRIGGERED_EVOLUTION relationships                â”‚   â”‚
â”‚  â”‚          â˜… NEW: Creates CAUSED and PRECEDENT_FOR relationships      â”‚   â”‚
â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜   â”‚
â”‚                          â”‚                                                  â”‚
â”‚                          â–¼                                                  â”‚
â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”   â”‚
â”‚  â”‚ Phase 6: Local Environment Setup â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ 10 min       â”‚   â”‚
â”‚  â”‚          Authenticate gcloud, create .env, .gitignore               â”‚   â”‚
â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜   â”‚
â”‚                          â”‚                                                  â”‚
â”‚                          â–¼                                                  â”‚
â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”   â”‚
â”‚  â”‚ Phase 7: Claude Code Setup â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ 5 min        â”‚   â”‚
â”‚  â”‚          Authenticate + verify                                       â”‚   â”‚
â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜   â”‚
â”‚                          â”‚                                                  â”‚
â”‚                          â–¼                                                  â”‚
â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”   â”‚
â”‚  â”‚ Phase 8: Verification â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ 5 min        â”‚   â”‚
â”‚  â”‚          Test all connections                                        â”‚   â”‚
â”‚  â”‚          â˜… Verify TRIGGERED_EVOLUTION relationship exists            â”‚   â”‚
â”‚  â”‚          â˜… NEW: Verify CAUSED and PRECEDENT_FOR relationships        â”‚   â”‚
â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜   â”‚
â”‚                                                                             â”‚
â”‚  TOTAL TIME: ~85 minutes                                                   â”‚
â”‚                                                                             â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

---

## Phase 2: Anthropic API Credits (5 minutes)

Claude Code requires API credits (separate from your Claude Max subscription).

### Step 2.1: Buy API Credits

```
1. Go to: https://console.anthropic.com/settings/billing
2. Click "Buy credits"
3. Add $50 (enough for weeks of development)
4. Complete payment
```

### Step 2.2: Verify

```
1. Refresh the billing page
2. Confirm you see a credit balance (e.g., "$50.00")
```

âœ… **Checkpoint:** Credit balance shows in Anthropic console.

---

## Phase 3: Local Development Tools (20 minutes)

### Step 3.1: Install Python 3.11+

**macOS:**
```bash
brew install python@3.11
```

**Windows:**
```
1. Download from: https://www.python.org/downloads/
2. Run installer
3. âœ“ CHECK "Add Python to PATH" during install
```

**Verify:**
```bash
python3 --version
# Should show: Python 3.11.x or higher
```

### Step 3.2: Install Node.js 20+

**macOS:**
```bash
brew install node@20
```

**Windows:**
```
1. Download LTS from: https://nodejs.org/
2. Run installer, accept defaults
```

**Verify:**
```bash
node --version
# Should show: v20.x.x or higher

npm --version
# Should show: 10.x.x
```

### Step 3.3: Install Google Cloud CLI

**macOS:**
```bash
brew install --cask google-cloud-sdk
```

**Windows:**
```
1. Download from: https://cloud.google.com/sdk/docs/install
2. Run installer
3. Accept defaults
```

**Verify:**
```bash
gcloud --version
# Should show: Google Cloud SDK xxx.x.x
```

âœ… **Checkpoint:** All three commands return version numbers.

---

## Phase 4: Neo4j Aura Account (10 minutes)

Neo4j Aura provides a free graph database for the semantic layer.

**Note on AuraDS:** The free tier (AuraDB) is sufficient for this demo. However, if you need advanced GDS algorithms like FastRP embeddings (used in Neo4j's context-graph-demo), upgrade to AuraDS (paid tier). Our demo doesn't require FastRP â€” our differentiator is TRIGGERED_EVOLUTION, not embedding similarity.

### Step 4.1: Create Account

```
1. Go to: https://neo4j.com/cloud/aura-free/
2. Click "Start Free"
3. Sign up with Google or email
4. Verify your email if required
```

### Step 4.2: Create Free Database

```
1. In Neo4j Aura console, click "New Instance"
2. Select "AuraDB Free" (the free tier)
3. Configuration:
   - Instance name: gen-ai-roi-demo
   - Region: Select closest to you (or leave default)
4. Click "Create"
5. âš ï¸ IMPORTANT: A password will be shown. SAVE IT NOW.
   You will NOT see this password again!
```

### Step 4.3: Note Connection Details

After creation (wait 1-2 minutes), you'll see:
```
Connection URI: neo4j+s://xxxxxxxx.databases.neo4j.io
Username: neo4j
Password: (the one you saved)
```

**Save these three values** â€” you'll enter them in the Colab notebook.

âœ… **Checkpoint:** Neo4j database shows "Running" status, you have URI and password saved.

---

## Phase 5: Colab Infrastructure Setup (30 minutes)

This is where the magic happens. The Colab notebook sets up everything programmatically.

### Step 5.1: Open Colab

```
1. Go to: https://colab.research.google.com/
2. Sign in with your Google account (same as GCP)
```

### Step 5.2: Upload the Setup Notebook

```
1. File â†’ Upload notebook
2. Select: setup_notebook_v4.py (from your downloads)
   OR
   File â†’ New notebook, then paste contents of setup_notebook_v4.py
```

### Step 5.3: Run the Notebook

The notebook has **31 cells** (v3 adds CAUSED/PRECEDENT_FOR relationships). Run them in order (Shift+Enter for each).

**Key cells to watch:**

| Cell | What It Does | What You Need to Do |
|------|--------------|---------------------|
| 1 | Install packages | Just run |
| 2 | Authenticate GCP | Click popup link, sign in |
| 3 | Set project config | **CHANGE PROJECT_ID if needed** |
| 4 | Enable APIs | Just run (takes 2-3 min) |
| 6-11 | Create BigQuery | Just run |
| 12-19 | Create Firestore | Just run (creates collections) |
| 20 | Test Gemini | Just run (verifies Vertex AI) |
| 22 | Neo4j credentials | **ENTER YOUR NEO4J URI AND PASSWORD** |
| 23-26 | Seed Neo4j graph (original entities) | Just run |
| **27** | **Create Decision Trace nodes** | Just run |
| **28** | **â˜… Create TRIGGERED_EVOLUTION + CAUSED + PRECEDENT_FOR** | Just run |
| **29** | **â˜… Verify two-loop schema + Neo4j compatibility** | Just run |
| 30 | Generate .env | **COPY THE OUTPUT** |

### Step 5.4: Handle Firestore Creation

If you see "database not found" error in Cell 12:

```
1. Go to: https://console.cloud.google.com/firestore
2. Click "Create Database"
3. Select "Native mode" (NOT Datastore mode) âš ï¸ CRITICAL
4. Select location: nam5 (United States)
5. Click "Create"
6. Wait 1-2 minutes
7. Re-run Cell 12
```

### Step 5.5: Verify Decision Trace Schema (UPDATED v4)

Cell 29 should output:
```
Decision Trace Schema Verification:
â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
Decision nodes:           5
DecisionContext nodes:    5  
EvolutionEvent nodes:     3
TRIGGERED_EVOLUTION rels: 3  â† THE KEY RELATIONSHIP
CAUSED rels:              2  (causal chains)
PRECEDENT_FOR rels:       2  (precedent matching)

âœ“ Two-loop schema verified â€” TRIGGERED_EVOLUTION relationships exist
âœ“ Neo4j compatibility verified â€” CAUSED and PRECEDENT_FOR exist
```

âš ï¸ **If TRIGGERED_EVOLUTION shows 0:** Re-run Cell 28. This relationship is critical.
âš ï¸ **If CAUSED or PRECEDENT_FOR show 0:** Re-run Cell 28 (v3 adds these relationships).

### Step 5.6: Copy .env Output

Cell 30 outputs your .env file contents. It looks like:

```
# GCP Configuration
GOOGLE_CLOUD_PROJECT=gen-ai-roi-demo
GOOGLE_CLOUD_REGION=us-central1

# BigQuery
BIGQUERY_DATASET=ucl

# Vertex AI (Gemini)
GEMINI_MODEL=gemini-1.5-pro-002
GEMINI_LOCATION=us-central1

# Neo4j Aura
NEO4J_URI=neo4j+s://xxxxxxxx.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-actual-password

# Application
LOG_LEVEL=INFO
ENVIRONMENT=development
```

**Copy this entire block** â€” you'll use it in the next phase.

âœ… **Checkpoint:** Cell 31 shows "SETUP COMPLETE! âœ“" with summary including Decision Trace entities.

---

## Phase 6: Local Environment Setup (10 minutes)

### Step 6.1: Authenticate gcloud

Open terminal on your local machine:

```bash
# Login to GCP
gcloud auth login
```

This opens a browser. Sign in with your Google account.

```bash
# Set your project
gcloud config set project gen-ai-roi-demo
```

Replace `gen-ai-roi-demo` with your actual project ID if different.

```bash
# Set application default credentials (needed for local development)
gcloud auth application-default login
```

This opens browser again. Sign in.

```bash
# Set region
gcloud config set compute/region us-central1
```

### Step 6.2: Verify gcloud

```bash
gcloud config list
```

Should show:
```
[core]
account = your.email@gmail.com
project = gen-ai-roi-demo

[compute]
region = us-central1
```

### Step 6.3: Create .env File

Navigate to your project directory:

```bash
cd ~/projects/gen-ai-roi-demo
```

Create .env file with the content from Colab Cell 30:

```bash
# Option 1: Use a text editor
nano .env
# Paste the content, save (Ctrl+X, Y, Enter)

# Option 2: Use cat (paste the content, then Ctrl+D)
cat > .env << 'EOF'
# GCP Configuration
GOOGLE_CLOUD_PROJECT=gen-ai-roi-demo
GOOGLE_CLOUD_REGION=us-central1

# BigQuery
BIGQUERY_DATASET=ucl

# Vertex AI (Gemini)
GEMINI_MODEL=gemini-1.5-pro-002
GEMINI_LOCATION=us-central1

# Neo4j Aura
NEO4J_URI=neo4j+s://xxxxxxxx.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-actual-password

# Application
LOG_LEVEL=INFO
ENVIRONMENT=development
EOF
```

**âš ï¸ Replace the Neo4j values with your actual credentials!**

### Step 6.4: Create .env.example

```bash
# Copy .env but remove sensitive values
sed 's/NEO4J_PASSWORD=.*/NEO4J_PASSWORD=your-password-here/' .env > .env.example
```

### Step 6.5: Create .gitignore

```bash
cat > .gitignore << 'EOF'
# Environment
.env
.env.local
.env.*.local

# Python
__pycache__/
*.py[cod]
*$py.class
venv/
.venv/
*.egg-info/

# Node
node_modules/
dist/
build/
.next/

# IDE
.idea/
.vscode/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Logs
*.log
logs/

# Testing
coverage/
.pytest_cache/
EOF
```

### Step 6.6: Verify Project Structure

```bash
ls -la ~/projects/gen-ai-roi-demo/
```

Should show:
```
CLAUDE.md
.env
.env.example
.gitignore
docs/
  â””â”€â”€ vc_demo_build_spec_v6.md
```

âœ… **Checkpoint:** .env file exists with correct values, .gitignore exists.

---

## Phase 7: Claude Code Setup (5 minutes)

### Step 7.1: Start Claude Code

```bash
cd ~/projects/gen-ai-roi-demo
claude
```

### Step 7.2: Select Login Method

When prompted:
```
Select: "Anthropic console account"
```

### Step 7.3: Authenticate

```
1. Browser opens to console.anthropic.com
2. Log in (same account where you bought credits)
3. Authorize Claude Code
4. Return to terminal â€” should see confirmation
```

### Step 7.4: Test Claude Code

In Claude Code, type:
```
> Say hello
```

Should get a response.

Then test project context:
```
> Read CLAUDE.md and tell me what the key differentiator is
```

Should mention: **Tab 2 (Runtime Evolution)** and **TRIGGERED_EVOLUTION relationship**.

âœ… **Checkpoint:** Claude Code responds and understands the project context.

---

## Phase 8: Verification (5 minutes)

### Step 8.1: Verify GCP Access

```bash
# Check project
gcloud config get-value project
# Should return: gen-ai-roi-demo

# Check BigQuery
bq ls
# Should show: ucl

# Check BigQuery tables
bq ls ucl
# Should show: kpi_contracts, supply_chain_metrics, finance_metrics, kpi_sprawl_registry
```

### Step 8.2: Verify Firestore

```
1. Go to: https://console.cloud.google.com/firestore
2. Click "Data" tab
3. Should see collections: exceptions, vendors, contracts, policies, patterns, deployments, receipts
```

### Step 8.3: Verify Neo4j (UPDATED v4)

```
1. Go to Neo4j Aura console
2. Click "Query" on your database
3. Run: MATCH (n) RETURN count(n) as nodes
4. Should return: ~39 nodes (includes Decision Trace entities)
```

**Critical verification â€” TRIGGERED_EVOLUTION:**
```cypher
MATCH ()-[r:TRIGGERED_EVOLUTION]->() 
RETURN count(r) as triggered_evolution_count
```
Should return: **3** (or more)

**NEW in v4 â€” Verify Neo4j compatibility:**
```cypher
MATCH ()-[r:CAUSED]->() RETURN count(r) as caused_count
// Should return: 2

MATCH ()-[r:PRECEDENT_FOR]->() RETURN count(r) as precedent_count
// Should return: 2
```

âš ï¸ **If TRIGGERED_EVOLUTION returns 0, the key differentiator is missing!** Re-run Colab Cell 28.
âš ï¸ **If CAUSED/PRECEDENT_FOR return 0:** Re-run Colab Cell 28 (v3 notebook adds these).

### Step 8.4: Verify Vertex AI

```bash
# Quick Python test
python3 << 'EOF'
import vertexai
from vertexai.generative_models import GenerativeModel

vertexai.init(project="gen-ai-roi-demo", location="us-central1")
model = GenerativeModel("gemini-1.5-pro-002")
response = model.generate_content("Say 'Vertex AI is ready'")
print(response.text)
EOF
```

Should print: "Vertex AI is ready" or similar.

### Step 8.5: Verify Decision Trace Schema (UPDATED v4)

```bash
python3 << 'EOF'
from neo4j import GraphDatabase
import os

uri = os.getenv("NEO4J_URI")
user = os.getenv("NEO4J_USERNAME")  
password = os.getenv("NEO4J_PASSWORD")

driver = GraphDatabase.driver(uri, auth=(user, password))

with driver.session() as session:
    # Verify Decision Trace nodes
    result = session.run("""
        MATCH (d:Decision) RETURN count(d) as decisions
    """)
    decisions = result.single()["decisions"]
    
    # Verify TRIGGERED_EVOLUTION relationships
    result = session.run("""
        MATCH ()-[r:TRIGGERED_EVOLUTION]->() RETURN count(r) as evolutions
    """)
    evolutions = result.single()["evolutions"]
    
    # NEW in v4: Verify CAUSED relationships
    result = session.run("""
        MATCH ()-[r:CAUSED]->() RETURN count(r) as caused
    """)
    caused = result.single()["caused"]
    
    # NEW in v4: Verify PRECEDENT_FOR relationships
    result = session.run("""
        MATCH ()-[r:PRECEDENT_FOR]->() RETURN count(r) as precedents
    """)
    precedents = result.single()["precedents"]
    
    print(f"Decision nodes: {decisions}")
    print(f"TRIGGERED_EVOLUTION relationships: {evolutions}")
    print(f"CAUSED relationships: {caused}")
    print(f"PRECEDENT_FOR relationships: {precedents}")
    
    if evolutions > 0:
        print("âœ“ Two-loop schema verified")
    else:
        print("âœ— ERROR: TRIGGERED_EVOLUTION missing â€” re-run Colab Cell 28")
    
    if caused > 0 and precedents > 0:
        print("âœ“ Neo4j compatibility verified")
    else:
        print("âœ— WARNING: CAUSED/PRECEDENT_FOR missing â€” use setup_notebook_v4.py")

driver.close()
EOF
```

âœ… **Checkpoint:** All verifications pass, including TRIGGERED_EVOLUTION and Neo4j compatibility.

---

## ðŸŽ‰ Bootstrap Complete!

You're now ready to start building.

### Your Next Command in Claude Code:

```
> Read docs/vc_demo_build_spec_v6.md and execute Week 1, Day 1:
  Initialize the frontend (Vite + React + TypeScript + Tailwind) and 
  backend (FastAPI + Pydantic) with all dependencies.
  
  CRITICAL: The Decision Trace schema is already in Neo4j. Tab 2 is 
  THE differentiator â€” it should be built first and best.
```

---

## Quick Reference: What You Now Have

| Component | Status | Details |
|-----------|--------|---------|
| GCP Project | âœ… | `gen-ai-roi-demo` |
| BigQuery | âœ… | Dataset `ucl` with 4 tables, seeded with data |
| Firestore | âœ… | 7 collections with seed data |
| Neo4j | âœ… | Graph with **~39 nodes** (including Decision Trace entities) |
| **Decision Trace Schema** | âœ… | **Decision, DecisionContext, EvolutionEvent nodes** |
| **TRIGGERED_EVOLUTION** | âœ… | **The key relationship â€” our differentiator** |
| **CAUSED/PRECEDENT_FOR** | âœ… | **Neo4j-compatible causal chains** |
| Vertex AI | âœ… | Gemini 1.5 Pro accessible (used for narration only) |
| Local Tools | âœ… | Python 3.11+, Node 20+, gcloud |
| Claude Code | âœ… | Authenticated with API credits |
| Project Files | âœ… | CLAUDE.md (v6), .env, build spec (v6) |

---

## Troubleshooting

### "Permission denied" on GCP

```bash
gcloud auth login
gcloud auth application-default login
gcloud config set project gen-ai-roi-demo
```

### "Firestore database not found"

```
1. Go to: https://console.cloud.google.com/firestore
2. Create database in NATIVE MODE (not Datastore)
3. Re-run Colab cells 12-19
```

### "Neo4j connection failed"

```
1. Check URI starts with neo4j+s:// (not neo4j://)
2. Verify password is correct (no extra spaces)
3. Wait 2-3 minutes if database was just created
```

### "TRIGGERED_EVOLUTION returns 0" âš ï¸ CRITICAL

```
1. Go back to Colab
2. Re-run Cell 28 (Create Decision Trace relationships)
3. Verify with Cell 29
4. This relationship is THE key differentiator â€” must exist
```

### Claude Code "API key invalid"

```bash
# Re-authenticate
claude logout  # if available
claude  # start fresh, select Anthropic console account
```

### BigQuery "Dataset not found"

```bash
# Verify project
gcloud config get-value project

# If wrong project, fix it:
gcloud config set project gen-ai-roi-demo
```

---

## What's Next?

The build happens in **2 weeks** (accelerated from 4 weeks due to simplified agent architecture) following the spec in `docs/vc_demo_build_spec_v6.md`:

| Week | Focus | Outcome | Note |
|------|-------|---------|------|
| 1 | **Tab 2 First** + Tabs 1,3,4 | All 4 tabs working | Tab 2 is priority â€” build on Day 1-2 |
| 2 | Polish + Demo Prep | Demo-ready application | Animations, rehearsal, edge cases |

### Why 2 Weeks Instead of 4? (NEW in v5)

The simplified agent architecture reduces backend complexity:
- **Before (v4):** 6 backend services (~1000+ lines)
- **After (v5):** 2 files: agent.py + reasoning.py (~200 lines)

Decision logic is rule-based (4 if-statements). LLM is used for narration only.
The demo proves the ARCHITECTURE, not agent sophistication.

### Build Verification Gates

| Gate | Day | Criteria |
|------|-----|----------|
| **Tab 2 Working** | 2 | Eval gate + TRIGGERED_EVOLUTION visible |
| **All Tabs Working** | 5 | End-to-end flow through all 4 tabs |
| **Animations Polish** | 7 | Graph animates, closed loop steps appear sequentially |
| **Demo Ready** | 10 | Full rehearsal completed, no console errors |

### Reference Implementation

Neo4j's context-graph-demo is the industry reference:
- **Repository:** https://github.com/johnymontana/context-graph-demo
- **Live Demo:** https://context-graph-demo.vercel.app/

Our schema is compatible with their patterns. Our differentiator is TRIGGERED_EVOLUTION.

---

*Bootstrap Sequence v5 | January 2026*
*Key changes: Simplified agent architecture references (2-week build), updated file versions (setup_notebook_v4, build_spec_v6, CLAUDE_v6)*
