# Tandem Explorer
## Made by Fabrice TRA

---

## Live demo : no need to install the next Dashboard

**https://dashboard-theta-lemon-69.vercel.app**

---

## Quick Start

```bash
# 1 - Install test dependencies
cd analysis
pip install -r requirements.txt

# 2 - Run the test suite
pytest tests/ -v

# 3 - Run the analysis
python3 analyze.py
# → Writes analysis/output/insights.json

# 4 - Copy insights to dashboard and start
cp output/insights.json ../dashboard/public/insights.json
cd ../dashboard
npm install
npm run dev
# → http://localhost:3000
```

---

## Project Structure

```
tandem-technical-test/
├── data/
│   └── sessions.json          # Source data (244 events, JSONL)
├── analysis/
│   ├── analyze.py             # Analysis pipeline (stdlib only)
│   ├── requirements.txt       # pytest
│   ├── pyproject.toml         # pytest configuration
│   ├── tests/
│   │   ├── conftest.py
│   │   └── test_analyze.py    # 54 unit + integration tests
│   └── output/
│       └── insights.json      # Generated output consumed by dashboard
├── dashboard/                 # Next.js 16 dashboard (App Router)
│   ├── app/
│   ├── components/
│   ├── lib/types.ts
│   └── public/insights.json   # Copy of analysis output
└── README.md
```

---

## Technical Choices

### Analysis - Python (stdlib only)

Pure standard library: `json`, `collections`, `datetime`, `os`. No pandas - the dataset is 244 events. Reaching for a dataframe for this would be over-engineering. The pipeline is explicit and readable: each step is an isolated pure function (input → output), which also makes every function directly unit-testable without mocks.

The output contract (`insights.json`) is the interface between the two parts of the monorepo. This separation means the analysis can be rerun independently and the dashboard stays purely presentational.

### Dashboard - Next.js 16 + TypeScript + Recharts

Next.js App Router generete with my AI boilerplate with server-side data loading: `insights.json` is read at build time via `fs.readFile` in a server component, so the dashboard is fully static.


---

## Product Decisions

### What I focused on and why

**Revenue impact first.** The data covers a busy morning on an e-commerce site, so the most valuable question is: where is money being lost right now? I prioritised checkout friction above everything else : a broken checkout is a direct revenue leak, not a UX annoyance. That's why issue detection runs before behavior surfacing in the pipeline: bugs that block purchases outrank interesting observations.

**Drill-down over aggregates.** A product manager reading "8 sessions hit an error at checkout" needs to be able to show that to an engineer within the same tool. I built the session timeline drill-down directly into each issue card so the path from finding to fix is as short as possible.

**Behaviors as hypotheses, not conclusions.** 244 events is a small sample. I chose to surface cross-session patterns (negative review then purchase, cart-then-logout, non-buyer comments) as signals to investigate rather than as definitive facts. Each behavior card includes an "Insight" that frames the finding as an opportunity, not a verdict, because acting on statistically weak data without that caveat leads to bad product decisions.

**Common journeys as normalized paths.** Raw session paths are too granular to be comparable across 30 sessions. I normalized product detail pages to `/products/*` so that sessions going through different products are grouped into the same pattern. This surfaces the actual shape of user navigation (e.g., `/ → /products → /products/* → /cart → /checkout`) rather than a list of one-off paths.

**No external dependencies on the analysis side.** The pipeline produces a single JSON file that the dashboard reads statically. This means the analysis can be re-run on new data without touching the frontend, and the dashboard can be deployed as a static site with no backend. Given the scope of the task, this tradeoff maximises reliability and simplicity over flexibility.

---

## Analysis Approach

### 1. Data Loading & Cleaning
Parse the JSONL line by line, handle malformed lines gracefully, flag events with missing timestamps without dropping them.

### 2. Session Reconstruction
Group events by `session_id`, sort by `event_time` (nulls last). Build journey objects: ordered page sequences, error flags, completion status.

### 3. Funnel Analysis
Count sessions reaching each conversion step sequentially (homepage → products → cart → checkout → order placed). A session drops out at the first step it didn't reach, guaranteeing monotonically decreasing counts and meaningful drop-off rates. Separate checkout outcomes: completed, cancelled, retried-then-dropped, silent drop.

### 4. Issue Detection based on my experience with Tuzzo, bim! an FLEXX
Rule-based detection of 5 pattern types:
- Checkout errors leading to abandonment
- Sessions starting directly at `/checkout` without a cart
- FAQ answers failing to load (important when users want to know more about your service)
- Language switcher errors on `/settings`
- `/random` page causing user confusion

Each issue includes: severity, description, affected session IDs, and a product recommendation.

### 5. Behavior Surfacing
Cross-session patterns that are interesting but not necessarily bugs:
- Users leaving negative product comments then completing purchases
- Cart-then-logout sessions (recovery email opportunity)
- Multilingual users: higher engagement, more friction
- `/random` seems to be a dead page they use to search
- Product comments left by non-buyers, weakening social proof

---

## What I Would Do With More Time

**On the analysis:**
- Build a proper session graph to detect loops and back-navigation patterns
- Time-delta analysis between events to identify where users hesitate
- Cluster users by behavior profile (explorers vs. direct buyers vs. confused users)
- Statistical significance tests : 244 events is a small sample, findings should be presented as hypotheses to validate
- Proper sentiment analysis on product comments because the current keyword list is fragile and language-dependent. A lightweight model (VADER, TextBlob, or an LLM call) would generalise to any product vocabulary and surface nuance the keyword approach misses
- Cross-session user journeys : sessions are currently analysed independently, but the same user may abandon in one session and convert in another. Stitching sessions by `user_id` would reveal recovery patterns and true conversion rates at the user level, not the session level


**On the dashboard:**

- Sankey diagram for flow visualization between pages
- Click-through to a full session replay-style timeline
- Export to PDF/CSV for sharing with non-technical stakeholders

Many other things can be done, and I will be happy to talk about it in details on the debrief.

Warning: 
In this project, I used AI to :
- Write more rapidly the documentation because of the time I had to respect
- Test classes because it gave me more time to work on analysis and data displaying
- Generate the boilerplate of the dashboard because I was very important to me to show the analysis in a visual way.

