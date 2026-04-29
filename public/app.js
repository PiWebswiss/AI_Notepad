/******
 * This file was developed with the assistance of Claude by Anthropic.
 ******/

/*
  MeteoGlobe - CesiumJS edition
  Interactive 3D globe that shows real-time weather for any location.
  Uses Open-Meteo API (free, no key) for weather data, Nominatim for place names,
  and CesiumJS for the 3D globe rendering with Esri satellite imagery.
*/

// --- Internationalization (i18n) ---
// All user-visible strings in English and French.
// t('key') returns the string for the current language.
let lang = (navigator.language || '').startsWith('fr') ? 'fr' : 'en';

const I18N = {
  en: {
    loading: 'Loading MeteoGlobe...',
    searchPlaceholder: 'Search city or country...',
    clickHint: 'Click anywhere on the 3D globe for weather',
    forecast7day: '7-Day Forecast',
    ssHint: 'Move mouse or touch to return',
    feelsLike: 'Feels like',
    noResults: 'No locations found',
    forecastLoading: 'Loading forecast...',
    forecastUnavailable: 'Forecast unavailable',
    noData: 'No data',
    refreshing: 'Refreshing weather...',
    refreshFailed: 'Refresh failed',
    weatherError: 'Weather error',
    searchError: 'Search weather error',
    locating: 'Locating your position...',
    locationBlocked: 'Location blocked by browser. Allow it in site settings.',
    locationUnavail: 'Location unavailable. Use search or click on the globe.',
    liveUpdated: 'Live weather updated for your location',
    yourLocation: 'Your location',
    cityUnavail: 'City weather unavailable. Check API/network.',
    cesiumFail: 'CesiumJS failed to load. Check network and hard refresh (Ctrl+F5).',
    unknown: 'Unknown',
    selected: 'Selected',
    fetching: 'Fetching...',
    now: 'now',
    today: 'Today',
    dayNames: ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'],
  },
  fr: {
    loading: 'Chargement de MeteoGlobe...',
    searchPlaceholder: 'Rechercher une ville ou un pays...',
    clickHint: 'Cliquez n\'importe ou sur le globe pour la meteo',
    forecast7day: 'Previsions 7 jours',
    ssHint: 'Bougez la souris ou touchez pour revenir',
    feelsLike: 'Ressenti',
    noResults: 'Aucun lieu trouve',
    forecastLoading: 'Chargement des previsions...',
    forecastUnavailable: 'Previsions indisponibles',
    noData: 'Pas de donnees',
    refreshing: 'Actualisation de la meteo...',
    refreshFailed: 'Echec de l\'actualisation',
    weatherError: 'Erreur meteo',
    searchError: 'Erreur de recherche meteo',
    locating: 'Localisation en cours...',
    locationBlocked: 'Localisation bloquee par le navigateur. Autorisez-la dans les parametres.',
    locationUnavail: 'Localisation indisponible. Utilisez la recherche ou cliquez sur le globe.',
    liveUpdated: 'Meteo mise a jour pour votre position',
    yourLocation: 'Votre position',
    cityUnavail: 'Meteo des villes indisponible. Verifiez le reseau.',
    cesiumFail: 'CesiumJS n\'a pas pu charger. Verifiez le reseau et actualisez (Ctrl+F5).',
    unknown: 'Inconnu',
    selected: 'Selection',
    fetching: 'Chargement...',
    now: 'maint.',
    today: 'Auj.',
    dayNames: ['Dim', 'Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam'],
  },
};

// Returns the translated string for the given key
function t(key) {
  return (I18N[lang] || I18N.en)[key] || (I18N.en)[key] || key;
}

// Updates all HTML elements with data-i18n or data-i18n-placeholder attributes
function applyI18n() {
  document.querySelectorAll('[data-i18n]').forEach(el => {
    const key = el.getAttribute('data-i18n');
    el.textContent = t(key);
  });
  document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
    const key = el.getAttribute('data-i18n-placeholder');
    el.placeholder = t(key);
  });
}

// --- Weather icon mapping ---
// Maps WMO weather codes directly to MeteoSwiss icon codes.
// { d: daytime icon, n: nighttime icon }
const WMO_TO_METEO = {
  0:  { d: 1, n: 101 },   // Clear sky
  1:  { d: 2, n: 102 },   // Mainly clear
  2:  { d: 3, n: 103 },   // Partly cloudy
  3:  { d: 5, n: 105 },   // Overcast
  45: { d: 25, n: 25 },   // Fog
  48: { d: 25, n: 25 },   // Depositing rime fog
  51: { d: 7, n: 7 },     // Light drizzle
  53: { d: 7, n: 7 },     // Moderate drizzle
  55: { d: 7, n: 7 },     // Dense drizzle
  56: { d: 26, n: 26 },   // Light freezing drizzle
  57: { d: 26, n: 26 },   // Dense freezing drizzle
  61: { d: 7, n: 7 },     // Slight rain
  63: { d: 8, n: 8 },     // Moderate rain
  65: { d: 9, n: 9 },     // Heavy rain
  66: { d: 26, n: 26 },   // Light freezing rain
  67: { d: 26, n: 26 },   // Heavy freezing rain
  71: { d: 13, n: 13 },   // Slight snow
  73: { d: 14, n: 14 },   // Moderate snow
  75: { d: 15, n: 15 },   // Heavy snow
  77: { d: 15, n: 15 },   // Snow grains
  80: { d: 17, n: 17 },   // Slight rain showers
  81: { d: 18, n: 18 },   // Moderate rain showers
  82: { d: 19, n: 19 },   // Violent rain showers
  85: { d: 17, n: 17 },   // Slight snow showers
  86: { d: 15, n: 15 },   // Heavy snow showers
  95: { d: 23, n: 23 },   // Thunderstorm
  96: { d: 20, n: 20 },   // Thunderstorm with slight hail
  99: { d: 21, n: 21 },   // Thunderstorm with heavy hail
};

// --- Constants ---
const HOME_VIEW = { lat: 20, lon: 10, range: 12_000_000 }; // Default globe view (center of Africa, zoomed out)
const ROTATION_STEP_DEG = 0.08;  // ~1.6°/sec at 50ms ticks
const ROTATION_TICK_MS = 50;     // ~20 fps — smoother spin while still light on the Pi

// --- Global state ---
let map;                          // CesiumJS map adapter (wraps the Cesium Viewer)
let cityWeatherCache = [];        // Cached weather data for all cities on the globe
let activeTarget = null;          // Currently selected location { lat, lon, source }
let activeMarkerData = null;      // Weather data for the currently selected location
let useFahrenheit = false;        // Temperature unit toggle (default: Celsius)
let userLocation = null;          // User's GPS location { lat, lon, acc }
let refreshInFlight = false;      // Prevents multiple simultaneous refresh requests
let rotateTimer = null;           // Interval ID for globe auto-rotation
let searchTimer = null;           // Debounce timer for search input
let hintTimer = null;             // Timer for hiding hint messages
let cityRetryTimer = null;        // Retry timer if city weather loading fails
let cesiumLoadPromise = null;     // Promise for loading CesiumJS library
let mapContextMenuBound = false;  // Whether right-click is already blocked on the globe
let zoomRenderTimer = null;       // Debounce timer for zoom-based marker updates
let lastZoomTier = 1;             // Current zoom tier (1=global, 2=regional, 3=close)
let cityPlacemarkMap = new Map(); // Map of city name -> { bubble marker, icon marker, tier }
let activeMarkerObjects = [];     // Markers for the currently selected location
let screensaverActive = false;    // True while the screensaver is showing — switches pills to compact mode

// t: city tier — 1=megacity (always shown), 2=major city (shown at regional zoom), 3=smaller city (shown when zoomed in)
const CITIES = [
  { name: 'New York',     lat: 40.71,  lon: -74.01,  t: 1 },
  { name: 'Washington',   lat: 38.91,  lon: -77.04,  t: 2 },
  { name: 'Boston',       lat: 42.36,  lon: -71.06,  t: 3 },
  { name: 'Miami',        lat: 25.76,  lon: -80.19,  t: 2 },
  { name: 'Atlanta',      lat: 33.75,  lon: -84.39,  t: 3 },
  { name: 'Dallas',       lat: 32.78,  lon: -96.80,  t: 2 },
  { name: 'Houston',      lat: 29.76,  lon: -95.37,  t: 2 },
  { name: 'Seattle',      lat: 47.61,  lon: -122.33, t: 3 },
  { name: 'San Francisco',lat: 37.77,  lon: -122.42, t: 2 },
  { name: 'Los Angeles',  lat: 34.05,  lon: -118.24, t: 1 },
  { name: 'Chicago',      lat: 41.88,  lon: -87.63,  t: 1 },
  { name: 'Vancouver',    lat: 49.28,  lon: -123.12, t: 3 },
  { name: 'Toronto',      lat: 43.65,  lon: -79.38,  t: 2 },
  { name: 'Montreal',     lat: 45.50,  lon: -73.57,  t: 3 },
  { name: 'Mexico City',  lat: 19.43,  lon: -99.13,  t: 1 },
  { name: 'Bogota',       lat: 4.71,   lon: -74.07,  t: 2 },
  { name: 'Lima',         lat: -12.05, lon: -77.04,  t: 2 },
  { name: 'Santiago',     lat: -33.45, lon: -70.67,  t: 2 },
  { name: 'São Paulo',    lat: -23.55, lon: -46.63,  t: 1 },
  { name: 'Rio de Janeiro', lat: -22.91, lon: -43.20, t: 2 },
  { name: 'Buenos Aires', lat: -34.60, lon: -58.38,  t: 1 },
  { name: 'Dublin',       lat: 53.35,  lon: -6.26,   t: 2 },
  { name: 'London',       lat: 51.51,  lon: -0.13,   t: 1 },
  { name: 'Lisbon',       lat: 38.72,  lon: -9.14,   t: 2 },
  { name: 'Paris',        lat: 48.85,  lon: 2.35,    t: 1 },
  { name: 'Brussels',     lat: 50.85,  lon: 4.35,    t: 2 },
  { name: 'Prague',       lat: 50.08,  lon: 14.44,   t: 2 },
  { name: 'Berlin',       lat: 52.52,  lon: 13.40,   t: 1 },
  { name: 'Warsaw',       lat: 52.23,  lon: 21.01,   t: 2 },
  { name: 'Madrid',       lat: 40.42,  lon: -3.70,   t: 2 },
  { name: 'Barcelona',    lat: 41.39,  lon: 2.17,    t: 2 },
  { name: 'Rome',         lat: 41.90,  lon: 12.50,   t: 2 },
  { name: 'Amsterdam',    lat: 52.37,  lon: 4.90,    t: 2 },
  { name: 'Copenhagen',   lat: 55.68,  lon: 12.57,   t: 2 },
  { name: 'Stockholm',    lat: 59.33,  lon: 18.07,   t: 2 },
  { name: 'Oslo',         lat: 59.91,  lon: 10.75,   t: 3 },
  { name: 'Helsinki',     lat: 60.17,  lon: 24.94,   t: 3 },
  { name: 'Vienna',       lat: 48.21,  lon: 16.37,   t: 2 },
  { name: 'Budapest',     lat: 47.50,  lon: 19.04,   t: 2 },
  { name: 'Athens',       lat: 37.98,  lon: 23.73,   t: 2 },
  { name: 'Bucharest',    lat: 44.43,  lon: 26.10,   t: 3 },
  { name: 'Belgrade',     lat: 44.79,  lon: 20.45,   t: 3 },
  { name: 'Kyiv',         lat: 50.45,  lon: 30.52,   t: 2 },
  { name: 'Zurich',       lat: 47.38,  lon: 8.54,    t: 3 },
  { name: 'Geneva',       lat: 46.20,  lon: 6.15,    t: 3 },
  { name: 'Berne',        lat: 46.95,  lon: 7.45,    t: 3 },
  { name: 'Moscow',       lat: 55.75,  lon: 37.62,   t: 1 },
  { name: 'Casablanca',   lat: 33.57,  lon: -7.59,   t: 2 },
  { name: 'Algiers',      lat: 36.75,  lon: 3.06,    t: 3 },
  { name: 'Tunis',        lat: 36.81,  lon: 10.18,   t: 3 },
  { name: 'Dakar',        lat: 14.69,  lon: -17.44,  t: 3 },
  { name: 'Accra',        lat: 5.56,   lon: -0.20,   t: 3 },
  { name: 'Istanbul',     lat: 41.01,  lon: 28.98,   t: 1 },
  { name: 'Cairo',        lat: 30.04,  lon: 31.24,   t: 1 },
  { name: 'Lagos',        lat: 6.52,   lon: 3.38,    t: 1 },
  { name: 'Addis Ababa',  lat: 8.98,   lon: 38.79,   t: 3 },
  { name: 'Nairobi',      lat: -1.29,  lon: 36.82,   t: 2 },
  { name: 'Kigali',       lat: -1.95,  lon: 30.06,   t: 3 },
  { name: 'Johannesburg', lat: -26.20, lon: 28.04,   t: 2 },
  { name: 'Cape Town',    lat: -33.92, lon: 18.42,   t: 2 },
  { name: 'Riyadh',       lat: 24.71,  lon: 46.67,   t: 2 },
  { name: 'Dubai',        lat: 25.20,  lon: 55.27,   t: 1 },
  { name: 'Abu Dhabi',    lat: 24.45,  lon: 54.38,   t: 3 },
  { name: 'Doha',         lat: 25.29,  lon: 51.53,   t: 3 },
  { name: 'Muscat',       lat: 23.59,  lon: 58.41,   t: 3 },
  { name: 'Jerusalem',    lat: 31.77,  lon: 35.21,   t: 3 },
  { name: 'Tehran',       lat: 35.69,  lon: 51.39,   t: 2 },
  { name: 'Karachi',      lat: 24.86,  lon: 67.01,   t: 2 },
  { name: 'Mumbai',       lat: 19.08,  lon: 72.88,   t: 1 },
  { name: 'Delhi',        lat: 28.61,  lon: 77.21,   t: 1 },
  { name: 'Dhaka',        lat: 23.81,  lon: 90.41,   t: 3 },
  { name: 'Kathmandu',    lat: 27.72,  lon: 85.32,   t: 3 },
  { name: 'Colombo',      lat: 6.93,   lon: 79.86,   t: 3 },
  { name: 'Bangkok',      lat: 13.75,  lon: 100.52,  t: 2 },
  { name: 'Kuala Lumpur', lat: 3.14,   lon: 101.69,  t: 3 },
  { name: 'Jakarta',      lat: -6.21,  lon: 106.85,  t: 2 },
  { name: 'Hanoi',        lat: 21.03,  lon: 105.85,  t: 3 },
  { name: 'Ho Chi Minh City', lat: 10.82, lon: 106.63, t: 3 },
  { name: 'Manila',       lat: 14.60,  lon: 120.98,  t: 2 },
  { name: 'Hong Kong',    lat: 22.32,  lon: 114.17,  t: 2 },
  { name: 'Taipei',       lat: 25.03,  lon: 121.56,  t: 2 },
  { name: 'Beijing',      lat: 39.91,  lon: 116.39,  t: 1 },
  { name: 'Shanghai',     lat: 31.23,  lon: 121.47,  t: 1 },
  { name: 'Tokyo',        lat: 35.68,  lon: 139.69,  t: 1 },
  { name: 'Osaka',        lat: 34.69,  lon: 135.50,  t: 3 },
  { name: 'Seoul',        lat: 37.57,  lon: 126.98,  t: 1 },
  { name: 'Singapore',    lat: 1.35,   lon: 103.82,  t: 1 },
  { name: 'Sydney',       lat: -33.87, lon: 151.21,  t: 1 },
  { name: 'Melbourne',    lat: -37.81, lon: 144.96,  t: 2 },
  { name: 'Perth',        lat: -31.95, lon: 115.86,  t: 3 },
  { name: 'Auckland',     lat: -36.85, lon: 174.76,  t: 3 },
  { name: 'Wellington',   lat: -41.29, lon: 174.78,  t: 3 },
];

