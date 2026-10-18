import os
import time
import io
import re
from flask import Flask, render_template, request, jsonify
from google import genai
from PIL import Image
import requests
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# ── API Keys — loaded from .env, never hardcoded ──────────────
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")          # Required: set in .env
GEMINI_MODEL   = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
FALLBACK_MODELS = ["gemini-2.5-flash", "gemini-1.5-flash", "gemini-1.5-pro"]

if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY not set. Copy .env.example to .env and add your key.")

# ── WMO Weather codes ──────────────────────────────────────────
WEATHER_CODES = {
    0:  ("Clear Sky",           "☀️"),
    1:  ("Mainly Clear",        "🌤️"),
    2:  ("Partly Cloudy",       "⛅"),
    3:  ("Overcast",            "☁️"),
    45: ("Foggy",               "🌫️"),
    48: ("Rime Fog",            "🌫️"),
    51: ("Light Drizzle",       "🌦️"),
    53: ("Moderate Drizzle",    "🌦️"),
    55: ("Dense Drizzle",       "🌧️"),
    61: ("Slight Rain",         "🌧️"),
    63: ("Moderate Rain",       "🌧️"),
    65: ("Heavy Rain",          "🌧️"),
    71: ("Slight Snow",         "🌨️"),
    73: ("Moderate Snow",       "🌨️"),
    75: ("Heavy Snow",          "❄️"),
    80: ("Rain Showers",        "🌦️"),
    81: ("Moderate Showers",    "🌦️"),
    82: ("Violent Showers",     "⛈️"),
    95: ("Thunderstorm",        "⛈️"),
    96: ("Thunderstorm + Hail", "⛈️"),
    99: ("Severe Thunderstorm", "⛈️"),
}

def is_private_ip(ip):
    if not ip or ip in ("127.0.0.1", "::1", "localhost"):
        return True
    return ip.startswith(("10.", "192.168.", "172.16.", "172.17.",
                           "172.18.", "172.19.", "172.20.", "172.31."))

def detect_location(client_ip=None):
    """3-tier IP geolocation: ipapi.co -> ip-api.com -> ipwho.is"""
    clean_ip = None
    if client_ip and not is_private_ip(client_ip):
        clean_ip = client_ip.split(",")[0].strip()

    # Primary: ipapi.co
    try:
        url = f"https://ipapi.co/{clean_ip}/json/" if clean_ip else "https://ipapi.co/json/"
        r = requests.get(url, headers={"User-Agent": "AquaCatch/1.0"}, timeout=6)
        if r.status_code == 200:
            d = r.json()
            if d.get("latitude") is not None:
                return {
                    "lat": round(float(d["latitude"]), 4),
                    "lon": round(float(d["longitude"]), 4),
                    "city": d.get("city") or "Coastal Zone",
                    "region": d.get("region") or "",
                    "country": d.get("country_name") or "",
                    "source": "ipapi.co",
                    "ip": d.get("ip") or (clean_ip or "auto")
                }
    except Exception as e:
        print(f"ipapi.co: {e}")

    # Fallback 1: ip-api.com
    try:
        url = f"http://ip-api.com/json/{clean_ip}" if clean_ip else "http://ip-api.com/json/"
        r = requests.get(url, timeout=6)
        if r.status_code == 200:
            d = r.json()
            if d.get("status") == "success":
                return {
                    "lat": round(float(d["lat"]), 4),
                    "lon": round(float(d["lon"]), 4),
                    "city": d.get("city") or "Coastal Region",
                    "region": d.get("regionName") or "",
                    "country": d.get("country") or "",
                    "source": "ip-api.com",
                    "ip": d.get("query") or (clean_ip or "auto")
                }
    except Exception as e:
        print(f"ip-api.com: {e}")

    # Fallback 2: ipwho.is
    try:
        url = f"https://ipwho.is/{clean_ip}" if clean_ip else "https://ipwho.is/"
        r = requests.get(url, timeout=6)
        if r.status_code == 200:
            d = r.json()
            if d.get("success"):
                return {
                    "lat": round(float(d["latitude"]), 4),
                    "lon": round(float(d["longitude"]), 4),
                    "city": d.get("city") or "Harbor Area",
                    "region": d.get("region") or "",
                    "country": d.get("country") or "",
                    "source": "ipwho.is",
                    "ip": d.get("ip") or (clean_ip or "auto")
                }
    except Exception as e:
        print(f"ipwho.is: {e}")

    # Default coastal baseline
    return {
        "lat": 12.9187, "lon": 74.8598,
        "city": "Mangaluru Port", "region": "Karnataka",
        "country": "India", "source": "default", "ip": "local"
    }

