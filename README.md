# BeeFriendly — AI Visual Studio

Sign in → type any topic in plain English → get presentation-ready
diagrams and AI images in seconds. Built for students and
professionals who need visuals for slides, reports and notes.

## Features

- **User accounts** — SQLite storage with PBKDF2-hashed passwords
  (salted, constant-time verification)
- **Recruiter / HR portal** — invite-code access to a branded showcase page
  that presents the project to hiring managers
- **14 visual types** — Flowchart · Mind Map · SWOT · Timeline ·
  Comparison Table · Cycle/Process · Architecture · Concept Tree ·
  Fishbone · Decision Tree · Org Chart · Kanban · Journey Roadmap ·
  Layered Pyramid
- **Two design engines**
  - *Pro Infographic* — Gemini designs Napkin-style HTML/CSS cards,
    rendered to PNG via headless Edge/Chrome
  - *Standard* — classic Mermaid diagrams via mermaid.ink
- **Custom colour themes** — preset palettes or pick your own
  card/border/line/text colours
- **Reference images** — upload an example diagram or picture;
  Gemini studies its structure/style and recreates something similar
- **AI Image Studio** — text-to-image generation with art styles and
  optional style-reference image
- **Advanced mode** — edit Mermaid code by hand, re-render live
- **Auto-repair loop** — broken Mermaid is fixed automatically by
  feeding errors back to Gemini
- **Session gallery** — reopen anything you generated this session
- **Exports** — PNG and SVG downloads

## Tech Stack

| Layer | Tool |
|---|---|
| UI | Streamlit |
| Auth | SQLite + PBKDF2-HMAC-SHA256 |
| AI | Google Gemini REST API (model-fallback chain, thinking disabled) |
| Pro rendering | Headless Edge/Chrome screenshots |
| Diagrams | Mermaid.js via mermaid.ink |

## Setup (Windows)

1. Install Python 3.10+ — https://www.python.org/downloads/
2. Get a free Gemini API key — https://aistudio.google.com/apikey
3. Save the key permanently:
   ```
   py save_key.py
   ```
4. Run:
   ```
   streamlit run app.py
   ```

## Recruiter / HR portal

On the sign-in screen there is a **Recruiter / HR** tab. A recruiter needs
their name, email and a chosen password, plus the **invite code**
(default `HIRE-BEE-2026`).

The invite code can be changed for production with the environment variable
`BEEFRIENDLY_HR_CODE`. HR logins are stored with `role = 'hr'` and are shown
a branded showcase page instead of the full studio.

## Deploy to Streamlit Community Cloud (free)

1. Push this folder to a GitHub repository.
2. Go to https://share.streamlit.io and sign in with GitHub.
3. Create a new app → select your repo → main file path:
   `app.py`
4. After deploy: **Settings → Secrets** and paste:
   ```toml
   GEMINI_API_KEY = "your-key-here"
   ```
   The key stays permanent on the cloud too — never committed to git.

## Project Layout

```
app.py        Streamlit UI (auth, studios, gallery)
ai.py         Gemini REST client (text/vision/image)
diagrams.py   Visual pipelines (Mermaid, HTML→PNG, tables)
auth.py       User database + password hashing
assets/       Logo files
save_key.py   One-time API key setup helper
```