// Quick lookup: city name -> tier number (for fast visibility checks)
const CITY_TIER = new Map(CITIES.map(c => [c.name, c.t]));

// Zoom thresholds: returns max tier to display at given camera range (metres)
// range > 5M  ? only megacities (t=1, ~22 cities)
// range 1.5M–5M ? major cities (t=2, ~60 cities)
// range < 1.5M ? all cities   (t=3, 93 cities)
function getMaxCityTier(range) {
  if (range > 5_000_000) return 1;
  if (range > 1_500_000) return 2;
  return 3;
}

// --- Script/CSS loading helpers ---
// Loads an external JS script with a timeout (rejects if too slow)
function loadScriptWithTimeout(src, timeoutMs = 12000) {
  return new Promise((resolve, reject) => {
    const script = document.createElement('script');
    let done = false;

    const finish = (ok, err) => {
      if (done) return;
      done = true;
      clearTimeout(timer);
      script.onload = null;
      script.onerror = null;
      if (ok) resolve();
      else reject(err || new Error(`Failed to load ${src}`));
    };

    const timer = setTimeout(() => {
      finish(false, new Error(`Timed out while loading ${src}`));
    }, timeoutMs);

    script.src = src;
    script.async = true;
    script.crossOrigin = 'anonymous';
    script.onload = () => finish(true);
    script.onerror = () => finish(false, new Error(`Error while loading ${src}`));
    document.head.appendChild(script);
  });
}

// Adds a CSS stylesheet to the page (only once per href)
function ensureStylesheetLoaded(href) {
  if (document.querySelector(`link[data-href="${href}"]`)) return;
  const link = document.createElement('link');
  link.rel = 'stylesheet';
  link.href = href;
  link.setAttribute('data-href', href);
  document.head.appendChild(link);
}

// --- Zoom / range conversion ---
// Converts camera height (metres) to a Google Maps-style zoom level (2-18).
// Anchor: at 5000 m altitude, zoom = 16. Each doubling of altitude loses 1 zoom.
function rangeToZoom(range) {
  const r = Math.max(2_000, asFiniteNumber(range, HOME_VIEW.range));
  const z = 16 - Math.log2(r / 5_000);
  return Math.max(2, Math.min(18, Math.round(z)));
}

// Inverse of rangeToZoom: zoom level → camera height (metres).
function zoomToRange(zoom) {
  const z = Math.max(2, Math.min(18, asFiniteNumber(zoom, 2)));
  return 5_000 * (2 ** (16 - z));
}

// --- CesiumJS loader ---
// Loads the CesiumJS library from CDN (only once). Returns true if successful.
async function ensureCesiumLoaded() {
  if (window.Cesium?.Viewer) return true;
  if (cesiumLoadPromise) {
    try {
      await cesiumLoadPromise;
    } catch (_) {}
    return !!window.Cesium?.Viewer;
  }

  cesiumLoadPromise = (async () => {
    // Pinned to 1.119: last release that still honors `requestWebgl1`. Newer
    // Cesium ships WebGL2-only shaders (GLSL ES 3.00 with `flat` qualifiers)
    // that fail to compile on devices without WebGL2 — letting us opt back to
    // WebGL1 here is what makes the app run on the broadest range of hardware.
    // Served from jsDelivr: unpkg's CORS policy blocks Cesium's runtime asset
    // XHR (skybox textures, IAU2006 ephemerides, worker scripts), jsDelivr
    // sends Access-Control-Allow-Origin: * for these requests.
    const base = 'https://cdn.jsdelivr.net/npm/cesium@1.119.0/Build/Cesium/';
    window.CESIUM_BASE_URL = base;
    ensureStylesheetLoaded(`${base}Widgets/widgets.css`);
    await loadScriptWithTimeout(`${base}Cesium.js`, 22000);
    if (!window.Cesium?.Viewer) {
      throw new Error('Cesium script loaded but API unavailable');
    }
  })();

  try {
    await cesiumLoadPromise;
  } catch (_) {
  }
  return !!window.Cesium?.Viewer;
}

// --- DOM helpers ---
// Sets the text content of an element by its ID
function setText(id, text) {
  const el = document.getElementById(id);
  if (el) el.textContent = text;
}

// Adds or removes the 'active' CSS class on an element
function showEl(id, active) {
  const el = document.getElementById(id);
  if (!el) return;
  if (active) el.classList.add('active');
  else el.classList.remove('active');
}

// Capitalizes the first letter of a string
function cap(s) {
  return s ? s.charAt(0).toUpperCase() + s.slice(1) : '';
}

// --- Weather helpers ---
// Converts a WMO weather code to a MeteoSwiss icon code (used for /api/icon/{code}).
// When a cloud-cover percentage is provided, codes 0-3 (clear/mainly clear/partly
// cloudy/overcast) are refined using finer thresholds than the WMO discretization,
// so the icon better matches the actual sky state.
function getMeteoIcon(wmoCode, daytime = true, cloudCover = null) {
  // Refine "clear-ish" codes using cloud cover when available.
  // WMO codes 0-3 are themselves defined from cloud-cover ranges, but the code
  // alone loses precision. Using the raw % gives us a more faithful icon choice.
  if (cloudCover != null && Number.isFinite(cloudCover) && wmoCode >= 0 && wmoCode <= 3) {
    let refined;
    if (cloudCover < 13) refined = 0;       // truly clear
    else if (cloudCover < 38) refined = 1;  // mainly clear
    else if (cloudCover < 75) refined = 2;  // partly cloudy
    else refined = 3;                       // overcast
    const mr = WMO_TO_METEO[refined];
    if (mr) return daytime ? mr.d : mr.n;
  }
  const m = WMO_TO_METEO[wmoCode];
  if (m) return daytime ? m.d : m.n;
  return daytime ? 1 : 101;
}

// Returns a short text label for a WMO weather code (used as fallback when icon fails)
function getWeatherEmoji(wmoCode, daytime = true) {
  if (wmoCode === 0) return daytime ? 'SUN' : 'MOON';
  if (wmoCode === 1) return 'PCLD';
  if (wmoCode === 2) return 'SCLD';
  if (wmoCode === 3) return 'CLD';
  if (wmoCode >= 45 && wmoCode <= 48) return 'FG';
  if (wmoCode >= 51 && wmoCode <= 67) return 'RN';
  if (wmoCode >= 71 && wmoCode <= 77) return 'SN';
  if (wmoCode >= 80 && wmoCode <= 82) return 'RN';
  if (wmoCode >= 85 && wmoCode <= 86) return 'SN';
  if (wmoCode >= 95) return 'TS';
  return 'WX';
}
// Generates an inline SVG data URL as a fallback weather icon
function buildWeatherIconDataUrl(wmoCode, daytime = true) {
  const txt = getWeatherEmoji(wmoCode, daytime);
  const iconText = escapeXml(txt);
  const svg = `\n<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 96 96">\n  <rect x="8" y="8" width="80" height="80" rx="16" fill="#0d1b33"/>\n  <text x="48" y="58" text-anchor="middle" font-size="22" font-family="Inter,Segoe UI,Arial,sans-serif" fill="#ffffff" font-weight="700">${iconText}</text>\n</svg>`;
  return `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`;
}

// Checks if it's daytime at the weather location (using sunrise/sunset timestamps)
function isDaytime(data) {
  if (!data || !data.sys) return true;
  if (!data.sys.sunrise || !data.sys.sunset) return true;
  return data.dt >= data.sys.sunrise && data.dt <= data.sys.sunset;
}

// Returns a color based on temperature (blue=cold, red=hot)
function tempColor(c) {
  if (c < -15) return '#00bfff';
  if (c < 0) return '#64b5f6';
  if (c < 10) return '#81c784';
  if (c < 20) return '#ffd54f';
  if (c < 30) return '#ff9800';
  return '#f44336';
}

// Formats temperature for display (respects C/F toggle)
function displayTemp(c) {
  if (useFahrenheit) return `${Math.round(c * 9 / 5 + 32)}°F`;
  return `${Math.round(c)}°C`;
}

// Safely converts a value to a number, returns fallback if invalid
function asFiniteNumber(v, fallback = 0) {
  const n = Number(v);
  return Number.isFinite(n) ? n : fallback;
}

// Escapes special characters for safe use in SVG/XML strings
function escapeXml(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&apos;');
}