def get_weather(lat, lon):
    """Fetch live weather from Open-Meteo (free, no key needed)."""
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        f"&current=temperature_2m,relative_humidity_2m,apparent_temperature,"
        f"precipitation,rain,weather_code,wind_speed_10m,wind_direction_10m"
        f"&timezone=auto"
    )
    try:
        r = requests.get(url, timeout=8)
        if r.status_code == 200:
            c = r.json().get("current", {})
            code = c.get("weather_code", 0)
            desc, icon = WEATHER_CODES.get(code, ("Fair", "🌤️"))
            return {
                "temperature":          c.get("temperature_2m", 26.0),
                "apparent_temperature": c.get("apparent_temperature", 26.0),
                "precipitation":        c.get("precipitation", 0.0),
                "rain":                 c.get("rain", 0.0),
                "wind_speed":           c.get("wind_speed_10m", 8.0),
                "wind_direction":       c.get("wind_direction_10m", 0),
                "humidity":             c.get("relative_humidity_2m", 72),
                "condition":            desc,
                "icon":                 icon,
                "live":                 True
            }
    except Exception as e:
        print(f"Open-Meteo error: {e}")

    return {
        "temperature": 26.0, "apparent_temperature": 28.0,
        "precipitation": 0.0, "rain": 0.0, "wind_speed": 8.0,
        "wind_direction": 90, "humidity": 72,
        "condition": "Mainly Clear", "icon": "🌤️", "live": False
    }

def parse_verdict(text):
    if not text:
        return "CAUTION"
    u = text.upper()
    if "HIGH RISK" in u or "CRITICAL RISK" in u:
        return "HIGH RISK"
    elif "CAUTION" in u or "MODERATE RISK" in u:
        return "CAUTION"
    elif "SAFE" in u:
        return "SAFE"
    return "CAUTION"

# ── Routes ─────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/telemetry")
def telemetry():
    try:
        lat = request.args.get("lat")
        lon = request.args.get("lon")
        client_ip = request.headers.get("X-Forwarded-For") or request.remote_addr

        if lat and lon:
            lat, lon = round(float(lat), 4), round(float(lon), 4)
            location = {
                "lat": lat, "lon": lon,
                "city": request.args.get("city") or "Your Location",
                "region": "", "country": "", "source": "device-gps"
            }
        else:
            location = detect_location(client_ip)
            lat, lon = location["lat"], location["lon"]

        weather = get_weather(lat, lon)
        return jsonify({"success": True, "location": location,
                        "weather": weather, "timestamp": time.strftime("%H:%M")})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/analyze", methods=["POST"])
