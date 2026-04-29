######
# This file was developed with the assistance of Claude by Anthropic.
######

"""
MeteoGlobe API server.

FastAPI backend that serves the 3D globe frontend and proxies weather data
from Open-Meteo (free, no API key) and place names from Nominatim (OpenStreetMap).
Also proxies map tiles and serves local weather icon assets.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel

load_dotenv()
logger = logging.getLogger("meteo")
# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def env_int(name: str, default: int) -> int:
    """Read an integer from an environment variable, with fallback."""
    raw = os.getenv(name, str(default))
    try:
        return int(str(raw).strip())
    except (TypeError, ValueError):
        return default
# ---------------------------------------------------------------------------
# Configuration (from environment / docker-compose.yml)
# ---------------------------------------------------------------------------

PORT = env_int("PORT", 3000)

# Directory for caching satellite/label tiles on disk (persistent across restarts)
SAT_TILE_CACHE_DIR = os.getenv("SAT_TILE_CACHE_DIR", "tile_cache")

# ---------------------------------------------------------------------------
# In-memory caches
# ---------------------------------------------------------------------------

# Generic TTL cache: key -> {"data": ..., "expires_at": unix_ts}
_cache: dict[str, dict[str, Any]] = {}

# Weather icon file cache: code -> (raw_bytes, content_type)
_icon_cache: dict[int, tuple[bytes, str]] = {}
ICON_LOCAL_DIR = os.path.join("public", "icons")
# Codes actually shipped under public/icons/ — kept aligned with the WMO_TO_METEO
# mapping in public/app.js. Day codes 1-99, night codes 101-199 (where they
# differ from day). Adjust both this set and download_open_source_icons.py if
# the frontend mapping changes.
SUPPORTED_ICON_CODES = {1, 2, 3, 5, 7, 8, 9, 13, 14, 15, 17, 18, 19, 20, 21, 23, 25, 26,
                        101, 102, 103, 105}

# Shared HTTP client (created in lifespan)
_http: httpx.AsyncClient | None = None

# Nominatim rate-limiter: max 1 request per ~1.1s (their free usage policy)
_nominatim_last_call: float = 0.0
_nominatim_lock = asyncio.Lock()
def cache_get(key: str) -> Any | None:
    """Return cached data if it exists and hasn't expired, else None."""
    entry = _cache.get(key)
    if entry and time.time() < float(entry["expires_at"]):
        return entry["data"]
    return None
def cache_set(key: str, data: Any, ttl: int = 600) -> None:
    """Store data in cache with a time-to-live in seconds."""
    _cache[key] = {"data": data, "expires_at": time.time() + ttl}
def as_float(v: Any) -> float | None:
    """Safely convert a value to float, returning None on failure."""
    try:
        if v is None:
            return None
        return float(v)
    except (TypeError, ValueError):
        return None
def as_int(v: Any) -> int | None:
    """Safely convert a value to int, returning None on failure."""
    try:
        if v is None:
            return None
        return int(v)
    except (TypeError, ValueError):
        return None

def iso_utc_to_unix(ts: Any) -> int | None:
    """Convert an ISO-8601 UTC timestamp string to a Unix epoch integer."""
    if not isinstance(ts, str) or not ts:
        return None
    try:
        # Python <3.11 can't parse a trailing "Z" for UTC — normalize to +00:00
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp())
    except Exception:
        return None
def wmo_code(code: Any) -> int:
    """Ensure a WMO weather code is a valid integer, defaulting to 0 (clear sky)."""
    c = as_int(code)
    return c if c is not None else 0
