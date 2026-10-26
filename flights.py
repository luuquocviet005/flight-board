"""Call 3 aviation APIs for each airport and save the result as docs/data.json.

The web page (docs/index.html) reads data.json, so API keys never reach the browser.

Run (PowerShell):
    $env:AIRLABS_KEY="..."; $env:AVIATIONSTACK_KEY="..."; python flights.py
"""
import json
import os
import urllib.request
from datetime import datetime, timezone

AIRPORTS = ["SGN", "HAN", "DAD"]  # IATA codes
# ponytail: 3 Aviationstack calls per run; free plan = 100/month, so run at most ~once a day


def get(url):
    # AirportsAPI returns 403 to Python's default User-Agent
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def airport_info(code):
    a = get(f"https://airportsapi.com/api/airports/{code}")["data"]["attributes"]
    keep = ["name", "iata_code", "icao_code", "type", "latitude", "longitude", "elevation"]
    return {k: a.get(k) for k in keep}


def airlabs(code, key):
    r = get(f"https://airlabs.co/api/v9/schedules?dep_iata={code}&api_key={key}")
    if "error" in r:
        raise RuntimeError(r["error"].get("message", r["error"]))
    return [{
        "flight": f.get("flight_iata"),
        "airline": f.get("airline_iata"),
        "to": f.get("arr_iata"),
        "dep_time": f.get("dep_time"),
        "arr_time": f.get("arr_time"),
        "status": f.get("status"),
        "delay": f.get("dep_delayed"),
    } for f in r.get("response", [])]


def aviationstack(code, key):
    r = get(f"http://api.aviationstack.com/v1/flights?dep_iata={code}&limit=50&access_key={key}")
    if "error" in r:
        raise RuntimeError(r["error"].get("message", r["error"]))

    def t(s):  # "2026-10-16T17:30:00+00:00" -> "2026-10-16 17:30" (local time despite +00:00)
        return s[:16].replace("T", " ") if s else None

    return [{
        "flight": f["flight"]["iata"],
        "airline": f["airline"]["iata"],
        "to": f["arrival"]["iata"],
        "dep_time": t(f["departure"]["scheduled"]),
        "arr_time": t(f["arrival"]["scheduled"]),
        "status": f["flight_status"],
        "delay": f["departure"]["delay"],
    } for f in r.get("data", [])]


def safe(fn, *args):
    """Return (rows, error) so one failing API doesn't kill the whole run."""
    try:
        return fn(*args), None
    except Exception as e:
        return [], str(e)


def main():
    airlabs_key = os.environ.get("AIRLABS_KEY")
    avs_key = os.environ.get("AVIATIONSTACK_KEY")
    if not (airlabs_key or avs_key):
        # Don't overwrite the published data.json with an empty board
        exit("Set AIRLABS_KEY / AVIATIONSTACK_KEY first (in VS Code use the 'Debug flights.py' config, it reads .env)")
    out = {"updated": datetime.now(timezone.utc).isoformat(timespec="minutes"), "airports": {}}

    for code in AIRPORTS:
        info, info_err = safe(airport_info, code)
        al, al_err = safe(airlabs, code, airlabs_key) if airlabs_key else ([], "AIRLABS_KEY not set")
        av, av_err = safe(aviationstack, code, avs_key) if avs_key else ([], "AVIATIONSTACK_KEY not set")
        out["airports"][code] = {
            "info": info or {"iata_code": code},
            "airlabs": al,
            "aviationstack": av,
            "errors": {k: v for k, v in {"airportsapi": info_err, "airlabs": al_err, "aviationstack": av_err}.items() if v},
        }
        print(f"{code}: airlabs={len(al)} aviationstack={len(av)} errors={out['airports'][code]['errors']}")

    os.makedirs("docs", exist_ok=True)
    with open("docs/data.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print("Saved docs/data.json")


if __name__ == "__main__":
    main()