// Cleans a city name to ASCII-safe text, truncated to maxLen (avoids rendering issues)
function safeCityName(name, maxLen = 14) {
  return (name || '')
    .toString()
    .normalize('NFD')                    // split accented chars into base+diacritic
    .replace(/[\u0300-\u036f]/g, '')     // drop combining diacritical marks
    .replace(/[^\x20-\x7E]/g, '')        // keep only printable ASCII
    .replace(/\s+/g, ' ')
    .trim()
    .slice(0, maxLen);
}

// Formats temperature for marker badges (e.g. "+23°C")
function tempBadgeText(c) {
  const n = asFiniteNumber(c, 0);
  if (useFahrenheit) {
    const f = Math.round(n * 9 / 5 + 32);
    return `${f > 0 ? '+' : ''}${f}\u00B0F`;
  }
  const v = Math.round(n);
  return `${v > 0 ? '+' : ''}${v}\u00B0C`;
}

// --- Marker rendering ---
// Pill dimensions for each mode — read by collision detection too.
const PILL_FULL = { w: 116, h: 40 };     // Default: icon + city name + temperature
const PILL_COMPACT = { w: 76, h: 30 };   // Screensaver: icon + temperature only (small, dense)

// Draws a pill-shaped weather marker for a city on the globe.
// Two variants:
//   - compact=false (default): icon left, city name top-right, temperature bottom-right
//   - compact=true: icon left, temperature right — used during screensaver so many
//     pills fit on screen at once and the user gets the "weather everywhere" feel
// Rendered on a <canvas> at 2x resolution for sharp text in CesiumJS.
function buildCityLabelCanvas({ name, temp, iconImg, compact = false }) {
  const tv = asFiniteNumber(temp, 0);
  const color = tempColor(tv);
  const tempTxt = tempBadgeText(tv);
  const S = 2;
  const dims = compact ? PILL_COMPACT : PILL_FULL;
  const W = dims.w * S, H = dims.h * S;
  const c = document.createElement('canvas');
  c.width = W; c.height = H;
  c._superSampling = S;
  const ctx = c.getContext('2d');
  ctx.clearRect(0, 0, W, H);

  // Pill background — fully rounded in compact, soft-rounded in full mode
  const radius = compact ? (H / 2 - 2 * S) : 12 * S;
  ctx.beginPath();
  ctx.roundRect(2 * S, 2 * S, W - 4 * S, H - 4 * S, radius);
  ctx.fillStyle = 'rgba(10,18,36,0.92)';
  ctx.fill();
  ctx.strokeStyle = 'rgba(255,255,255,0.22)';
  ctx.lineWidth = 1.5 * S;
  ctx.stroke();

  // Weather icon on the left, clipped to a circle so any icon size looks clean
  const iconSize = (compact ? 20 : 24) * S;
  const iconCx = (compact ? 17 : 20) * S;
  const iconCy = (compact ? 15 : 20) * S;
  const iconR = iconSize / 2;
  if (iconImg && iconImg.complete && iconImg.naturalWidth > 0) {
    ctx.save();
    ctx.beginPath();
    ctx.arc(iconCx, iconCy, iconR, 0, Math.PI * 2);
    ctx.clip();
    ctx.drawImage(iconImg, iconCx - iconR, iconCy - iconR, iconSize, iconSize);
    ctx.restore();
  } else {
    // Fallback: colored dot
    ctx.beginPath();
    ctx.arc(iconCx, iconCy, 5 * S, 0, Math.PI * 2);
    ctx.fillStyle = color;
    ctx.globalAlpha = 0.5;
    ctx.fill();
    ctx.globalAlpha = 1;
  }

  ctx.textBaseline = 'middle';

  if (compact) {
    // Just the temperature, centered on the right side of the pill
    ctx.font = `800 ${12 * S}px Inter, Arial, sans-serif`;
    ctx.textAlign = 'center';
    ctx.fillStyle = color;
    ctx.fillText(tempTxt, 50 * S, 15 * S);
  } else {
    const city = safeCityName(name || '', 14);
    const textX = 36 * S;
    ctx.textAlign = 'left';
    // City name (top right of icon)
    ctx.font = `700 ${9 * S}px Inter, Arial, sans-serif`;
    ctx.fillStyle = '#ffffff';
    ctx.fillText(city, textX, 13 * S);
    // Temperature (bottom right of icon)
    ctx.font = `800 ${13 * S}px Inter, Arial, sans-serif`;
    ctx.fillStyle = color;
    ctx.fillText(tempTxt, textX, 28 * S);
  }

  return c;
}

// Draws a larger tooltip marker for the currently selected location.
// Shows weather icon + city name on top and colored temperature below.
function buildActiveMarkerCanvas({ name, temp, iconImg }) {
  const tv = asFiniteNumber(temp, 0);
  const color = tempColor(tv);
  const tempTxt = tempBadgeText(tv);
  const city = safeCityName(name || t('selected'), 16);
  const S = 2;
  const W = 130 * S, H = 46 * S;
  const c = document.createElement('canvas');
  c.width = W; c.height = H;
  c._superSampling = S;
  const ctx = c.getContext('2d');
  ctx.clearRect(0, 0, W, H);

  // Tooltip background
  ctx.beginPath();
  ctx.roundRect(2 * S, 2 * S, W - 4 * S, H - 4 * S, 14 * S);
  ctx.fillStyle = 'rgba(10,18,36,0.92)';
  ctx.fill();
  ctx.strokeStyle = color;
  ctx.globalAlpha = 0.5;
  ctx.lineWidth = 1.5 * S;
  ctx.stroke();
  ctx.globalAlpha = 1;

  // Weather icon on the left, clipped to a rounded rect so any icon size looks clean
  const iconSize = 30 * S;
  const iconX = 10 * S;
  const iconY = (H - iconSize) / 2;
  if (iconImg && iconImg.complete && iconImg.naturalWidth > 0) {
    ctx.save();
    ctx.beginPath();
    ctx.roundRect(iconX, iconY, iconSize, iconSize, 6 * S);
    ctx.clip();
    ctx.drawImage(iconImg, iconX, iconY, iconSize, iconSize);
    ctx.restore();
  }

  // City name (right of icon, top)
  const textX = 44 * S;
  ctx.font = `700 ${10 * S}px Inter, Arial, sans-serif`;
  ctx.textAlign = 'left';
  ctx.textBaseline = 'middle';
  ctx.fillStyle = '#ffffff';
  ctx.fillText(city, textX, 15 * S);

  // Temperature (right of icon, bottom)
  ctx.font = `800 ${14 * S}px Inter, Arial, sans-serif`;
  ctx.fillStyle = color;
  ctx.fillText(tempTxt, textX, 33 * S);

  return c;
}

// Preloads a weather icon image and calls back with the Image element.
// Used to draw icons directly into marker canvases.
function loadIconImage(iconCode, wmoCode, daytime, callback) {
  const img = new Image();
  img.crossOrigin = 'anonymous';
  img.onload = () => callback(img);
  img.onerror = () => {
    const fallback = new Image();
    fallback.src = buildWeatherIconDataUrl(wmoCode, daytime);
    fallback.onload = () => callback(fallback);
    fallback.onerror = () => callback(null);
  };
  img.src = `/api/icon/${iconCode}`;
}

// Calculates the local time at the weather location using timezone offset
function localTime(data) {
  if (!data || !Number.isFinite(data.timezone) || !Number.isFinite(data.dt)) return '';
  const d = new Date((data.dt + data.timezone) * 1000);
  const h = d.getUTCHours().toString().padStart(2, '0');
  const m = d.getUTCMinutes().toString().padStart(2, '0');
  return `${h}:${m} (local)`;
}

// Shows a temporary hint message at the bottom of the screen
function flashHint(message, duration = 2600) {
  const hint = document.getElementById('hint');
  if (!hint) return;
  hint.textContent = message;
  hint.classList.remove('fade');
  clearTimeout(hintTimer);
  hintTimer = setTimeout(() => hint.classList.add('fade'), duration);
}

// --- API helpers ---
// Builds an API URL with query parameters (e.g. /api/weather?lat=46&lon=6)
function apiPath(path, params = {}) {
  const url = new URL(path, window.location.origin);
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null) url.searchParams.set(k, String(v));
  });
  return `${url.pathname}${url.search}`;
}

// Extracts an error message from a failed API response
async function readErrorMessage(res) {
  try {
    const body = await res.json();
    if (typeof body?.detail === 'string') return body.detail;
  } catch (_) {}
  return `${res.status} ${res.statusText}`;
}

// Fetches current weather from the backend for given coordinates
async function fetchWeatherAt(lat, lon, force = false) {
  const res = await fetch(apiPath('/api/weather', { lat, lon, force }));
  if (!res.ok) throw new Error(await readErrorMessage(res));
  return res.json();
}

// fetchPointWeather is an alias kept for call-site readability
const fetchPointWeather = fetchWeatherAt;

// --- Weather panel ---
// Shows a loading state in the weather panel while data is being fetched
function panelLoading() {
  setText('loc-city', t('fetching'));
  setText('loc-country', '');
  setText('loc-time', '');
  setText('hero-temp', '-');
  setText('hero-desc', '');
  setText('hero-feels', '');
  showEl('weather-panel', true);
  document.getElementById('forecast-scroll').innerHTML =
    '<div class="forecast-placeholder">Loading...</div>';
}

// Fills and shows the weather panel with data (icon, temp, description, forecast)
function showPanel(data, opts = {}) {
  const w0 = data?.weather?.[0] || { id: 0, description: 'weather' };
  const code = Number.isFinite(Number(w0.id)) ? Number(w0.id) : 0;
  const day = isDaytime(data);
  const clouds = Number.isFinite(Number(data?.clouds?.all)) ? Number(data.clouds.all) : null;
  const iconCode = getMeteoIcon(code, day, clouds);
  const temp = Number.isFinite(data?.main?.temp) ? data.main.temp : 0;
  const feelsLike = Number.isFinite(data?.main?.feels_like) ? data.main.feels_like : temp;
  const tc = tempColor(temp);

  setText('loc-city', data.name || t('unknown'));
  setText('loc-country', `${data?.sys?.country || ''}`);
  setText('loc-time', localTime(data));


  // Load weather icon as inline SVG for sharp rendering at any size.
  // Using fetch + innerHTML instead of <img> because browsers rasterize
  // SVGs in <img> at their intrinsic size (40x40), causing blur when scaled.
  const iconWrap = document.getElementById('hero-icon-wrap');
  fetch(`/api/icon/${iconCode}`)
    .then(r => r.ok ? r.text() : null)
    .then(svgText => {
      if (svgText && svgText.includes('<svg')) {
        iconWrap.innerHTML = svgText;
      } else {
        iconWrap.innerHTML = `<img id="hero-icon" src="${buildWeatherIconDataUrl(code, day)}" alt="Weather icon">`;
      }
    })
    .catch(() => {
      iconWrap.innerHTML = `<img id="hero-icon" src="${buildWeatherIconDataUrl(code, day)}" alt="Weather icon">`;
    });

  const tempEl = document.getElementById('hero-temp');
  tempEl.textContent = displayTemp(temp);
  tempEl.style.color = tc;
  setText('hero-desc', cap(w0.description || 'Weather'));
  setText('hero-feels', `${t('feelsLike')} ${displayTemp(feelsLike)}`);

  showEl('weather-panel', true);
  activeMarkerData = data;
  activeTarget = opts.target || (data.coord ? { lat: data.coord.lat, lon: data.coord.lon, source: 'weather' } : null);

  if (data.coord) {
    loadForecast(data.coord.lat, data.coord.lon, !!opts.force);
  }

  if (activeTarget?.lat != null && activeTarget?.lon != null) {
    setActiveMarker(activeTarget.lat, activeTarget.lon, temp, code, day, data.name || '', clouds);
    renderCityMarkers(cityWeatherCache);
  }

  document.getElementById('hint').classList.add('fade');
}

// Hides the weather panel and clears the selected marker
function hidePanel() {
  document.getElementById('weather-panel').classList.remove('active');
  clearActiveMarkers();
  activeMarkerData = null;
  activeTarget = null;
  renderCityMarkers(cityWeatherCache);
}