def build_open_meteo_forecast(payload: dict[str, Any]) -> dict[str, Any]:
    """Convert Open-Meteo hourly forecast into a simplified list (every 3h, up to 16 slots).
    Also returns an 'hourly' array with every hour's data for the temperature/rain chart."""
    hourly = payload.get("hourly") if isinstance(payload, dict) else None
    if not isinstance(hourly, dict):
        return {"list": [], "hourly": [], "_source": "open-meteo"}

    times = hourly.get("time") if isinstance(hourly.get("time"), list) else []
    temps = hourly.get("temperature_2m") if isinstance(hourly.get("temperature_2m"), list) else []
    probs = hourly.get("precipitation_probability") if isinstance(hourly.get("precipitation_probability"), list) else []
    precip = hourly.get("precipitation") if isinstance(hourly.get("precipitation"), list) else []
    codes = hourly.get("weather_code") if isinstance(hourly.get("weather_code"), list) else []
    n = min(len(times), len(temps), len(codes))
    if n == 0:
        return {"list": [], "hourly": [], "_source": "open-meteo"}

    # UTC offset from Open-Meteo (seconds) — used by frontend to interpret local times
    utc_offset = as_int(payload.get("utc_offset_seconds")) or 0

    now_ts = int(time.time())

    # Build hourly array for the chart (local ISO times from Open-Meteo with timezone:auto)
    hourly_data: list[dict[str, Any]] = []
    for i in range(n):
        t = times[i] if i < len(times) else None
        if not isinstance(t, str):
            continue
        entry: dict[str, Any] = {
            "time": t,  # local ISO string e.g. "2026-03-28T14:00"
            "temp": as_float(temps[i]) if i < len(temps) else 0.0,
            "precip": as_float(precip[i]) if i < len(precip) else 0.0,
            "pop": as_float(probs[i]) if i < len(probs) else 0.0,
        }
        hourly_data.append(entry)
        if len(hourly_data) >= 48:
            break

    # Build 3-hourly forecast cards (for the scrollable forecast row)
    out: list[dict[str, Any]] = []
    for i in range(n):
        if i % 3 != 0:
            continue
        dt_unix = iso_utc_to_unix(times[i])
        # Skip slots older than 1h (keep a small grace window around "now")
        if dt_unix is None or dt_unix < now_ts - 3600:
            continue
        out.append(
            {
                "dt": dt_unix,
                "main": {"temp": temps[i]},
                "weather": [{"id": wmo_code(codes[i]), "description": "forecast"}],
                # Convert % probability → 0..1 and clamp in case of bad upstream data
                "pop": max(0.0, min(1.0, (as_float(probs[i]) or 0.0) / 100.0)),
            }
        )
        if len(out) >= 16:
            break

    # Build 7-day daily forecast
    daily_raw = payload.get("daily") if isinstance(payload, dict) else None
    daily_out: list[dict[str, Any]] = []
    if isinstance(daily_raw, dict):
        d_times = daily_raw.get("time", [])
        d_tmax = daily_raw.get("temperature_2m_max", [])
        d_tmin = daily_raw.get("temperature_2m_min", [])
        d_precip = daily_raw.get("precipitation_sum", [])
        d_codes = daily_raw.get("weather_code", [])
        d_clouds = daily_raw.get("cloud_cover_mean", []) if isinstance(daily_raw.get("cloud_cover_mean"), list) else []
        d_n = min(len(d_times), len(d_tmax), len(d_tmin), len(d_codes))
        for i in range(d_n):
            daily_out.append({
                "date": d_times[i],  # "2026-03-28"
                "temp_max": as_float(d_tmax[i]) or 0.0,
                "temp_min": as_float(d_tmin[i]) or 0.0,
                "precip": as_float(d_precip[i]) if i < len(d_precip) else 0.0,
                "code": wmo_code(d_codes[i]),
                "clouds": as_int(d_clouds[i]) if i < len(d_clouds) else None,
            })

    return {"list": out, "hourly": hourly_data, "daily": daily_out, "utc_offset": utc_offset, "_source": "open-meteo"}
# ---------------------------------------------------------------------------
# External API helpers
# ---------------------------------------------------------------------------

async def fetch_json(
    url: str,
    cache_key: str,
    ttl: int = 600,
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
    force: bool = False,
) -> Any:
    """GET a JSON endpoint with caching. Bypasses cache when force=True."""
    if not force:
        cached = cache_get(cache_key)
        if cached is not None:
            return cached

    assert _http is not None
    resp = await _http.get(url, params=params or {}, headers=headers or {})
    resp.raise_for_status()
    data = resp.json()
    cache_set(cache_key, data, ttl=ttl)
    return data
# ---------------------------------------------------------------------------
# Reverse geocoding (Nominatim / OpenStreetMap)
# ---------------------------------------------------------------------------

