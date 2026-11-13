# DataRefuse

A Flask prototype that helps people examine app privacy information, search policy text for concerns, compare alternative tools and prepare data-rights request drafts.

## Run locally
1. Install dependencies: `python3 -m pip install -r requirements.txt`
2. Run: `python3 app.py`
3. Open the local URL shown in the terminal (usually `http://127.0.0.1:5001`).

## Deploy on Render
- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn app:app`
- Deploy the repository root containing `app.py`, `requirements.txt`, `templates/` and `static/`.

## Current features
- App directory and profiles across four categories.
- Data categories to investigate and official policy links.
- Policy Analyzer with policy retrieval, document extraction and rule-based keyword matching.
- Manual ChatGPT handoff: copy a question and matching policy passages, then paste them into ChatGPT. This is not an integrated OpenAI API or chatbot.
- Data Rights Assistant that drafts requests to refuse optional data use, withdraw consent or request deletion of eligible data. It does not submit requests.
- Manual request tracker.
- Location-permission checklist for iPhone and Android. The site does not scan the device or read live GPS permissions.
- Alternative tools for comparison. They are not certified as data-free or less data-intensive.

## Limitations
Policy retrieval can fail when a site blocks automated access or renders content dynamically. Keyword matching can miss context or return irrelevant passages. Results are research leads, not legal advice, verified audits or proof of a violation. App profiles identify categories worth checking; they do not prove that every app collects every listed category. Tracker statuses are user-updated and not verified by platforms.

## Privacy and data
The prototype uses SQLite for request-tracker records. Do not enter sensitive personal information. On a free Render instance, local files may not persist across service restarts or redeployments unless persistent storage is configured.

See `DESIGN.md` for the visual design system.
