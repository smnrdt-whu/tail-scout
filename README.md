# RoboXY Tail-Spend Sourcing Agent

Streamlit MVP for the Lio Sales Engineering Super Day case study:
**competitive quotes for low-value procurement (tail spend).**

## The problem

RoboXY manufactures robotics components. For needs under ~€20,000 (e.g. painting services), requesters typically contact a single known supplier. Procurement skips competitive quotes because manual effort outweighs expected savings (€500–€1,000 per case, 200–300 cases/year).

## What this MVP does

1. Takes a well-specified requirement (no spec engineering)
2. Matches & ranks suppliers from the internal database
3. Drafts RFQ emails
4. **Human-in-the-loop:** approve before anything is sent
5. Simulates incoming quotes and compares them (scorecard)
6. Recommends the most competitive option — human confirms award
7. Mock “Submit to SAP” for the secondary ERP pain point

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py --server.port 8512
```

Open [http://localhost:8512](http://localhost:8512).

## Deploy on Streamlit Community Cloud

1. Push this repo to GitHub
2. At [share.streamlit.io](https://share.streamlit.io) → **New app**
3. Main file: `app.py`, Python 3.11+
4. Deploy

No API keys required — supplier matching and quote simulation are deterministic so the live demo works offline.

## Demo path (≈ Super Day walkthrough)

1. **Übersicht** — pain point, annual savings potential (~€125–250k)
2. Select `REQ-2026-0142` (hall painting) → **Sourcing-Assistent**
3. Walk steps: Bedarf → Lieferanten → E-Mails freigeben → Angebote → Vergleich → SAP
4. Highlight HITL gates and the savings vs. the familiar single-supplier path

## Project layout

```
app.py                  # Streamlit UI
src/agent.py            # Matching, RFQ drafts, quote sim, comparison
src/models.py           # Domain types
src/state.py            # Session + data loading
data/suppliers.json     # Mock supplier master data
data/sample_requests.json
requirements.txt
.streamlit/config.toml
```

## Customer notes reflected in the product

| Note | In the MVP |
|------|------------|
| Company RoboXY, robotics parts | Branding & copy |
| Need → docs → suppliers → email ping-pong → buy | Wizard steps |
| No review under €20k / no comparison quotes | Explicit warning + agent value prop |
| Example: painting service | Primary demo request |
| Humans at key decisions (send email) | Approval step before send |
| Later full automation | Roadmap on “Über den MVP” |