def _extract_place_name(data: Any) -> tuple[str, str]:
    """Extract city/town name and country code from a Nominatim response dict.

    Tries address fields from most to least specific, falling back to
    display_name or raw name if no structured match is found.
    """
    if not isinstance(data, dict):
        return "Selected location", ""
    address = data.get("address") if isinstance(data, dict) else {}
    if not isinstance(address, dict):
        address = {}
    name = (
        address.get("city")
        or address.get("town")
        or address.get("village")
        or address.get("hamlet")
        or address.get("suburb")
        or address.get("municipality")
        or address.get("county")
        or address.get("state")
        or str(data.get("display_name") or "").split(",")[0].strip()
        or str(data.get("name") or "").strip()
        or "Selected location"
    )
    country = str(address.get("country_code") or "").upper()
    return name, country
async def _nominatim_fetch(params: dict[str, Any], cache_key: str, force: bool = False) -> Any:
    """Fetch from Nominatim with rate-limiting (max 1 req/sec) and retry on 429."""
    global _nominatim_last_call
    async with _nominatim_lock:
        elapsed = time.time() - _nominatim_last_call
        if elapsed < 1.1:
            await asyncio.sleep(1.1 - elapsed)
        _nominatim_last_call = time.time()
        return await fetch_json(
            "https://nominatim.openstreetmap.org/reverse",
            cache_key,
            ttl=30 * 24 * 3600,  # 30 days — place names don't change
            headers={"User-Agent": "MeteoGlobe/1.0 (local app)", "Accept-Language": "en"},
            params=params,
            force=force,
        )
async def reverse_geocode_brief(lat: float, lon: float, force: bool = False) -> tuple[str, str]:
    """Return (place_name, country_code) for a lat/lon using Nominatim reverse geocoding."""
    key = f"revgeo_{lat:.3f}_{lon:.3f}"
    if not force:
        cached = cache_get(key)
        if isinstance(cached, dict):
            return _extract_place_name(cached)

    try:
        params = {"lat": lat, "lon": lon, "format": "jsonv2", "addressdetails": 1, "zoom": 14}
        data = await _nominatim_fetch(params, key, force=force)
        return _extract_place_name(data)
    except Exception as exc:
        logger.warning("reverse_geocode_brief failed for (%s, %s): %s", lat, lon, exc)
        return "Selected location", ""
# ---------------------------------------------------------------------------
# Weather data assembly
# ---------------------------------------------------------------------------

async def weather_payload(lat: float, lon: float, force: bool = False, place_name_override: str | None = None) -> dict[str, Any]:
    """Build a full current-weather response combining Open-Meteo data + place name.

    Returns a dict shaped like the legacy OpenWeatherMap format so the
    frontend can consume it without changes.
    When place_name_override is given, skip the slow Nominatim reverse-geocode call.
    """
    if place_name_override:
        place_name, country_code = place_name_override, ""
    else:
        place_name, country_code = await reverse_geocode_brief(lat, lon, force=force)
    om_key = f"om_current_{lat:.4f}_{lon:.4f}"
    om_url = "https://api.open-meteo.com/v1/forecast"
    payload = await fetch_json(
        om_url,
        om_key,
        ttl=900,  # 15 min — weather updates are not instant
        params={
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,apparent_temperature,weather_code,is_day,cloud_cover",
            "timezone": "auto",
        },
        force=force,
    )
    current = payload.get("current") if isinstance(payload, dict) else None
    if not isinstance(current, dict):
        raise HTTPException(status_code=500, detail="Open-Meteo current block missing")

    # With timezone=auto, current.time is in the lieu's local time. Convert
    # back to a real UTC unix timestamp using the offset Open-Meteo returns.
    utc_offset = as_int(payload.get("utc_offset_seconds")) or 0
    local_unix = iso_utc_to_unix(current.get("time")) or int(time.time())
    dt_unix = local_unix - utc_offset

    temp = as_float(current.get("temperature_2m"))
    feels_like = as_float(current.get("apparent_temperature"))
    weather_code = wmo_code(current.get("weather_code"))
    is_day = as_int(current.get("is_day"))
    cloud_cover = as_int(current.get("cloud_cover"))

    # Open-Meteo's free tier doesn't expose real sunrise/sunset here, so we
    # give the frontend a rough +/-6h window around "now" based on is_day.
    sunrise = dt_unix - 6 * 3600 if is_day == 1 else dt_unix + 6 * 3600
    sunset = dt_unix + 6 * 3600 if is_day == 1 else dt_unix - 6 * 3600

    return {
        "_source": "open-meteo-current",
        "coord": {"lat": lat, "lon": lon},
        "weather": [{"id": weather_code, "description": "weather"}],
        "main": {
            "temp": temp if temp is not None else 0.0,
            "feels_like": feels_like if feels_like is not None else (temp if temp is not None else 0.0),
        },
        "clouds": {"all": cloud_cover if cloud_cover is not None else 0},
        "sys": {"country": country_code, "sunrise": sunrise, "sunset": sunset},
        "dt": dt_unix,
        "timezone": utc_offset,
        "name": place_name,
    }
