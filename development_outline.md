# Multi-Agent Business Research Copilot (Hackathon MVP)

## Goal

Build a business-oriented multi-agent system that turns a natural-language growth request into a ranked lead list with actionable next steps.

## Current Implementation Status

The repository has already moved beyond the initial outline in several important ways:

- LangGraph workflow orchestration is implemented
- planner and reasoning steps support structured LLM-backed execution with deterministic fallback
- search now uses a provider interface:
  - `SEARCH_BACKEND=mock` is implemented
  - `SEARCH_BACKEND=live` is implemented with richer same-domain page fetching
  - `SEARCH_BACKEND=tavily` is implemented for production-style search discovery when `TAVILY_API_KEY` is set
- validation is domain-aware and distinguishes:
  - `cross_domain`
  - `same_domain_only`
  - `insufficient`
- lightweight human-review flags and a review queue are included in outputs
- each run now generates matched output pairs:
  - `output_<run_id>.csv`
  - `summary_<run_id>.md`
  - `result_<run_id>.json`
- a lightweight API layer is implemented:
  - `/`
  - `/health`
  - `/capabilities`
  - `/investigate`
- a lightweight browser UI is implemented on top of the API
- investigation works across:
  - companies
  - people
  - products

Still pending for the next phase:

- stronger semantic extraction from live pages
- source reputation scoring
- richer human review workflow
- auth/background job support if the API is hardened beyond demo usage

Target demo:

```bash
python main.py "Find 20 SaaS companies in NYC that likely need AI automation help"
```

Output:
- `output.csv`
- `summary.md`
- 5-20 usable leads with contact clues, priority scores, outreach angles, and source evidence

Core story for judges:

> We are not just collecting data. We are simulating a lightweight business development team with specialized AI agents that research, qualify, and prioritize opportunities.

---

## Why This Works In A Business Hackathon

Business judges usually care about:
- clear customer value
- time saved versus manual work
- decision quality, not just raw data volume
- a believable path to revenue
- a demo that feels like a product, not a script

So the MVP should answer one business question well:

> Who should I sell to first, and why?

---

## Product Positioning

### Problem

Early-stage founders, agency teams, and B2B sales reps waste hours manually searching for prospects, checking websites, guessing fit, and drafting outreach notes.

### Solution

A multi-agent business research copilot that:
- understands an ICP or growth goal
- finds candidate companies
- extracts structured signals
- reasons about likely buyer roles when exact titles are missing
- scores which leads are most promising
- explains the reason behind each recommendation
- attaches source evidence for every important claim

### Ideal User

- startup founders doing outbound
- consulting firms sourcing clients
- GTM teams validating new markets

### Business Value

- save 3-5 hours of manual research per campaign
- improve lead quality by ranking instead of dumping raw results
- create a reusable workflow for outbound prospecting

---

## MVP Scope

Keep the system small, but make the agent roles visible.

### Input

User provides:
- target market or ICP
- geography
- optional buyer role
- optional business need

Example:

```bash
python main.py "Find fintech startups in New York with small teams and signs they may need workflow automation"
```

### Output

Each row should ideally include:
- `company`
- `website`
- `location`
- `industry`
- `employee_estimate`
- `target_role_requested`
- `best_contact_role_found`
- `role_match_type`
- `pain_point_signal`
- `why_now`
- `reasoning_summary`
- `confidence`
- `lead_score`
- `source_urls`

Also generate a simple markdown summary:
- total leads found
- top 5 leads
- common pain points
- suggested outreach angle

Important behavior:
- if the requested title is not found, infer the closest relevant role
- every inferred field must point back to source evidence
- separate `observed facts` from `agent inference`

---

## Multi-Agent Design

Use 4 focused agents plus 1 orchestrator. That is enough to feel like a real multi-agent system without overbuilding.

### 1. Orchestrator Agent

Responsibility:
- parse the user request
- define the search plan
- call other agents in order
- merge outputs into the final dataset

### 2. Research Agent

Responsibility:
- generate search queries
- discover candidate company URLs
- collect source pages

### 3. Extraction Skill

Responsibility:
- read page content
- extract company facts and buyer clues
- normalize fields into JSON

### 4. Qualification Skill

Responsibility:
- infer likely pain points
- determine whether the lead matches the ICP
- reject weak or irrelevant leads

### 5. Reasoning Agent

Responsibility:
- handle missing or incomplete information
- infer the best alternative contact when the requested role is absent
- explain why that alternative role is relevant
- label which outputs are direct evidence versus inferred conclusions

Example:
- requested role: `CTO`
- not found in sources
- inferred fallback: `VP Engineering` or `Head of Platform`
- rationale: closest technical budget owner based on team page and job posts

### 6. Scoring Skill

Responsibility:
- rank leads by business value
- produce a score and justification
- suggest an outreach angle

---

## End-To-End Flow

```text
User Request
-> Orchestrator interprets ICP
-> Research Agent finds candidate companies
-> Extraction Skill builds structured profiles
-> Qualification Skill filters and explains fit
-> Reasoning Agent fills gaps and selects fallback roles
-> Scoring Skill ranks opportunities
-> Save CSV + summary
```

Important:
- keep the flow mostly linear
- limit retries
- avoid memory, long planning loops, or agent-to-agent chatter beyond what helps the demo
- make reasoning explicit and inspectable, not hidden inside one opaque output

---

## Technical Build Plan

## Step 1. CLI Entry

`main.py`
- accept one natural-language query
- create a run ID
- call the orchestrator
- save outputs

Success check:

```bash
python main.py "test"
```

## Step 2. Orchestrator