// Fetches and displays the hourly forecast (48h) from the backend
async function loadForecast(lat, lon, force = false) {
  const scroll = document.getElementById('forecast-scroll');
  scroll.innerHTML = `<div class="forecast-placeholder">${t('forecastLoading')}</div>`;
  const src = document.getElementById('data-source');

  try {
    const res = await fetch(apiPath('/api/forecast', { lat, lon, force }));
    if (!res.ok) throw new Error(await readErrorMessage(res));
    const data = await res.json();

    src.textContent = 'Open-Meteo';
    renderForecast(scroll, data?.daily || []);
    // Draw the temperature curve chart (MeteoSuisse style) for today
    renderTempChart(data?.hourly || []);
  } catch (err) {
    const msg = err?.message || t('forecastUnavailable');
    scroll.innerHTML = `<div class="forecast-placeholder">${t('forecastUnavailable')} (${msg})</div>`;
  }
}

// Renders 7-day forecast cards (day name, icon, min/max temp, rain) into the scroll area
function renderForecast(scroll, daily) {
  if (!daily || !daily.length) {
    scroll.innerHTML = `<div class="forecast-placeholder">${t('noData')}</div>`;
    return;
  }

  scroll.innerHTML = '';
  daily.slice(0, 7).forEach((item, idx) => {
    // Parse date string "2026-03-28"
    const parts = (item.date || '').split('-');
    const dt = new Date(+parts[0], +parts[1] - 1, +parts[2]);
    const dayName = idx === 0 ? t('today') : t('dayNames')[dt.getDay()];
    const tMax = Math.round(item.temp_max ?? 0);
    const tMin = Math.round(item.temp_min ?? 0);
    const code = item.code ?? 0;
    const dayClouds = Number.isFinite(Number(item.clouds)) ? Number(item.clouds) : null;
    const iconCode = getMeteoIcon(code, true, dayClouds);
    const rain = (item.precip ?? 0) >= 0.1 ? `${item.precip.toFixed(1)} mm` : '';

    const cell = document.createElement('div');
    cell.className = 'fc-cell';
    cell.innerHTML = `
      <div class="fc-time">${dayName}</div>
      <div class="fc-icon" data-icon-code="${iconCode}"></div>
      <div class="fc-temp">
        <span style="color:${tempColor(tMax)}">${tMax}°</span>
        <span class="fc-temp-min" style="color:${tempColor(tMin)}">${tMin}°</span>
      </div>
      <div class="fc-rain">${rain}</div>
    `;
    scroll.appendChild(cell);

    // Load inline SVG for crisp rendering at any size
    const fcIconEl = cell.querySelector('.fc-icon');
    fetch(`/api/icon/${iconCode}`)
      .then(r => r.ok ? r.text() : null)
      .then(svgText => {
        if (svgText && svgText.includes('<svg')) {
          fcIconEl.innerHTML = svgText;
        } else {
          fcIconEl.innerHTML = '<span>--</span>';
        }
      })
      .catch(() => { fcIconEl.innerHTML = '<span>--</span>'; });
  });
}