# ---------------------------------------------------------------------------
# FastAPI application setup
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create (and later close) the shared HTTP client used for all external API calls."""
    global _http
    _http = httpx.AsyncClient(timeout=8.0)
    yield
    await _http.aclose()
app = FastAPI(
    title="MeteoGlobe API",
    description="Weather data proxy for the 3D globe frontend",
    lifespan=lifespan,
)
# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------
@app.get("/", include_in_schema=False)
async def root():
    return FileResponse("public/index.html", headers={"Cache-Control": "no-store"})

@app.get("/api/sat/{layer}/{z}/{x}/{y}", summary="Cached satellite/label tile proxy")
async def sat_tile_proxy(layer: str, z: int, x: int, y: int):
    """Proxy Esri satellite or label tiles with persistent disk caching.

    First request fetches from Esri and saves to disk; subsequent requests
    are served directly from the Pi's storage — same quality, no API call.
    """
    if layer not in ("imagery", "labels"):
        raise HTTPException(status_code=400, detail="Layer must be 'imagery' or 'labels'")
    if z < 0 or x < 0 or y < 0 or z > 19:
        raise HTTPException(status_code=400, detail="Invalid tile coordinate")

    # Check disk cache first
    cache_path = os.path.join(SAT_TILE_CACHE_DIR, layer, str(z), str(x), f"{y}.png")
    if os.path.isfile(cache_path):
        return FileResponse(cache_path, media_type="image/png",
                            headers={"Cache-Control": "public, max-age=604800"})

    # Fetch from Esri
    if layer == "imagery":
        url = f"https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
    else:
        url = f"https://services.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}"

    try:
        assert _http is not None
        resp = await _http.get(url, follow_redirects=True)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Esri unreachable: {e}") from e

    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail="Tile unavailable")

    # Save to disk
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    with open(cache_path, "wb") as f:
        f.write(resp.content)

    content_type = resp.headers.get("content-type", "image/png")
    return Response(content=resp.content, media_type=content_type,
                    headers={"Cache-Control": "public, max-age=604800"})
@app.get("/api/weather", summary="Current weather at a coordinate")
async def weather(lat: float, lon: float, force: bool = False):
    """Return current weather for a given lat/lon (used when clicking the globe)."""
    try:
        return await weather_payload(lat, lon, force=force)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
@app.get("/api/forecast", summary="48h forecast at a coordinate")
async def forecast(lat: float, lon: float, force: bool = False):
    om_key = f"om_forecast_{lat:.3f}_{lon:.3f}"
    payload = await fetch_json(
        "https://api.open-meteo.com/v1/forecast",
        om_key,
        ttl=1800,  # 30 min — forecast changes slowly
        params={
            "latitude": lat,
            "longitude": lon,
            "hourly": "temperature_2m,precipitation_probability,precipitation,weather_code",
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,weather_code,cloud_cover_mean",
            "forecast_days": 7,
            "timezone": "auto",
        },
        force=force,
    )
    data = build_open_meteo_forecast(payload if isinstance(payload, dict) else {})
    if data.get("list"):
        return data
    raise HTTPException(status_code=500, detail="Forecast unavailable")
class City(BaseModel):
    name: str
    lat: float
    lon: float
class CitiesRequest(BaseModel):
    cities: list[City]
@app.post("/api/cities", summary="Weather for a list of cities (parallel fetch)")
async def cities_weather(body: CitiesRequest, force: bool = False):
    """Fetch current weather for multiple cities in parallel (max 8 concurrent).

    Used by the frontend to populate city marker bubbles on the globe.
    If a city's API call fails it is silently dropped from the result so the
    other markers still render.
    """
    sem = asyncio.Semaphore(8)

    async def fetch_city(city: City) -> dict[str, Any] | None:
        async with sem:
            try:
                w = await weather_payload(city.lat, city.lon, force=force, place_name_override=city.name)
                if not isinstance(w.get("name"), str) or not w.get("name"):
                    w["name"] = city.name
                return {**city.model_dump(), "weather": w}
            except Exception:
                return None

    results = await asyncio.gather(*[fetch_city(c) for c in body.cities])
    return [r for r in results if r is not None]
@app.get("/api/geocode", summary="Convert city name to lat/lon")
async def geocode(q: str):
    """Search for a place by name using Nominatim and return matching coordinates."""
    qq = (q or "").strip()
    if len(qq) < 2:
        return []

    key = f"geo_{qq.lower()}"
    cached = cache_get(key)
    if cached is not None:
        return cached

    try:
        raw = await fetch_json(
            "https://nominatim.openstreetmap.org/search",
            key,
            ttl=7 * 24 * 3600,  # 7 days — search results are stable
            headers={"User-Agent": "MeteoGlobe/1.0 (local app)", "Accept-Language": "en"},
            params={"q": qq, "format": "jsonv2", "addressdetails": 1, "limit": 8},
        )
        out: list[dict[str, Any]] = []
        if isinstance(raw, list):
            for item in raw:
                if not isinstance(item, dict):
                    continue
                lat = as_float(item.get("lat"))
                lon = as_float(item.get("lon"))
                if lat is None or lon is None:
                    continue
                address = item.get("address") if isinstance(item.get("address"), dict) else {}
                display_name = str(item.get("display_name") or "").strip()
                name = (
                    address.get("city")
                    or address.get("town")
                    or address.get("village")
                    or address.get("municipality")
                    or address.get("county")
                    or address.get("state")
                    or (display_name.split(",")[0] if display_name else "Unknown")
                )
                out.append(
                    {
                        "name": name,
                        "lat": lat,
                        "lon": lon,
                        "country": str(address.get("country_code") or "").upper(),
                        "state": address.get("state") or "",
                    }
                )
        cache_set(key, out, ttl=7 * 24 * 3600)
        return out
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
@app.get("/api/icon/{code}", summary="Weather pictogram from local files")
async def icon(code: int):
    """Serve a weather icon (SVG or PNG) from local assets, with in-memory caching."""
    if code not in SUPPORTED_ICON_CODES:
        raise HTTPException(status_code=400, detail="Icon code must be 1-42 or 101-142")

    if code in _icon_cache:
        raw, ct = _icon_cache[code]
        return Response(content=raw, media_type=ct, headers={"Cache-Control": "public, max-age=2592000"})

    local_path = os.path.join(ICON_LOCAL_DIR, f"{code}.svg")
    if os.path.isfile(local_path):
        with open(local_path, "rb") as fh:
            raw = fh.read()
        ct = "image/svg+xml"
        _icon_cache[code] = (raw, ct)
        return Response(content=raw, media_type=ct, headers={"Cache-Control": "public, max-age=2592000"})

    raise HTTPException(
        status_code=404,
        detail="Icon file not found locally in public/icons. Rebuild image with committed icon files.",
    )
@app.get("/{filename:path}", include_in_schema=False)
async def public_files(filename: str):
    """Catch-all route to serve static files from the public/ directory."""
    path = os.path.join("public", filename)
    if os.path.isfile(path):
        lower = filename.lower()
        if lower.endswith((".html", ".js", ".css")):
            return FileResponse(path, headers={"Cache-Control": "no-store"})
        return FileResponse(path, headers={"Cache-Control": "public, max-age=2592000"})  # 30 days
    raise HTTPException(status_code=404)
# ---------------------------------------------------------------------------
# Direct execution (development mode with auto-reload)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    print(f"\n[MeteoGlobe]  http://localhost:{PORT}")
    print(f"[API docs]    http://localhost:{PORT}/docs\n")

    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=PORT,
        reload=True,
    )
