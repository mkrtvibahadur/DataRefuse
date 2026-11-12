# DataRefuse

A local Flask prototype for exploring app data practices and matching user concerns to relevant passages in official privacy-policy text.

## Features
- 16 apps across food & shopping, social & communication, travel & mobility, and entertainment & video.
- App data-practice summaries and alternative services to investigate.
- Policy Analyzer: choose an app, type a concern in everyday language (for example, "location tracking"), and DataRefuse retrieves the configured policy page where possible.
- Query expansion for related wording (for example, location → GPS, geolocation, coordinates, device location).
- Matching policy passages with matched terms and cautious plain-language explanations.
- Data-rights request drafts and manual request tracking.

## Run locally (Mac)
```bash
python3 -m pip install -r requirements.txt
python3 app.py
```
Open http://127.0.0.1:5001

If port 5001 is occupied, set another port:
```bash
PORT=5002 python3 app.py
```

## Important limitations
- The analyzer retrieves the official URL configured for each app. Some sites block automated access or load content dynamically; retrieval can be incomplete.
- Matches are first-pass text matching, not a legal opinion and not proof of wrongdoing.
- Plain-language explanations are cautious rule-based descriptions, not legal advice.
- App data summaries and alternatives are starting points for research and must be checked against current official policies before being presented as verified findings.
- Request drafts are not automatically submitted; the tracker is user-maintained.

## Alternative options
Each app profile includes practical alternatives to investigate, including privacy-oriented apps, offline tools, direct ordering, public transport and locally controlled services. These are not certified as data-free; users should compare current policies and trade-offs.