`orchestrator.py`
- convert the request into a structured brief:
  - target industry
  - geography
  - target role
  - likely business problem
- call downstream agents in sequence

Suggested brief schema:

```json
{
  "market": "",
  "geography": "",
  "buyer_role": "",
  "business_need": "",
  "search_queries": []
}
```

## Step 3. Research Agent

`agents/research_agent.py`
- expand search queries
- search the web
- return top candidate URLs
- deduplicate aggressively

Target:
- 10-20 candidate URLs

## Step 4. Extraction Skill

`skills/extraction_skill.py`
- scrape page HTML or visible text
- extract structured company info
- capture source evidence for traceability

Minimum schema:

```json
{
  "company": "",
  "website": "",
  "location": "",
  "industry": "",
  "observed_roles": [],
  "pain_point_signal": "",
  "evidence": [
    {
      "field": "",
      "value": "",
      "source_url": "",
      "snippet": ""
    }
  ]
}
```

## Step 5. Qualification Skill

`skills/qualification_skill.py`
- decide if the company matches the ICP
- assign `fit_label`: `high`, `medium`, or `low`
- give a one-sentence reason

## Step 6. Reasoning Agent

`agents/reasoning_agent.py`
- compare the requested buyer role against observed roles
- infer the closest relevant contact if the exact title is missing
- produce a short explanation with confidence
- mark each output as either `observed` or `inferred`

Suggested reasoning schema:

```json
{
  "target_role_requested": "CTO",
  "best_contact_role_found": "VP Engineering",
  "role_match_type": "inferred_adjacent",
  "reasoning_summary": "No CTO was found, but VP Engineering appears to be the closest technical decision-maker.",
  "confidence": 0.78
}
```

Fallback examples:
- `CTO` -> `VP Engineering`
- `Head of AI` -> `Director of Data Science`
- `COO` -> `Head of Operations`

## Step 7. Scoring Skill

`skills/scoring_skill.py`
- assign `lead_score` from 1-100
- generate `why_now`
- suggest one outreach hook

Example scoring logic:
- +30 if industry matches target
- +20 if geography matches
- +20 if a relevant pain point appears
- +15 if buyer role is visible
- +15 if the website suggests growth or operational complexity

## Step 8. Save Deliverables

Save:
- `output_<run_id>.csv`
- `summary_<run_id>.md`

`summary.md` should include:
- what was searched
- how many leads were found
- top 5 ranked opportunities
- a one-paragraph market takeaway
- a short section called `Reasoning Notes`
- a short section called `Evidence Trail`

---

## Recommended Folder Structure

```text
project/
  main.py
  orchestrator.py
  workflows/
    research_workflow.py
  state/
    graph_state.py
  agents/
    planner_agent.py
    research_agent.py
    reasoning_agent.py
  skills/
    extraction_skill.py
    qualification_skill.py
    validation_skill.py
    scoring_skill.py
    formatting_skill.py
  tools/
    search_provider.py
    agent_tools.py
  llm/
    client.py
    config.py
    prompts.py
    schemas.py
    planner_service.py
    reasoner_service.py
  utils/
    schemas.py
    query_parser.py
    mock_data.py
    formatters.py
  output/
    output_<run_id>.csv
    summary_<run_id>.md
```

---

## Demo Narrative

Do not pitch this as "a scraper."

Pitch it as:

> An AI business development team in a box.

Live demo flow:

1. Enter a business request in plain English.
2. Show each agent's role briefly in the logs.
3. Show one case where the requested title was not found.
4. Show how the reasoning agent selected the nearest relevant role.
5. Open the ranked CSV.
6. Open `summary.md`.
7. Explain why the top lead was ranked first and which sources support it.

One-line pitch:

> This system acts like a mini GTM team: one agent researches, one extracts signals, one qualifies fit, and one prioritizes where a human should focus first.

Better version for your use case:

> This system does more than crawl. It reasons over incomplete business data, finds the closest decision-maker when an exact title is missing, and shows the evidence behind every recommendation.

---

## Judge-Friendly Differentiators

If you have time, add one of these:
- a confidence score for each lead
- an outreach email draft for the top 3 leads
- a simple Streamlit UI
- a side-by-side comparison between manual research and agent output

Best optional feature:

> Generate a personalized outreach opener for the top-ranked company.

That makes the output feel immediately monetizable.

High-value optional feature:

> Add clickable evidence links and snippets for each ranked lead so a judge can audit the agent's reasoning in seconds.

---

## Constraints

- runtime under 90 seconds
- 10-20 URLs max for the MVP
- prefer reliability over breadth
- one strong workflow is better than five weak features
- multi-agent should be visible in architecture and logs, but still simple to debug
- every important field should be traceable to at least one source URL

---

## Debug Order

1. Research agent returns URLs.
2. Extraction skill returns valid JSON plus evidence objects.
3. Qualification skill rejects obvious bad leads.
4. Reasoning agent handles missing titles correctly.
5. Scoring skill produces explainable rankings.
6. Final CSV and summary are saved correctly.

Never debug all agents at once.

---

## Build Strategy

### Must Have

- working end-to-end pipeline
- at least 3 distinct agent roles
- ranked lead output
- clear business use case
- fallback role reasoning when exact contacts are missing
- source-backed evidence for key claims

### Nice To Have

- markdown summary
- outreach hooks
- lightweight UI

### Do Not Build

- long-term memory
- autonomous loops
- complicated agent negotiations
- too many tools or integrations

---

## Principle

> Business impact + clear agent roles + working demo beats technical complexity.

Ship the smallest multi-agent system that produces a ranked business decision and can explain how it reached it.