def analyze():
    try:
        # Image validation
        image_file = request.files.get("image")
        if not image_file or image_file.filename == "":
            return jsonify({"error": "No image provided."}), 400

        # Location
        lat_val = request.form.get("lat")
        lon_val = request.form.get("lon")
        client_ip = request.headers.get("X-Forwarded-For") or request.remote_addr

        if lat_val and lon_val:
            try:
                lat, lon = round(float(lat_val), 4), round(float(lon_val), 4)
                location = {"lat": lat, "lon": lon,
                            "city": request.form.get("location_name") or "Field Location",
                            "region": "", "country": "", "source": "gps"}
            except ValueError:
                location = detect_location(client_ip)
                lat, lon = location["lat"], location["lon"]
        else:
            location = detect_location(client_ip)
            lat, lon = location["lat"], location["lon"]

        water_type = request.form.get("water_type", "General Coastal Water Body")
        language   = request.form.get("language", "English")

        # Live weather
        wx = get_weather(lat, lon)
        temp      = wx["temperature"]
        feels     = wx["apparent_temperature"]
        rain      = wx["precipitation"]
        wind      = wx["wind_speed"]
        wind_dir  = wx["wind_direction"]
        humidity  = wx["humidity"]
        condition = wx["condition"]

        # Process image
        try:
            image = Image.open(image_file.stream)
            if image.mode in ("RGBA", "P", "LA", "CMYK"):
                image = image.convert("RGB")
        except Exception as e:
            return jsonify({"error": f"Invalid image: {e}"}), 400

        city_str = ", ".join(filter(None, [location.get("city"), location.get("region"), location.get("country")]))

        lang_instruction = (
            f"IMPORTANT: Write your ENTIRE response — all headings, labels, descriptions, and bullet points — "
            f"in {language}. Do NOT use English unless the language requested IS English."
            if language != "English" else ""
        )

        prompt = f"""
You are AquaCatch AI — an expert marine biologist and artisanal fishing safety advisor.
{lang_instruction}

Analyze the attached photo (water body, shoreline, water sample, or fish catch) combined with these LIVE weather metrics for {city_str} (Lat: {lat}, Lon: {lon}):

LIVE TELEMETRY:
- Temperature: {temp}°C (Feels like {feels}°C)
- Recent Rainfall: {rain} mm
- Wind Speed: {wind} km/h ({wind_dir}°)
- Humidity: {humidity}%
- Sky Condition: {condition}
- Water Body Type: {water_type}

Provide a structured advisory report using EXACTLY these markdown sections:

### 1. Visual Water & Catch Evaluation
- **Clarity & Color**: Describe transparency, color tints (algal green, tannin-brown, clay turbidity, clear).
- **Turbidity & Surface**: Note suspended sediment, oil sheens, foam, debris, or algal bloom signs.
- **Biological Indicators**: If fish are visible — assess eye clarity, gill color, scales, signs of stress or hypoxia. If only water — assess ecological health indicators.

### 2. Smart Timing & Spot Advisory
- **Weather Impact**: How does current rainfall ({rain} mm), wind ({wind} km/h), and temperature ({temp}°C) affect water quality and fish behavior RIGHT NOW?
- **Best Time to Fish**: Specific guidance — cast now, wait X hours, target tide change, etc.
- **Best Spots**: Recommend strategic locations (sheltered bays, eddy pools, river mouths, deeper water vs. turbid shallows).

### 3. Final Actionable Verdict
- **Safety Rating**: State EXACTLY one of: **[SAFE]**, **[CAUTION]**, or **[HIGH RISK]**
- **Summary**: Two concise sentences integrating what you see visually with the live weather data.
- **3 Immediate Actions**: Three concrete bullet points the fisherman should do right now (gear, technique, safety, consumption advice).
"""

        # Call Gemini API (key is hardcoded server-side, never exposed)
        client = genai.Client(api_key=GEMINI_API_KEY)
        models_to_try = [GEMINI_MODEL] + [m for m in FALLBACK_MODELS if m != GEMINI_MODEL]

        response_text = None
        last_err = None

        for model in models_to_try:
            for attempt in range(3):
                try:
                    resp = client.models.generate_content(
                        model=model,
                        contents=[image, prompt]
                    )
                    response_text = resp.text
                    break
                except Exception as e:
                    last_err = e
                    err = str(e)
                    if ("503" in err or "429" in err) and attempt < 2:
                        time.sleep(2 * (attempt + 1))
                    else:
                        print(f"Model {model} attempt {attempt+1}: {err}")
                        break
            if response_text:
                break

        if not response_text:
            raise Exception(str(last_err))

        return jsonify({
            "success":   True,
            "verdict":   parse_verdict(response_text),
            "report":    response_text,
            "location":  location,
            "weather":   wx,
            "timestamp": time.strftime("%d %b %Y, %H:%M")
        })

    except Exception as e:
        print(f"Analyze error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("FLASK_PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "True").lower() in ("true", "1", "yes")
    print(f"[AquaCatch AI] Running on http://127.0.0.1:{port}")
    app.run(host="0.0.0.0", port=port, debug=debug)