// Draws a MeteoSuisse-style chart: red temperature curve on top, blue rain bars below.
// Data comes as local ISO time strings from the backend (timezone:auto).
// Shows today 00:00-23:00 with a "now" marker, temp labels, and rain mm values.
function renderTempChart(hourly) {
  const canvas = document.getElementById('temp-chart');
  if (!canvas) return;
  const wrap = canvas.parentElement;
  if (!wrap) return;

  if (!hourly || !hourly.length) {
    canvas.width = 0; canvas.height = 0;
    return;
  }

  // Parse local ISO times (e.g. "2026-03-28T14:00") into { hour, temp, precip, pop }
  const parsed = hourly.map(h => {
    const m = (h.time || '').match(/(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/);
    if (!m) return null;
    return {
      year: +m[1], month: +m[2], day: +m[3], hour: +m[4],
      temp: h.temp ?? 0,
      precip: Math.max(0, h.precip ?? 0),
      pop: h.pop ?? 0,
    };
  }).filter(Boolean);

  if (parsed.length < 2) { canvas.width = 0; canvas.height = 0; return; }

  // Filter to today only (same date as the first data point)
  const today = parsed[0];
  const todayPts = parsed.filter(p => p.year === today.year && p.month === today.month && p.day === today.day);
  if (todayPts.length < 2) { canvas.width = 0; canvas.height = 0; return; }

  // High-DPI canvas
  const dpr = window.devicePixelRatio || 1;
  const W = wrap.clientWidth;
  const H = 150;
  canvas.width = W * dpr;
  canvas.height = H * dpr;
  canvas.style.width = W + 'px';
  canvas.style.height = H + 'px';
  const ctx = canvas.getContext('2d');
  ctx.scale(dpr, dpr);

  // Layout zones:
  // Top area: temperature curve (padT to rainTop)
  // Bottom area: rain bars (rainTop to H - padB)
  // Time labels: below everything
  const padL = 30, padR = 30, padT = 18, padB = 18;
  const rainZoneH = 32; // height of the rain bar area
  const gap = 6;        // gap between temp curve and rain bars
  const tempBot = H - padB - rainZoneH - gap;
  const tempH = tempBot - padT;
  const rainTop = H - padB - rainZoneH;
  const rainBot = H - padB;
  const cw = W - padL - padR;

  // Temperature range
  const temps = todayPts.map(p => p.temp);
  let tMin = Math.floor(Math.min(...temps) - 1);
  let tMax = Math.ceil(Math.max(...temps) + 1);
  if (tMax - tMin < 4) { tMin -= 2; tMax += 2; }
  const tRange = tMax - tMin || 1;

  // Rain range (cap at 10mm for display)
  const maxPrecip = Math.max(0.5, ...todayPts.map(p => p.precip));
  const rainCap = Math.min(maxPrecip * 1.3, Math.max(maxPrecip, 2));

  // Map hour -> x position (0-23 across the chart)
  const xOf = (hour) => padL + (hour / 23) * cw;
  const tempY = (t) => padT + tempH - ((t - tMin) / tRange) * tempH;

  // --- Background grid lines (subtle) ---
  ctx.strokeStyle = 'rgba(255,255,255,0.06)';
  ctx.lineWidth = 1;
  // Horizontal lines for temperature zone at nice intervals
  const tStep = tRange <= 8 ? 2 : tRange <= 16 ? 4 : 5;
  for (let t = Math.ceil(tMin / tStep) * tStep; t <= tMax; t += tStep) {
    const y = tempY(t);
    ctx.beginPath(); ctx.moveTo(padL, y); ctx.lineTo(W - padR, y); ctx.stroke();
  }
  // Vertical lines every 6h
  for (let h = 0; h <= 24; h += 6) {
    const x = xOf(h);
    ctx.beginPath(); ctx.moveTo(x, padT); ctx.lineTo(x, rainBot); ctx.stroke();
  }

  // --- Rain bars (blue, MeteoSuisse style) ---
  const barW = Math.max(3, cw / todayPts.length - 1);
  for (const p of todayPts) {
    if (p.precip <= 0.01) continue;
    const x = xOf(p.hour);
    const barH = Math.max(2, (p.precip / rainCap) * rainZoneH);
    const y = rainBot - barH;

    // Gradient blue bar: lighter for small rain, darker for heavy
    const intensity = Math.min(1, p.precip / 5);
    const r = Math.round(30 + 20 * (1 - intensity));
    const g = Math.round(100 + 60 * (1 - intensity));
    const b = Math.round(220 + 35 * (1 - intensity));
    ctx.fillStyle = `rgba(${r},${g},${b},0.85)`;

    // Rounded top bar
    const radius = Math.min(2, barH / 2);
    ctx.beginPath();
    ctx.moveTo(x - barW / 2, rainBot);
    ctx.lineTo(x - barW / 2, y + radius);
    ctx.arcTo(x - barW / 2, y, x, y, radius);
    ctx.arcTo(x + barW / 2, y, x + barW / 2, y + radius, radius);
    ctx.lineTo(x + barW / 2, rainBot);
    ctx.closePath();
    ctx.fill();

    // Show mm value above bar if significant
    if (p.precip >= 0.5) {
      ctx.font = '600 8px Inter, Arial, sans-serif';
      ctx.textAlign = 'center';
      ctx.fillStyle = 'rgba(80,160,255,0.9)';
      ctx.fillText(`${p.precip.toFixed(1)}`, x, y - 3);
    }
  }

  // --- Temperature gradient fill under curve ---
  const gradFill = ctx.createLinearGradient(0, padT, 0, tempBot);
  gradFill.addColorStop(0, 'rgba(220,60,60,0.18)');
  gradFill.addColorStop(1, 'rgba(220,60,60,0.0)');
  ctx.beginPath();
  ctx.moveTo(xOf(todayPts[0].hour), tempBot);
  ctx.lineTo(xOf(todayPts[0].hour), tempY(todayPts[0].temp));
  for (let i = 1; i < todayPts.length; i++) {
    const prev = todayPts[i - 1], cur = todayPts[i];
    const x0 = xOf(prev.hour), y0 = tempY(prev.temp);
    const x1 = xOf(cur.hour), y1 = tempY(cur.temp);
    const cpx = (x0 + x1) / 2;
    ctx.bezierCurveTo(cpx, y0, cpx, y1, x1, y1);
  }
  ctx.lineTo(xOf(todayPts[todayPts.length - 1].hour), tempBot);
  ctx.closePath();
  ctx.fillStyle = gradFill;
  ctx.fill();

  // --- Temperature curve (red line, MeteoSuisse style) ---
  ctx.beginPath();
  ctx.moveTo(xOf(todayPts[0].hour), tempY(todayPts[0].temp));
  for (let i = 1; i < todayPts.length; i++) {
    const prev = todayPts[i - 1], cur = todayPts[i];
    const x0 = xOf(prev.hour), y0 = tempY(prev.temp);
    const x1 = xOf(cur.hour), y1 = tempY(cur.temp);
    const cpx = (x0 + x1) / 2;
    ctx.bezierCurveTo(cpx, y0, cpx, y1, x1, y1);
  }
  ctx.strokeStyle = '#e04040';
  ctx.lineWidth = 2.5;
  ctx.lineJoin = 'round';
  ctx.lineCap = 'round';
  ctx.stroke();

  // --- "Now" vertical marker (red dashed line) ---
  const nowH = new Date().getHours() + new Date().getMinutes() / 60;
  if (nowH >= todayPts[0].hour && nowH <= todayPts[todayPts.length - 1].hour) {
    const nowX = xOf(nowH);
    ctx.setLineDash([4, 3]);
    ctx.strokeStyle = 'rgba(224,64,64,0.6)';
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(nowX, padT);
    ctx.lineTo(nowX, rainBot);
    ctx.stroke();
    ctx.setLineDash([]);

    // Small "now" label
    ctx.font = '700 8px Inter, Arial, sans-serif';
    ctx.textAlign = 'center';
    ctx.fillStyle = 'rgba(224,64,64,0.8)';
    ctx.fillText(t('now'), nowX, padT - 5);
  }

  // --- Temperature labels on left Y-axis ---
  ctx.font = '600 9px Inter, Arial, sans-serif';
  ctx.textAlign = 'right';
  ctx.fillStyle = 'rgba(220,80,80,0.7)';
  for (let t = Math.ceil(tMin / tStep) * tStep; t <= tMax; t += tStep) {
    ctx.fillText(`${t}°`, padL - 4, tempY(t) + 3);
  }

  // --- Rain axis label on right ---
  if (maxPrecip > 0.1) {
    ctx.textAlign = 'left';
    ctx.fillStyle = 'rgba(80,160,255,0.6)';
    ctx.font = '600 8px Inter, Arial, sans-serif';
    ctx.fillText('mm', W - padR + 4, rainTop + 8);
  }

  // --- Time labels at bottom (every 3h) ---
  ctx.font = '600 9px Inter, Arial, sans-serif';
  ctx.textAlign = 'center';
  ctx.fillStyle = 'rgba(255,255,255,0.45)';
  for (let h = 0; h <= 23; h += 3) {
    ctx.fillText(`${h.toString().padStart(2, '0')}h`, xOf(h), H - 4);
  }

  // --- Temperature value labels on curve (every 3h) ---
  ctx.font = '700 9px Inter, Arial, sans-serif';
  ctx.textAlign = 'center';
  for (const p of todayPts) {
    if (p.hour % 3 !== 0) continue;
    const x = xOf(p.hour);
    const y = tempY(p.temp);

    // Small dot on the curve
    ctx.beginPath();
    ctx.arc(x, y, 2.5, 0, Math.PI * 2);
    ctx.fillStyle = '#e04040';
    ctx.fill();

    // Temperature value above or below the dot (avoid overlap with top)
    const labelY = y - 9 < padT ? y + 13 : y - 9;
    ctx.fillStyle = '#ffabab';
    ctx.fillText(`${Math.round(p.temp)}°`, x, labelY);
  }
}

// --- Search ---

// Searches for a location via /api/geocode (Nominatim) and shows results in dropdown
async function doSearch(q, dropdown) {
  let results = [];
  try {
    const res = await fetch(apiPath('/api/geocode', { q }));
    if (!res.ok) throw new Error(await readErrorMessage(res));
    results = await res.json();
  } catch (_) {
  }

  dropdown.innerHTML = '';
  if (!Array.isArray(results) || !results.length) {
    dropdown.innerHTML = `<div class="no-results">${t('noResults')}</div>`;
    return;
  }

  results.slice(0, 8).forEach((r) => {
    const item = document.createElement('div');
    item.className = 'search-result';
    const cc = /^[A-Za-z]{2}$/.test(r.country || '') ? r.country.toUpperCase() : '';
    item.innerHTML = `
      <div>
        <div class="sr-name">${r.name}</div>
        <div class="sr-sub">${[r.state || '', cc || r.country || ''].filter(Boolean).join(' | ') || 'Location'}</div>
      </div>
      <span class="sr-flag">${cc || 'GLB'}</span>
    `;
    item.addEventListener('click', async () => {
      dropdown.innerHTML = '';
      document.getElementById('search-input').value = r.name;
      panelLoading();
      stopRotation();
      flyToLocation(r.lat, r.lon, 900000, 1.8);
      try {
        const data = await fetchPointWeather(r.lat, r.lon);
        showPanel(data, { target: { lat: r.lat, lon: r.lon, source: 'search' } });
      } catch (err) {
        hidePanel();
        flashHint(`${t('searchError')}: ${err.message}`, 4200);
      }
    });
    dropdown.appendChild(item);
  });
}

// Sets up the search bar: typing triggers a debounced search, clear button resets it
function initSearch() {
  const input = document.getElementById('search-input');
  const clearBtn = document.getElementById('search-clear');
  const dropdown = document.getElementById('search-results');

  input.addEventListener('input', () => {
    const q = input.value.trim();
    clearBtn.style.display = q ? 'block' : 'none';
    clearTimeout(searchTimer);
    if (q.length < 2) {
      dropdown.innerHTML = '';
      return;
    }
    searchTimer = setTimeout(() => doSearch(q, dropdown), 250);
  });

  clearBtn.addEventListener('click', () => {
    input.value = '';
    clearBtn.style.display = 'none';
    dropdown.innerHTML = '';
    input.focus();
  });
}

// --- Globe rotation (used by screensaver) ---
// Light-weight rotation tuned for low-power devices (Raspberry Pi):
// keeps requestRenderMode = true, only requests a render on each rotation tick
// (~15 fps), and refreshes marker visibility every 6 ticks (~600ms).
function stopRotation() {
  if (rotateTimer) {
    clearInterval(rotateTimer);
    rotateTimer = null;
  }
}

function startRotation() {
  if (rotateTimer) return;
  const viewer = map?.viewer;
  const scene = viewer?.scene;
  if (!viewer || !scene) return;
  // Step in radians per tick so the spin speed stays consistent if we change tick rate.
  const radPerTick = window.Cesium.Math.toRadians(ROTATION_STEP_DEG);
  let visibilityCounter = 0;
  rotateTimer = setInterval(() => {
    if (!viewer.camera) return;
    viewer.camera.rotate(window.Cesium.Cartesian3.UNIT_Z, radPerTick);
    scene.requestRender();
    visibilityCounter++;
    // ~12 ticks at 50ms = 600ms between visibility recomputes — keeps the
    // collision pass off the per-frame critical path.
    if (visibilityCounter >= 12) {
      visibilityCounter = 0;
      updateCityTierVisibility();
    }
  }, ROTATION_TICK_MS);
}

// --- Camera controls ---
// Moves the camera to center on a location at a given zoom range (instant, no animation)
function focusOn(lat, lon, range = 1_000_000) {
  if (!map) return;
  const zoom = rangeToZoom(range);
  map.panTo({ lat, lng: lon });
  map.setZoom(zoom);
}

// Smoothly animates the camera to a location over `durationSec` seconds.
// Falls back to an instant focusOn if the underlying map adapter has no flyTo method.
function flyToLocation(lat, lon, range = 1_000_000, durationSec = 1.8) {
  if (!map) return;
  if (typeof map.flyTo === 'function') {
    map.flyTo({ lat, lng: lon, range, duration: durationSec });
  } else {
    focusOn(lat, lon, range);
  }
}

function zoomIn() {
  if (!map) return;
  map.setZoom(Math.min(20, (map.getZoom() ?? 2) + 1));
}

function zoomOut() {
  if (!map) return;
  map.setZoom(Math.max(2, (map.getZoom() ?? 2) - 1));
}

// --- City markers on the globe ---
// Checks if coordinates are close to the currently selected location
// (used to hide the city marker when it overlaps with the active selection marker)
function isNearActiveTarget(lat, lon) {
  if (!activeTarget || !Number.isFinite(activeTarget.lat) || !Number.isFinite(activeTarget.lon)) {
    return false;
  }
  // Keep the selected city hidden from the base city layer to avoid doubled markers.
  return Math.abs(activeTarget.lat - lat) <= 0.08 && Math.abs(activeTarget.lon - lon) <= 0.08;
}

// Removes all city weather markers from the globe
function clearCityMarkers() {
  for (const { bubble, icon } of cityPlacemarkMap.values()) {
    if (bubble) bubble.setMap(null);
    if (icon) icon.setMap(null);
  }
  cityPlacemarkMap.clear();
}

// Removes the selected location marker from the globe
function clearActiveMarkers() {
  for (const m of activeMarkerObjects) m.setMap(null);
  activeMarkerObjects = [];
}

function markerSizeValue(sizeOrNumber, fallback) {
  if (sizeOrNumber && typeof sizeOrNumber.width === 'number') return sizeOrNumber.width;
  const n = Number(sizeOrNumber);
  return Number.isFinite(n) ? n : fallback;
}

function markerPointValue(pointOrNumber, axis, fallback) {
  if (pointOrNumber && typeof pointOrNumber[axis] === 'number') return pointOrNumber[axis];
  const n = Number(pointOrNumber);
  return Number.isFinite(n) ? n : fallback;
}

// Creates a billboard marker on the globe (image or canvas) at given coordinates.
// Returns an object with setMap()/setVisible()/setIcon() methods.
// zIndex controls rendering order (higher = in front).
function createImageMarker(lat, lon, imageSource, width, height, anchorX, anchorY, zIndex = 1000, visible = true) {
  if (!map?.viewer || !window.Cesium) {
    return {
      setMap() {},
      setVisible() {},
      setIcon() {},
    };
  }
  const C = window.Cesium;
  let removed = false;

  // If imageSource is a Canvas, use native resolution with scale — no resampling.
  // If it's a URL string, use explicit width/height as before.
  const isCanvas = imageSource instanceof HTMLCanvasElement;
  const billboardOpts = {
    image: imageSource,
    horizontalOrigin: C.HorizontalOrigin.LEFT,
    verticalOrigin: C.VerticalOrigin.TOP,
    pixelOffset: new C.Cartesian2(-anchorX, -anchorY),
    eyeOffset: new C.Cartesian3(0, 0, -(zIndex / 10)),
    disableDepthTestDistance: 0,
  };
  if (isCanvas) {
    billboardOpts.scale = 1 / (imageSource._superSampling || 2);
  } else {
    billboardOpts.width = width;
    billboardOpts.height = height;
  }

  const entity = map.viewer.entities.add({
    position: C.Cartesian3.fromDegrees(lon, lat, 0),
    show: !!visible,
    billboard: billboardOpts,
  });

  return {
    setMap(nextMap) {
      if (removed) return;
      if (!nextMap) {
        map.viewer.entities.remove(entity);
        removed = true;
        return;
      }
      entity.show = true;
    },
    setVisible(nextVisible) {
      if (removed) return;
      entity.show = !!nextVisible;
    },
    setIcon(iconOpts) {
      if (removed || !entity.billboard) return;
      const nextImg = iconOpts?.url || imageSource;
      const nextAx = markerPointValue(iconOpts?.anchor, 'x', anchorX);
      const nextAy = markerPointValue(iconOpts?.anchor?.y, 'y', anchorY);
      entity.billboard.image = nextImg;
      if (nextImg instanceof HTMLCanvasElement) {
        entity.billboard.scale = 1 / (nextImg._superSampling || 2);
        entity.billboard.width = undefined;
        entity.billboard.height = undefined;
      } else {
        entity.billboard.width = markerSizeValue(iconOpts?.scaledSize, width);
        entity.billboard.height = markerSizeValue(iconOpts?.scaledSize?.height, height);
        entity.billboard.scale = undefined;
      }
      entity.billboard.pixelOffset = new C.Cartesian2(-nextAx, -nextAy);
    },
  };
}

// Draws weather markers for all cities on the globe.
// Each city gets a single pill marker with icon + temperature drawn into one canvas.
// During screensaver, uses compact pills and shows every tier so the globe feels alive.
function renderCityMarkers(results) {
  if (!map) return;
  clearCityMarkers();

  const compact = screensaverActive;
  const dims = compact ? PILL_COMPACT : PILL_FULL;
  const zoom = map.getZoom() ?? 2;
  // Screensaver shows tiers 1+2 (~62 cities) — tier 3 is too small to read while
  // the globe is spinning, and skipping it cuts billboard count by a third on the Pi.
  const maxTier = compact ? 2 : getMaxCityTier(zoomToRange(zoom));
  lastZoomTier = maxTier;

  for (const r of results) {
    if (!r || !r.weather) continue;
    if (isNearActiveTarget(r.lat, r.lon)) continue;
    const cityTier = CITY_TIER.get(r.name) ?? 2;

    const w = r.weather;
    const code = w?.weather?.[0]?.id ?? 0;
    const day = isDaytime(w);
    const cityClouds = Number.isFinite(Number(w?.clouds?.all)) ? Number(w.clouds.all) : null;
    const iconCode = getMeteoIcon(code, day, cityClouds);
    const temp = asFiniteNumber(w?.main?.temp, 0);
    const show = cityTier <= maxTier;

    // First render without icon (shows colored dot fallback)
    const labelCanvas = buildCityLabelCanvas({ name: r.name, temp, compact });
    const label = createImageMarker(r.lat, r.lon, labelCanvas, dims.w, dims.h, dims.w / 2, dims.h, 1100, show);

    // Load icon and re-render the pill with the icon embedded
    loadIconImage(iconCode, code, day, (iconImg) => {
      if (iconImg) {
        const updated = buildCityLabelCanvas({ name: r.name, temp, iconImg, compact });
        label.setIcon({ url: updated, scaledSize: { width: dims.w, height: dims.h }, anchor: { x: dims.w / 2, y: dims.h } });
      }
    });

    // Cache the Cartesian3 position so the visibility pass doesn't re-allocate
    // 90 vectors per frame during the screensaver spin.
    const cartPos = window.Cesium
      ? window.Cesium.Cartesian3.fromDegrees(r.lon, r.lat, 0)
      : null;
    cityPlacemarkMap.set(r.name, { bubble: label, icon: null, tier: cityTier, lat: r.lat, lon: r.lon, pos: cartPos, pillW: dims.w, pillH: dims.h });
  }

  // Initial collision pass once Cesium has projected the new entities
  setTimeout(updateCityTierVisibility, 50);
}

// Shows/hides city markers based on zoom tier, backside culling, and screen-space
// collision detection. Tier filtering decides which cities are eligible at the current
// zoom; backside culling removes anything on the far side of the globe; collision
// detection then hides any pill whose screen rect overlaps a higher-priority pill.
function updateCityTierVisibility() {
  if (!cityPlacemarkMap.size) return;
  const zoom = map?.getZoom?.() ?? 2;
  // Screensaver caps at tier 2; normal view tier-filters by zoom.
  const maxTier = screensaverActive ? 2 : getMaxCityTier(zoomToRange(zoom));
  lastZoomTier = maxTier;

  const C = window.Cesium;
  const viewer = map?.viewer;
  const scene = viewer?.scene;
  if (!C || !viewer || !scene) {
    // Fallback to tier-only filtering if Cesium isn't ready
    for (const { bubble, icon, tier } of cityPlacemarkMap.values()) {
      const show = tier <= maxTier;
      if (bubble) bubble.setVisible(show);
      if (icon) icon.setVisible(show);
    }
    return;
  }

  const PAD = 4;

  // Backside culling: skip points hidden behind the globe from the camera's POV.
  const occluder = new C.EllipsoidalOccluder(scene.globe.ellipsoid, viewer.camera.position);
  // Cesium ≥1.110 renamed wgs84ToWindowCoordinates → worldToWindowCoordinates;
  // pick whichever the loaded build actually exposes so we work on both.
  const projectToScreen = C.SceneTransforms.worldToWindowCoordinates
    || C.SceneTransforms.wgs84ToWindowCoordinates;

  const candidates = [];
  for (const m of cityPlacemarkMap.values()) {
    if (m.tier > maxTier) {
      m.bubble?.setVisible(false);
      m.icon?.setVisible(false);
      continue;
    }
    const pos = m.pos;
    if (!pos) {
      m.bubble?.setVisible(false);
      continue;
    }
    if (!occluder.isPointVisible(pos)) {
      m.bubble?.setVisible(false);
      continue;
    }
    const screen = projectToScreen(scene, pos);
    if (!screen || !Number.isFinite(screen.x)) {
      m.bubble?.setVisible(false);
      continue;
    }
    candidates.push({ m, x: screen.x, y: screen.y });
  }
  // Tier 1 wins over tier 2 wins over tier 3 in collision contests.
  candidates.sort((a, b) => a.m.tier - b.m.tier);

  // Greedy placement: hide any marker whose box overlaps an already-placed one.
  // Each marker's box is sized from its own pill dimensions (compact vs full).
  const placed = [];
  for (const it of candidates) {
    const halfW = (it.m.pillW ?? PILL_FULL.w) / 2;
    const fullH = it.m.pillH ?? PILL_FULL.h;
    const left = it.x - halfW, right = it.x + halfW;
    const top = it.y - fullH, bottom = it.y;
    let collides = false;
    for (const p of placed) {
      if (left < p.right + PAD && right > p.left - PAD && top < p.bottom + PAD && bottom > p.top - PAD) {
        collides = true;
        break;
      }
    }
    it.m.bubble?.setVisible(!collides);
    if (!collides) placed.push({ left, right, top, bottom });
  }
}

// Schedules a retry to load city weather if the first attempt failed
function scheduleCityRetry(delayMs = 30_000) {
  if (cityRetryTimer) return;
  cityRetryTimer = setTimeout(async () => {
    cityRetryTimer = null;
    await loadCityMarkers(false);
  }, delayMs);
}

// Fetches weather for all cities from /api/cities and renders their markers on the globe
async function loadCityMarkers(force = false) {
  try {
    const res = await fetch(force ? '/api/cities?force=true' : '/api/cities', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ cities: CITIES }),
    });
    if (!res.ok) {
      if (!cityWeatherCache.length) {
        flashHint(t('cityUnavail'), 4200);
        scheduleCityRetry();
      }
      return;
    }
    const next = await res.json();
    if (Array.isArray(next) && next.length) {
      cityWeatherCache = next;
      renderCityMarkers(cityWeatherCache);
      if (cityRetryTimer) {
        clearTimeout(cityRetryTimer);
        cityRetryTimer = null;
      }
      return;
    }
    if (!cityWeatherCache.length) {
      flashHint(t('cityUnavail'), 4200);
      scheduleCityRetry();
    }
  } catch (_) {
    if (!cityWeatherCache.length) {
      flashHint(t('cityUnavail'), 4200);
      scheduleCityRetry();
    }
  }
}

