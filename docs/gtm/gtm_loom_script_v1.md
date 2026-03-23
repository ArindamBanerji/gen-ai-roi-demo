# Loom Demo Script — SOC Copilot
**Version:** 1.0 · March 2026
**Length:** 3 minutes
**Audience:** CISO / VP Security — first exposure to the product
**Goal:** Leave them thinking: "I understand what this does and I want to see it in my environment."

---

## Pre-Recording Setup

- Fresh browser session (no cached state)
- Backend running, Neo4j running, seed data loaded
- At least one alert with `identity_tier=executive` in the queue (triggers referral R1)
- IKS > 0 (a few decisions recorded)
- Tab 1 open, alert queue visible

---

## Script

---

### [0:00–0:15] The Alert Arrives

*Start on Tab 1. Alert queue is visible. Click on a credential access alert.*

> "Here's what a SOC analyst sees when they open SOC Copilot. An alert arrives — credential access, Singapore login. I click it."

*Tab 3 opens. Factor breakdown visible.*

> "Immediately: six factors that explain the recommendation. Travel match: 0.89 — no travel record to Singapore. Device trust: 0.71 — MDM enrolled. Threat intel: 0.62 — no active IOC match."

---

### [0:15–0:30] Show Your Work

*Point to the factor bars and kernel weights.*

> "This is not a black box. Every number has a source. Every weight is calibrated to this environment's specific noise profile — device_trust is weighted 1.56 because your MDM coverage is good. travel_match is weighted 0.31 because your travel data has gaps."

> "The recommendation: Escalate at 87% confidence. Here's why, in plain English."

*Point to NL explanation.*

---

### [0:30–0:50] Referral Rules

*Click on an alert that has should_refer=true — the executive account alert.*

> "Now watch this one. Same factor breakdown. But there's something different."

*Amber referral callout is visible.*

> "The system scored this as suppress at 91% confidence. But it's an executive account. Company policy says a human reviews those — regardless of confidence. So it refers to analyst."

> "Auto-approve overridden. That's not uncertainty. That's policy. The confidence gate and the referral rules are two different things — and they should be."

---

### [0:50–1:10] The System is Getting Smarter

*Switch to Tab 2.*

> "This is Tab 2. Institutional Knowledge Score: 47.3. At deployment it was zero. One hundred is full adaptation."

*Point to the IKS trend chart.*

> "Every verified analyst decision moves this number. 847 decisions recorded. The system has learned this firm's specific patterns — which categories to trust, which factors are reliable here, which aren't."

> "This is the number you show your board when they ask: is the AI getting better? Yes — 47.3 and climbing."

---

### [1:10–1:25] Auto-Approve — What Gets Handled Automatically

*Switch to Tab 4, point to auto-approve breakdown.*

> "40% of alerts are now handled automatically — at 85%+ confidence, in calibrated categories. Cloud infrastructure scans. Known-benign IOC matches. Routine suppresses."

> "Insider threat: 2% auto-approve. By design. The system doesn't touch the high-risk categories until it's earned it."

> "That's 352 analyst-minutes saved this week. $26,400 annualised at current volume."

---

### [1:25–1:40] Shadow Mode — Try Before You Trust

*Point to shadow mode indicator if visible, or describe.*

> "We don't ask you to trust it on day one. Shadow mode runs for 30 days alongside your analysts — silently. No recommendations shown. We measure agreement rate."

> "At the end of 30 days: a report. 'The system agreed with your analysts on 74% of alerts. Here are the 12 cases where it disagreed, with factor breakdowns for each.' You review. You decide. You click Activate."

> "It never goes live without your explicit sign-off."

---

### [1:40–1:55] The ROI

*Point to Tab 4 ROI calculator.*

> "The ROI calculator uses your actual numbers — your volume, your cost per analyst hour, your auto-approve rate. Not industry benchmarks. Your data."

> "At 200 alerts per day, 8 analysts, 40% auto-approve: $70,000 per month in recovered analyst time. That's before you count the 12 true positives your team would have missed."

---

### [1:55–2:10] Consistency — The Unconditional Claim

*No screen action — face to camera or static screen.*

> "One claim I'll make without any qualifiers: this system gives the same recommendation every time for the same inputs. Day shift, night shift, Monday morning, Friday at 5pm — the same answer."

> "Your analysts don't. Not because they're bad — because they're human. One consistent system plus your analysts is better than your analysts alone."

---

### [2:10–2:25] Your Intelligence, Your Moat

> "After 1,000 decisions at your firm, this system knows what YOUR firm has learned about YOUR environment. The kernel weights show which factors are reliable in your setup. The centroids encode how YOUR analysts handle each category."

> "A competitor with the same open-source code starts with nothing. You have 1,000 decisions of institutional judgment. That's not replicable."

---

### [2:25–2:40] The One Question

> "After 1,000 decisions, ask your current security tools: how did you get smarter? What specifically changed in how you handle insider threat alerts? Which factors do you now trust most in this environment?"

> "Only one system can answer that question. And the answer is auditable, exportable, and yours."

---

### [2:40–3:00] Close

> "30-day shadow mode pilot. Your analysts work normally. We measure agreement rate. If it's below 75% at Day 30, we extend — no charge."

> "The DPA is ready. The pilot playbook is ready. The only thing needed is a SIEM connection and 30 days."

*End on product screen with IKS visible.*

---

## Key Numbers to Have Ready

| Number | Value | Where it appears |
|---|---|---|
| IKS example | 47.3 | Tab 2 header |
| Auto-approve rate | 40% | Tab 4 |
| Decisions recorded | 847 | Tab 2 |
| Time saved (weekly) | 352 analyst-minutes | Tab 4 |
| Annual ROI (200 alerts/day) | ~$70K/month | Tab 4 ROI calculator |
| Agreement rate (shadow) | 74-78% | Shadow report |
| Referral precision (rules) | 50.7% at 72.7% DR | Internal — don't mention in demo |

---

## What NOT to Say

- "The AI decided" — say "the system recommended"
- Any unqualified accuracy number — always add condition ("at 85%+ confidence in calibrated categories")
- "Real-time" — the pipeline is fast but not sub-millisecond
- "It learns from all customers" — it learns only from YOUR decisions
- Any specific customer names

---

*Loom Script v1.0 · Compounding Intelligence Platform · March 2026*
