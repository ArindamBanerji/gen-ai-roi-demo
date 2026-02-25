# NBP Prompt — CGA-04: Enterprise Scaling: Candidate Filtering Pipeline

## Instructions for NBP

Create a horizontal pipeline/funnel infographic showing how cross-graph attention scales to enterprise graph sizes. The pipeline flows LEFT to RIGHT, starting with a large input block (150,000 raw entity pairs) and progressively narrowing through four filtering stages to a smaller output block (15–25K evaluated pairs). The visual metaphor is a funnel — wide on the left, narrow on the right — showing that the math stays the same but the candidate set shrinks at each stage.

This is a technical diagram for a published mathematical paper on cross-graph attention in enterprise AI. The audience is senior engineers, architects, and technical investors.

## Critical Instructions

- ALL 6 BLOCKS MUST BE PRESENT (1 input + 4 filters + 1 output) ← MUST INCLUDE
- Flow is strictly LEFT → RIGHT with arrows between every stage ← MUST INCLUDE
- The funnel/narrowing effect must be visually obvious — the input block should be visually the tallest/widest, each filter stage progressively shorter/narrower, and the output block should be compact ← MUST INCLUDE
- Each filter stage must show its name, mechanism (short phrase), and approximate reduction ← MUST INCLUDE
- Caption text at bottom: "The math doesn't change. The candidate set does." ← MUST INCLUDE
- Dark theme, consistent with existing blog graphics (#0f172a background)

## Layout

Use a diagram_flow archetype with horizontal left-to-right progression:

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  INPUT   │ →  │ FILTER 1 │ →  │ FILTER 2 │ →  │ FILTER 3 │ →  │ FILTER 4 │ →  │  OUTPUT  │
│  (tall)  │    │          │    │          │    │          │    │          │    │ (compact)│
└──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘
```

- Title banner at top, centered
- Six blocks in a single horizontal row with arrows between them
- Input block (leftmost): largest, uses accent color to draw the eye
- Four filter blocks: progressively smaller or visually narrowing, each a different shade
- Output block (rightmost): compact, uses a green/success color
- Caption at bottom center
- Equation reference chip below title: "CrossAttention(Gᵢ, Gⱼ) = softmax(Eᵢ · Eⱼᵀ / √d) · Vⱼ"

## Content

**Title:** Enterprise Scaling: Candidate Filtering Pipeline

**Subtitle:** Four filters reduce candidate pairs before cross-attention computes — the math stays unchanged

**Equation Chip:** Eq. 6: CrossAttention(Gᵢ, Gⱼ) = softmax(Eᵢ · Eⱼᵀ / √d) · Vⱼ

**Block 1 — Input (leftmost, largest)**
- Label: "Raw Pairs"
- Metric: "150,000"
- Detail: "6 domains × m² entities"
- Detail: "Full Cartesian product"
- Visual emphasis: This is the widest/tallest block

**Block 2 — Filter: Candidate Blocking**
- Label: "Candidate Blocking"
- Mechanism: "Shared structural keys"
- Examples chip: "same asset class · same geography · same process"
- Reduction: "→ ~45K pairs"
- Reduction note: "60–80% filtered"

**Block 3 — Filter: Time-Window**
- Label: "Time-Window"
- Mechanism: "Freshness & recency"
- Examples chip: "active entities only · Four Clocks encoding"
- Reduction: "→ ~30K pairs"

**Block 4 — Filter: ANN Index**
- Label: "ANN Index"
- Mechanism: "Top-K nearest neighbors"
- Examples chip: "LSH · HNSW graphs · pre-indexed embeddings"
- Reduction: "→ ~20K pairs"

**Block 5 — Filter: Governance**
- Label: "Governance"
- Mechanism: "Eligibility rules"
- Examples chip: "legal hold · clearance scope · pre-adjudicated"
- Reduction: "→ 15–25K pairs"

**Block 6 — Output (rightmost, compact)**
- Label: "Evaluated Pairs"
- Metric: "15–25K"
- Detail: "Full attention computed"
- Detail: "< 2 sec on commodity hardware"
- Visual emphasis: green/success tone — this is where discoveries happen

**Caption (bottom, centered, italic):**
"The math doesn't change. The candidate set does."

**Source reference (small, bottom-right):**
Cross-Graph Attention: Mathematical Foundation — Section 6, Property 1

## Theme & Style

- Mode: Dark
- Background: #0f172a (slate-900, matches existing blog graphics)
- Input block: bright accent color (#f59e0b amber or #ef4444 red-warm) — draws the eye to the scale of the raw problem
- Filter blocks: gradient from cooler blue (#3b82f6) through teal (#0ea5e9) to cyan (#06b6d4) — visually cooling/narrowing
- Output block: green (#4ade80) — success, same green used for UCL in other blog graphics
- Arrows: white or light gray, with subtle glow
- Text: white on dark backgrounds, dark on light chip backgrounds
- Equation chip: monospace font, subtle border, placed below title
- Caption: italic, lighter color (#94a3b8), centered at bottom

## Constraints

- Maximum 6 blocks (already specified above — no more)
- Keep text concise — this is a visual diagram, not a text slide
- Each filter block should have exactly 3 text elements: name, mechanism, reduction
- The funnel narrowing must be the dominant visual impression — a viewer should instantly see "big on left, small on right"
- Arrows between all adjacent blocks — these are required, not optional
- No icons needed — the funnel shape and color gradient carry the visual story