// Places a highlighted marker on the globe for the currently selected location
// Places a single highlighted marker on the globe for the currently selected location.
// The icon is drawn directly into the tooltip canvas so it always stays aligned.
function setActiveMarker(lat, lon, temp, wmoCode, day, name, cloudCover = null) {
  if (!map) return;
  clearActiveMarkers();
  const iconCode = getMeteoIcon(wmoCode, day, cloudCover);
  const tempVal = asFiniteNumber(temp, 0);
  const markerName = name || t('selected');

  // First render without icon
  const labelCanvas = buildActiveMarkerCanvas({ name: markerName, temp: tempVal });
  const label = createImageMarker(lat, lon, labelCanvas, 130, 46, 65, 46, 2200, true);

  // Load icon and re-render with the icon embedded
  loadIconImage(iconCode, wmoCode, day, (iconImg) => {
    if (iconImg) {
      const updated = buildActiveMarkerCanvas({ name: markerName, temp: tempVal, iconImg });
      label.setIcon({ url: updated, scaledSize: { width: 130, height: 46 }, anchor: { x: 65, y: 46 } });
    }
  });

  activeMarkerObjects = [label];
}

// Called when the user clicks on the globe: zooms in, fetches weather, shows panel
async function onMapPick(lat, lon, source = 'manual') {
  stopRotation();
  focusOn(lat, lon, Math.max(2_500, (zoomToRange(map?.getZoom?.() ?? 2)) * 0.72));
  panelLoading();
  try {
    const data = await fetchPointWeather(lat, lon);
    showPanel(data, { target: { lat, lon, source } });
  } catch (err) {
    hidePanel();
    flashHint(`${t('weatherError')}: ${err.message}`, 4200);
  }
}

// --- Cesium camera helpers ---
// Wraps longitude to [-180, 180] range.
// The +540 trick handles negative inputs correctly across the 180° seam.
function normalizeLon(lon) {
  return ((lon % 360) + 540) % 360 - 180;
}

// Gets the camera altitude (height above the globe in metres)
function getCameraRange(viewer) {
  const h = viewer?.camera?.positionCartographic?.height;
  return Number.isFinite(h) ? h : HOME_VIEW.range;
}

// Gets the lat/lon that the camera is currently looking at (center of screen)
function getCameraCenter(viewer) {
  if (!viewer || !window.Cesium) return { lat: HOME_VIEW.lat, lon: HOME_VIEW.lon };
  const C = window.Cesium;
  const scene = viewer.scene;
  const canvas = scene?.canvas;
  if (!canvas) return { lat: HOME_VIEW.lat, lon: HOME_VIEW.lon };
  const ray = viewer.camera.getPickRay(new C.Cartesian2(canvas.clientWidth / 2, canvas.clientHeight / 2));
  const picked = ray ? scene.globe.pick(ray, scene) : null;
  if (picked) {
    const cart = C.Cartographic.fromCartesian(picked);
    return {
      lat: C.Math.toDegrees(cart.latitude),
      lon: C.Math.toDegrees(cart.longitude),
    };
  }
  const cam = viewer.camera.positionCartographic;
  if (cam) {
    return {
      lat: C.Math.toDegrees(cam.latitude),
      lon: C.Math.toDegrees(cam.longitude),
    };
  }
  return { lat: HOME_VIEW.lat, lon: HOME_VIEW.lon };
}

function getHeadingDeg(viewer) {
  if (!viewer || !window.Cesium) return 0;
  const C = window.Cesium;
  const h = C.Math.toDegrees(viewer.camera.heading || 0);
  return ((h % 360) + 360) % 360;
}

function getTiltDeg(viewer) {
  if (!viewer || !window.Cesium) return 45;
  const C = window.Cesium;
  const p = C.Math.toDegrees(viewer.camera.pitch || 0);
  return Math.max(5, Math.min(85, Math.abs(p)));
}

// Moves the Cesium camera to look at a specific lat/lon/altitude with optional heading/tilt
function setCameraView(viewer, lat, lon, range, headingDeg = null, tiltDeg = null) {
  if (!viewer || !window.Cesium) return;
  const C = window.Cesium;
  const h = headingDeg == null ? getHeadingDeg(viewer) : headingDeg;
  const t = tiltDeg == null ? getTiltDeg(viewer) : tiltDeg;
  viewer.camera.setView({
    // Clamp latitude to +/-85 (avoid flipping at the poles) and range to >= 2 km (avoid clipping into the globe).
    destination: C.Cartesian3.fromDegrees(normalizeLon(lon), Math.max(-85, Math.min(85, lat)), Math.max(2_000, range)),
    orientation: {
      heading: C.Math.toRadians(h),
      pitch: C.Math.toRadians(-Math.max(5, Math.min(85, t))),
      roll: 0,
    },
  });
}

// Smoothly animates the Cesium camera toward a target lat/lon/altitude over `durationSec` seconds.
// Cancels any in-flight animation before starting a new one so successive calls don't queue up.
function flyCameraTo(viewer, lat, lon, range, durationSec = 1.6, headingDeg = null, tiltDeg = null) {
  if (!viewer || !window.Cesium) return;
  const C = window.Cesium;
  const h = headingDeg == null ? getHeadingDeg(viewer) : headingDeg;
  const t = tiltDeg == null ? getTiltDeg(viewer) : tiltDeg;
  viewer.camera.cancelFlight();
  viewer.camera.flyTo({
    destination: C.Cartesian3.fromDegrees(normalizeLon(lon), Math.max(-85, Math.min(85, lat)), Math.max(2_000, range)),
    orientation: {
      heading: C.Math.toRadians(h),
      pitch: C.Math.toRadians(-Math.max(5, Math.min(85, t))),
      roll: 0,
    },
    duration: Math.max(0, durationSec),
  });
}

// Converts a screen pixel position to lat/lon on the globe surface
function pickLatLonFromScreen(viewer, pos) {
  if (!viewer || !window.Cesium || !pos) return null;
  const C = window.Cesium;
  const cartesian = viewer.camera.pickEllipsoid(pos, viewer.scene.globe.ellipsoid);
  if (!cartesian) return null;
  const cartographic = C.Cartographic.fromCartesian(cartesian);
  return {
    lat: C.Math.toDegrees(cartographic.latitude),
    lon: C.Math.toDegrees(cartographic.longitude),
  };
}

// --- Cesium map adapter ---
// Wraps the Cesium Viewer in a simpler interface (panTo, setZoom, getZoom, addListener, etc.)
// so the rest of the app doesn't need to know Cesium-specific API details.
function createCesiumMapAdapter(viewer) {
  const C = window.Cesium;
  const listeners = {
    click: [],
    zoom_changed: [],
    dragstart: [],
    move_end: [],
  };
  const emit = (type, payload) => {
    const list = listeners[type] || [];
    for (const cb of [...list]) {
      try { cb(payload); } catch (_) {}
    }
  };

  const handler = new C.ScreenSpaceEventHandler(viewer.scene.canvas);
  handler.setInputAction((movement) => {
    const ll = pickLatLonFromScreen(viewer, movement?.position);
    if (!ll) return;
    emit('click', {
      latLng: {
        lat: () => ll.lat,
        lng: () => ll.lon,
      },
    });
  }, C.ScreenSpaceEventType.LEFT_CLICK);
  handler.setInputAction(() => emit('dragstart'), C.ScreenSpaceEventType.LEFT_DOWN);
  handler.setInputAction(() => emit('dragstart'), C.ScreenSpaceEventType.MIDDLE_DOWN);
  handler.setInputAction(() => emit('dragstart'), C.ScreenSpaceEventType.RIGHT_DOWN);

  let lastZoom = rangeToZoom(getCameraRange(viewer));
  viewer.camera.percentageChanged = 0.0008;
  viewer.camera.changed.addEventListener(() => {
    const z = rangeToZoom(getCameraRange(viewer));
    if (z !== lastZoom) {
      lastZoom = z;
      emit('zoom_changed');
    }
  });
  // Native moveEnd fires once after a camera move settles — perfect for collision recompute.
  // It does NOT fire during continuous auto-rotation, so the screensaver spin stays smooth.
  viewer.camera.moveEnd.addEventListener(() => emit('move_end'));

  return {
    viewer,
    addListener(type, cb) {
      if (!listeners[type]) listeners[type] = [];
      listeners[type].push(cb);
      return {
        remove() {
          listeners[type] = (listeners[type] || []).filter(fn => fn !== cb);
        },
      };
    },
    panTo({ lat, lng }) {
      setCameraView(viewer, lat, lng, getCameraRange(viewer));
    },
    flyTo({ lat, lng, range, duration }) {
      const r = Number.isFinite(range) ? range : getCameraRange(viewer);
      flyCameraTo(viewer, lat, lng, r, duration);
    },
    setZoom(z) {
      const c = getCameraCenter(viewer);
      setCameraView(viewer, c.lat, c.lon, zoomToRange(z));
    },
    getZoom() {
      return rangeToZoom(getCameraRange(viewer));
    },
    getCenter() {
      const c = getCameraCenter(viewer);
      return {
        lat: () => c.lat,
        lng: () => c.lon,
      };
    },
    getHeading() {
      return getHeadingDeg(viewer);
    },
    setHeading(deg) {
      const c = getCameraCenter(viewer);
      setCameraView(viewer, c.lat, c.lon, getCameraRange(viewer), deg);
    },
    setTilt(deg) {
      const c = getCameraCenter(viewer);
      setCameraView(viewer, c.lat, c.lon, getCameraRange(viewer), null, deg);
    },
  };
}

