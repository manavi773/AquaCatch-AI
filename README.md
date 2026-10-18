# AquaCatch AI 🎣

> **Real-time water quality & fishing safety advisor for artisanal fishermen**  
> Powered by **Gemini Vision AI** + **Open-Meteo live weather** + **IP Geolocation**

---

## Features

- 📷 **Photo Analysis** — Upload a water body or fish catch photo for instant AI-powered evaluation
- 🌤️ **Live Weather** — Real-time temperature, rainfall, wind, humidity via Open-Meteo (no API key needed)
- 📍 **Auto Geolocation** — 3-tier IP geolocation (ipapi.co → ip-api.com → ipwho.is) with GPS override
- 🌐 **Multilingual** — UI and AI reports in English, ಕನ್ನಡ, हिन्दी, தமிழ், తెలుగు
- ✅ / ⚠️ / 🚨 **Safety Verdict** — SAFE, CAUTION, or HIGH RISK with actionable advice

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python + Flask |
| AI | Google Gemini Vision (`gemini-2.5-flash`) |
| Weather | Open-Meteo API (free, no key) |
| Geolocation | ipapi.co / ip-api.com / ipwho.is |
| Frontend | HTML + Tailwind CSS + Vanilla JS |

---

## Setup

### 1. Clone the repo
```bash
git clone https://github.com/manavi773/AquaCatch-AI.git
cd AquaCatch-AI
```

### 2. Create a virtual environment
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment
```bash
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY
```

### 5. Run the app
```bash
python app.py
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your browser.

---

## Project Structure

```
AquaCatch-AI/
├── app.py              # Flask backend + Gemini + Weather + Geolocation
├── requirements.txt    # Python dependencies
├── .env.example        # Environment variable template
├── .gitignore
└── templates/
    └── index.html      # Full frontend (HTML + CSS + JS)
```

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `GEMINI_API_KEY` | ✅ | — | Your Google Gemini API key |
| `GEMINI_MODEL` | ❌ | `gemini-2.5-flash` | Gemini model to use |
| `FLASK_PORT` | ❌ | `5000` | Port to run Flask on |
| `FLASK_DEBUG` | ❌ | `True` | Enable debug mode |

---

## License

MIT — free to use, modify, and distribute.

---

*Built for the Hackathon · AquaCatch AI · Gemini Vision + Open-Meteo*