// Connects globe events to app logic (click->weather, zoom->update markers, drag->stop rotation)
function bindMapEventHandlers(nextMap) {
  nextMap.addListener('click', async (ev) => {
    if (!ev?.latLng) return;
    await onMapPick(ev.latLng.lat(), ev.latLng.lng(), 'manual');
  });
  nextMap.addListener('zoom_changed', () => {
    stopRotation();
    clearTimeout(zoomRenderTimer);
    zoomRenderTimer = setTimeout(updateCityTierVisibility, 80);
  });
  nextMap.addListener('move_end', () => {
    // Skip during screensaver spin: the camera is moving every frame, so the
    // collision pass would re-run continuously and stutter the rotation.
    if (rotateTimer) return;
    clearTimeout(zoomRenderTimer);
    zoomRenderTimer = setTimeout(updateCityTierVisibility, 80);
  });
  nextMap.addListener('dragstart', stopRotation);
}

// --- Globe imagery ---
// Adds satellite imagery to the globe. Tries in order:
// 1. Esri World Imagery (via local caching proxy on the Pi)
// 2. CesiumJS built-in NaturalEarthII texture
// 3. Public OpenStreetMap tiles (last resort)
// Also adds Esri label overlay (city/road names) on top of satellite imagery.
async function addBaseImageryLayer(C, viewer) {
  // Esri World Imagery via local caching proxy (tiles stored on Pi after first fetch)
  let baseAdded = false;
  try {
    const provider = new C.UrlTemplateImageryProvider({
      url: '/api/sat/imagery/{z}/{x}/{y}',
      credit: 'Esri World Imagery',
      maximumLevel: 17,
    });
    viewer.imageryLayers.addImageryProvider(provider, 0);
    baseAdded = true;
  } catch (_) {}
  if (!baseAdded) {
    // Fallback: NaturalEarthII bundled with Cesium
    try {
      const ne = await C.TileMapServiceImageryProvider.fromUrl(
        C.buildModuleUrl('Assets/Textures/NaturalEarthII')
      );
      viewer.imageryLayers.addImageryProvider(ne, 0);
      baseAdded = true;
    } catch (_) {}
  }
  if (!baseAdded) {
    // Last resort: public OpenStreetMap tiles (includes labels)
    viewer.imageryLayers.addImageryProvider(new C.UrlTemplateImageryProvider({
      url: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
      credit: '(c) OpenStreetMap contributors',
      maximumLevel: 19,
    }), 0);
    return; // OSM already has labels, skip label overlay
  }
  // Esri labels overlay via local caching proxy
  try {
    const labels = new C.UrlTemplateImageryProvider({
      url: '/api/sat/labels/{z}/{x}/{y}',
      credit: 'Esri Reference',
      maximumLevel: 17,
    });
    viewer.imageryLayers.addImageryProvider(labels);
  } catch (_) {}
}

// --- Map initialization ---
// Creates the CesiumJS 3D globe viewer with satellite imagery, dark base color,
// and camera controls. Blocks right-click context menu on the globe.
function initMap() {
  const container = document.getElementById('globe-container');
  container.innerHTML = '';
  const C = window.Cesium;
  // Wrap construction in try/catch: if the device can't give us a WebGL
  // context at all (no GPU + Chrome blocking software fallback, etc.), we
  // show a static fallback panel instead of letting the whole app die.
  let viewer;
  try {
    viewer = new C.Viewer(container, {
      animation: false,
      timeline: false,
      baseLayerPicker: false,
      geocoder: false,
      homeButton: false,
      sceneModePicker: false,
      navigationHelpButton: false,
      fullscreenButton: false,
      infoBox: false,
      selectionIndicator: false,
      terrainProvider: new C.EllipsoidTerrainProvider(),
      baseLayer: false,
      // Bare-minimum contextOptions: just relax the performance caveat so the
      // browser accepts a software-rendered fallback. Don't override alpha,
      // antialias, or webgl version — let Cesium pick its own defaults to
      // maximize the chance that the GPU/driver accepts the request.
      contextOptions: {
        webgl: {
          failIfMajorPerformanceCaveat: false,
        },
      },
    });
  } catch (err) {
    console.error('Cesium init failed:', err);
    container.innerHTML = `
      <div style="display:flex;align-items:center;justify-content:center;height:100vh;color:#fff;font-family:Inter,sans-serif;text-align:center;padding:20px;">
        <div>
          <div style="font-size:48px;margin-bottom:16px;">&#127757;</div>
          <div style="font-size:18px;margin-bottom:8px;">3D globe unavailable</div>
          <div style="font-size:13px;opacity:0.7;">This device or browser doesn't support the required WebGL features.<br>Try another browser, enable hardware acceleration, or update GPU drivers.</div>
        </div>
      </div>`;
    throw err;
  }
  // Dark base color prevents blue flash while satellite imagery loads
  viewer.scene.globe.baseColor = C.Color.fromCssColorString('#0a1628');
  // Mobile GPUs choke on retina-scale Cesium rendering + sun-lit shader.
  // Cap resolution and skip lighting on touch devices to keep things smooth.
  const isMobile = /Mobi|Android|iPhone|iPad/i.test(navigator.userAgent);
  // Software renderers (SwiftShader, llvmpipe, Microsoft Basic Render) can't
  // compile Cesium's lit-globe shader and crash on fullscreen resize at high
  // resolution. Detect via the WEBGL_debug_renderer_info extension and treat
  // them like mobile.
  let isSoftware = false;
  try {
    const probe = viewer.scene.canvas.getContext('webgl2')
      || viewer.scene.canvas.getContext('webgl');
    const dbg = probe?.getExtension('WEBGL_debug_renderer_info');
    const renderer = dbg ? probe.getParameter(dbg.UNMASKED_RENDERER_WEBGL) : '';
    isSoftware = /swiftshader|software|llvmpipe|microsoft basic render/i.test(renderer);
  } catch (_) {}
  const lowPower = isMobile || isSoftware;
  viewer.useBrowserRecommendedResolution = false;
  viewer.resolutionScale = lowPower ? 1 : Math.min(window.devicePixelRatio || 1, 2);
  // Only repaint when the scene actually changes (camera, entity, imagery).
  // Massive GPU/battery win on mobile with no quality loss.
  viewer.scene.requestRenderMode = true;
  viewer.scene.maximumRenderTimeChange = Infinity;
  // Satellite base layer (Esri World Imagery → NaturalEarthII → public OSM)
  addBaseImageryLayer(C, viewer);

  viewer.scene.globe.enableLighting = !lowPower;
  viewer.scene.screenSpaceCameraController.minimumZoomDistance = 2_000;
  viewer.scene.screenSpaceCameraController.maximumZoomDistance = 40_000_000;
  viewer.scene.screenSpaceCameraController.enableTilt = true;

  // Render-error recovery: with resize-reload handling viewport changes, the
  // remaining cause of mid-session render errors is async imagery / texture
  // loading. One recovery attempt (drop lighting + halve resolution) is enough
  // — if it fails again, prompt the user to reload.
  let recoveryDone = false;
  viewer.scene.renderError.addEventListener((_scene, err) => {
    console.warn('Cesium render error:', err);
    if (recoveryDone) {
      flashHint('Globe rendering failed. Reload to retry.', 12000);
      return;
    }
    recoveryDone = true;
    try {
      viewer.scene.globe.enableLighting = false;
      viewer.resolutionScale = 0.5;
      viewer.useDefaultRenderLoop = true;
      viewer.scene.requestRender();
    } catch (_) {}
  });

  map = createCesiumMapAdapter(viewer);
  bindMapEventHandlers(map);
  focusOn(HOME_VIEW.lat, HOME_VIEW.lon, HOME_VIEW.range);

  if (!mapContextMenuBound) {
    container.addEventListener('contextmenu', (ev) => {
      ev.preventDefault();
      ev.stopPropagation();
    }, true);
    mapContextMenuBound = true;
  }

  // WebGL recovery: on the Pi GPU the context can be lost under pressure.
  // Cesium's shader recompile sometimes fails after a loss, leaving a frozen
  // canvas. Stop the spin (frees GPU work) and reload once — using sessionStorage
  // so a broken GPU doesn't trap the user in an infinite reload loop.
  const glCanvas = viewer.scene?.canvas;
  if (glCanvas) {
    glCanvas.addEventListener('webglcontextlost', (ev) => {
      ev.preventDefault();
      try { stopRotation(); } catch (_) {}
      const alreadyReloaded = sessionStorage.getItem('mg_webgl_reloaded') === '1';
      if (alreadyReloaded) {
        flashHint('GPU context lost. Close other tabs and reload manually.', 15000);
        return;
      }
      sessionStorage.setItem('mg_webgl_reloaded', '1');
      setTimeout(() => location.reload(), 1500);
    }, false);
    glCanvas.addEventListener('webglcontextrestored', () => {
      // Clear the reload guard so a future independent loss can recover too.
      sessionStorage.removeItem('mg_webgl_reloaded');
    }, false);
  }

  // Resize / fullscreen strategy: rather than try to keep Cesium happy through
  // every viewport change (which historically caused shader recompile failures
  // and framebuffer-realloc crashes on weak GPUs), reload the page once the
  // resize settles. The loading screen appears instantly so the user has
  // immediate feedback, and the reload fires 250ms after the last resize event.
  let lastSize = `${window.innerWidth}x${window.innerHeight}`;
  let reloadTimer = null;
  const scheduleReload = () => {
    const next = `${window.innerWidth}x${window.innerHeight}`;
    if (next === lastSize) return;
    lastSize = next;
    // Show the loader instantly. The CSS sets a 0.7s opacity transition for
    // the initial fade-out; override it with style.transition='none' so the
    // resize-triggered show is immediate.
    const loader = document.getElementById('loading-screen');
    if (loader) {
      loader.style.transition = 'none';
      loader.classList.remove('hidden');
      loader.style.opacity = '1';
      loader.style.visibility = 'visible';
    }
    clearTimeout(reloadTimer);
    reloadTimer = setTimeout(() => location.reload(), 250);
  };
  window.addEventListener('resize', scheduleReload);
  document.addEventListener('fullscreenchange', scheduleReload);
  document.addEventListener('webkitfullscreenchange', scheduleReload);

  setText('map-attrib', '3D globe by CesiumJS | Esri World Imagery');
}

// --- Geolocation ---
// Promisified wrapper around the browser's geolocation API
function getCurrentPosition(options) {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) {
      reject(new Error('Geolocation not supported'));
      return;
    }
    navigator.geolocation.getCurrentPosition(resolve, reject, options);
  });
}

// Checks if the browser has granted/denied/prompt geolocation permission
async function geolocationPermissionState() {
  if (!navigator.permissions?.query) return 'unknown';
  try {
    const status = await navigator.permissions.query({ name: 'geolocation' });
    return status?.state || 'unknown';
  } catch (_) {
    return 'unknown';
  }
}

// Gets the best GPS position available (watches for accuracy improvements up to 13s)
async function getBestCurrentPosition() {
  try {
    return await new Promise((resolve, reject) => {
      let best = null;
      let done = false;
      let watchId = null;

      const finish = (pos, err) => {
        if (done) return;
        done = true;
        if (watchId != null) navigator.geolocation.clearWatch(watchId);
        clearTimeout(timeoutId);
        if (pos) resolve(pos);
        else reject(err || new Error('Unable to get location'));
      };

      watchId = navigator.geolocation.watchPosition(
        pos => {
          if (!best || (pos.coords?.accuracy ?? Infinity) < (best.coords?.accuracy ?? Infinity)) best = pos;
          if ((pos.coords?.accuracy ?? Infinity) <= 150) finish(pos, null);
        },
        err => {
          if (best) finish(best, null);
          else finish(null, new Error(err?.message || 'Location error'));
        },
        { enableHighAccuracy: true, timeout: 12000, maximumAge: 8000 },
      );

      const timeoutId = setTimeout(() => {
        if (best) finish(best, null);
        else finish(null, new Error('Location timeout'));
      }, 13000);
    });
  } catch (_) {
    return getCurrentPosition({ enableHighAccuracy: true, timeout: 10000, maximumAge: 15000 });
  }
}

// Gets the user's GPS location, flies the camera there, and shows their local weather.
// Only prompts for permission if user clicked the locate button (userInitiated=true).
async function locateAndShowUserWeather({ force = false, animate = true, userInitiated = false } = {}) {
  try {
    const permissionState = await geolocationPermissionState();
    if (!userInitiated && permissionState !== 'granted') {
      return;
    }
    if (permissionState === 'denied') {
      flashHint(t('locationBlocked'), 5200);
      return;
    }

    flashHint(t('locating'));
    const pos = await getBestCurrentPosition();
    const lat = pos.coords.latitude;
    const lon = pos.coords.longitude;
    const acc = Number.isFinite(pos.coords.accuracy) ? Math.round(pos.coords.accuracy) : null;
    userLocation = { lat, lon, acc };

    if (animate) {
      stopRotation();
      focusOn(lat, lon, 200000);
    }

    panelLoading();
    const data = await fetchPointWeather(lat, lon, force);
    showPanel(data, { target: { lat, lon, source: 'user' }, force });
    setText('loc-country', `${data?.sys?.country || ''} | ${t('yourLocation')}${acc != null ? ` | GPS +/- ${acc} m` : ''}`);
    flashHint(t('liveUpdated'));
  } catch (err) {
    flashHint(t('locationUnavail'), 4200);
  }
}

// --- UI controls ---
// Connects all buttons (zoom, home, locate, refresh, close, unit toggle) and keyboard shortcuts
function initControls() {
  const zoomInBtn = document.getElementById('btn-zoom-in');
  const zoomOutBtn = document.getElementById('btn-zoom-out');
  const homeBtn = document.getElementById('btn-home');
  const locateBtn = document.getElementById('btn-locate');
  const refreshBtn = document.getElementById('btn-refresh');
  const closePanelBtn = document.getElementById('close-panel');
  const unitToggleBtn = document.getElementById('unit-toggle');

  if (zoomInBtn) zoomInBtn.addEventListener('click', () => {
    stopRotation();
    zoomIn();
  });

  if (zoomOutBtn) zoomOutBtn.addEventListener('click', () => {
    stopRotation();
    zoomOut();
  });

  if (homeBtn) homeBtn.addEventListener('click', () => {
    stopRotation();
    focusOn(HOME_VIEW.lat, HOME_VIEW.lon, HOME_VIEW.range);
    hidePanel();
  });

  if (locateBtn) locateBtn.addEventListener('click', async () => {
    await locateAndShowUserWeather({ force: true, animate: true, userInitiated: true });
  });

  if (refreshBtn) refreshBtn.addEventListener('click', async () => {
    if (refreshInFlight) return;
    refreshInFlight = true;
    const btn = refreshBtn;
    btn.classList.add('busy');
    btn.disabled = true;
    flashHint(t('refreshing'));

    try {
      if (activeTarget?.lat != null && activeTarget?.lon != null) {
        const d = await fetchPointWeather(activeTarget.lat, activeTarget.lon, true);
        showPanel(d, { target: activeTarget, force: true });
      } else if (userLocation) {
        await locateAndShowUserWeather({ force: true, animate: false });
      }
      await loadCityMarkers(true);
    } catch (err) {
      flashHint(`${t('refreshFailed')}: ${err.message}`, 4200);
    } finally {
      refreshInFlight = false;
      btn.classList.remove('busy');
      btn.disabled = false;
    }
  });

  if (closePanelBtn) closePanelBtn.addEventListener('click', hidePanel);

  if (unitToggleBtn) unitToggleBtn.addEventListener('click', () => {
    useFahrenheit = !useFahrenheit;
    unitToggleBtn.textContent = useFahrenheit ? '°F' : '°C';
    if (activeMarkerData) showPanel(activeMarkerData, { target: activeTarget });
    else renderCityMarkers(cityWeatherCache);
  });

  // Language toggle: switch between EN and FR
  const langBtn = document.getElementById('lang-toggle');
  if (langBtn) {
    langBtn.textContent = lang.toUpperCase();
    langBtn.addEventListener('click', () => {
      lang = lang === 'en' ? 'fr' : 'en';
      langBtn.textContent = lang.toUpperCase();
      applyI18n();
      // Re-render weather panel and city markers with new language
      if (activeMarkerData) showPanel(activeMarkerData, { target: activeTarget });
      renderCityMarkers(cityWeatherCache);
    });
  }

  window.addEventListener('keydown', e => {
    const tag = (e.target && e.target.tagName) ? e.target.tagName.toLowerCase() : '';
    if (tag === 'input' || tag === 'textarea' || e.target?.isContentEditable) return;
    if (e.key === '+' || e.key === '=') zoomIn();
    else if (e.key === '-' || e.key === '_') zoomOut();
    else if (e.key === '0') focusOn(HOME_VIEW.lat, HOME_VIEW.lon, HOME_VIEW.range);
    else if (e.key === 'ArrowLeft' || e.key === 'ArrowRight' || e.key === 'ArrowUp' || e.key === 'ArrowDown') {
      if (!map) return;
      e.preventDefault();
      stopRotation();
      const zoom = map.getZoom() ?? 2;
      // Arrow-key pan step shrinks as we zoom in: 20° at z=2, halves per zoom level (floor 0.05°).
      const step = Math.max(0.05, 20 / (2 ** Math.max(0, zoom - 2)));
      const center = map.getCenter?.();
      if (!center) return;
      let lat = center.lat();
      let lon = center.lng();
      if      (e.key === 'ArrowLeft')  lon -= step;
      else if (e.key === 'ArrowRight') lon += step;
      else if (e.key === 'ArrowUp')    lat = Math.min(85, lat + step);
      else if (e.key === 'ArrowDown')  lat = Math.max(-85, lat - step);
      if (lon < -180) lon += 360;
      if (lon > 180) lon -= 360;
      map.panTo({ lat, lng: lon });
    }
  });
}

// --- App entry point ---
// Loads CesiumJS, initializes the globe, sets up UI, loads city weather, tries geolocation
async function main() {
  const loading = document.getElementById('loading-screen');
  const loaded = await ensureCesiumLoaded();
  if (!loaded || !window.Cesium?.Viewer) {
    if (loading) loading.classList.add('hidden');
    flashHint(t('cesiumFail'), 7000);
    return;
  }

  applyI18n();
  // initMap throws if WebGL initialization fails (browser ran out of contexts,
  // GPU crashed, etc.). Catch it so the page degrades gracefully with a hint
  // instead of a stack trace, and do NOT auto-reload — that would loop forever.
  try {
    initMap();
    // Successful boot — clear any stale reload guard from a previous crash.
    sessionStorage.removeItem('mg_webgl_reloaded');
  } catch (err) {
    if (loading) loading.classList.add('hidden');
    flashHint('WebGL initialization failed. Close other tabs, enable hardware acceleration in your browser, and reload.', 15000);
    console.error('initMap failed:', err);
    return;
  }
  initSearch();
  initControls();
  flashHint(t('clickHint'), 5000);

  if (loading) loading.classList.add('hidden');

  loadCityMarkers();
  // Then try geolocation to override with user's actual location
  locateAndShowUserWeather({ force: false, animate: true, userInitiated: false });
}

// --- Screensaver ---
// After 60s of inactivity: hides UI, zooms in, spins the globe slowly with a clock overlay.
// Any user interaction (mouse, keyboard, touch) dismisses it and restores the UI.
function initScreensaver() {
  const ss = document.getElementById('screensaver');
  const clock = document.getElementById('ss-clock');
  if (!ss || !clock) return;

  let idleTimer = null;
  let spinDelayTimer = null;
  let screensaverStartedRotation = false;
  let preScreensaverView = null; // Camera state captured when entering, restored on dismiss
  const IDLE_MS = 20_000;        // 20 s — short enough that idle behavior is obvious

  function updateClock() {
    const now = new Date();
    clock.textContent = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`;
  }

  function showScreensaver() {
    updateClock();
    ss.classList.add('active');
    // Hide UI elements for clean screensaver look
    document.querySelector('.topbar')?.classList.add('ss-hidden');
    document.querySelector('.controls')?.classList.add('ss-hidden');
    document.getElementById('hint')?.classList.add('ss-hidden');
    document.getElementById('map-attrib')?.classList.add('ss-hidden');
    document.getElementById('weather-panel').classList.remove('active');
    clearActiveMarkers();
    activeMarkerData = null;
    activeTarget = null;
    // Snapshot the user's view BEFORE we move the camera, so dismiss can restore it.
    if (map?.viewer) {
      const c = getCameraCenter(map.viewer);
      preScreensaverView = {
        lat: c.lat,
        lon: c.lon,
        range: getCameraRange(map.viewer),
      };
    }
    // Switch to compact pill mode and move the camera to the cinematic view first,
    // THEN render markers and run the visibility pass — this way collision/backside
    // culling is computed against the screensaver's camera, not whatever the user
    // was looking at before. Compact pills + showing tier 1+2 give the dense,
    // weather-everywhere look without overwhelming the Raspberry Pi GPU.
    // NOTE: deliberately not touching resolutionScale here — toggling it forces
    // Cesium to reallocate framebuffers, which can trigger WebGL context loss
    // on the Pi GPU.
    screensaverActive = true;
    focusOn(HOME_VIEW.lat, HOME_VIEW.lon, HOME_VIEW.range * 0.65);
    renderCityMarkers(cityWeatherCache);
    updateCityTierVisibility();
    if (rotateTimer) stopRotation();
    clearTimeout(spinDelayTimer);
    // Short delay so the camera/markers settle one frame before the spin starts.
    spinDelayTimer = setTimeout(() => {
      if (!ss.classList.contains('active')) return;
      startRotation();
      screensaverStartedRotation = true;
    }, 150);
  }

  function dismissScreensaver() {
    ss.classList.remove('active');
    // Restore UI elements
    document.querySelector('.topbar')?.classList.remove('ss-hidden');
    document.querySelector('.controls')?.classList.remove('ss-hidden');
    document.getElementById('hint')?.classList.remove('ss-hidden');
    document.getElementById('map-attrib')?.classList.remove('ss-hidden');
    clearTimeout(spinDelayTimer);
    if (screensaverStartedRotation) {
      stopRotation();
      screensaverStartedRotation = false;
    }
    // Switch back to full pills and re-render so city names return immediately,
    // then fly back to the view the user had before the screensaver took over.
    // Falls back to HOME_VIEW if we never captured one.
    screensaverActive = false;
    renderCityMarkers(cityWeatherCache);
    const target = preScreensaverView ?? HOME_VIEW;
    flyToLocation(target.lat, target.lon, target.range, 1.2);
    preScreensaverView = null;
    // Recompute marker visibility after the flight settles
    setTimeout(updateCityTierVisibility, 1300);
    resetIdle();
  }

  function resetIdle() {
    clearTimeout(idleTimer);
    idleTimer = setTimeout(showScreensaver, IDLE_MS);
  }

  setInterval(updateClock, 1000);

  ['mousemove', 'mousedown', 'keydown', 'touchstart', 'wheel'].forEach(evt => {
    window.addEventListener(evt, () => {
      if (ss.classList.contains('active')) dismissScreensaver();
      else resetIdle();
    }, { passive: true });
  });

  resetIdle();
}

document.addEventListener('DOMContentLoaded', main);
document.addEventListener('DOMContentLoaded', initScreensaver);
