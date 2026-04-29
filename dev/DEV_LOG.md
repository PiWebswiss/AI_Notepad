# Dev Log

Current live setup: https://meteoglobe.piweb.ch/

### Icon and text rendering fixes

I fixed blurry icons and text across the app:

- **Hero and forecast icons now render as inline SVG** instead of `<img>` tags. Browsers rasterize SVGs inside `<img>` at their intrinsic size (40x40 in our case), causing blur when scaled up. Using `fetch()` + `innerHTML` injects the SVG directly into the DOM so it renders crisply at any CSS size.
- **Server icon endpoint simplified to SVG-only.** Removed PNG fallback from `/api/icon/{code}` since all icons are now SVGs. This avoids stale PNG data in the in-memory `_icon_cache`.
- **Canvas marker resolution increased.** Globe marker canvases now render at `1.5× devicePixelRatio` (minimum 3x) instead of hardcoded 2x, and billboard scale uses `1/S` to match. This produces sharper temperature text in Cesium's WebGL pipeline.
- **CSS text rendering improved.** Added `-moz-osx-font-smoothing: grayscale`, `text-rendering: optimizeLegibility` globally, `shape-rendering: geometricPrecision` on all SVG icons, and `image-rendering: -webkit-optimize-contrast` on the temperature chart canvas.
- **CSS updated for inline SVGs.** All selectors targeting `img` in `.hero-icon-wrap`, `.fc-icon`, and `.marker-bubble` now also target `svg` so inline icons get correct dimensions at all responsive breakpoints.
- **Cache busters bumped** to `?v=svg-icons-1` on both `app.js` and `style.css` to force browsers to load the updated files.

I removed weather animations entirely. Deleted `weather-fx.js` and `local-weather-3d.js`, removed the `<canvas id="weather-canvas">` from HTML, and cleaned all `weatherFX`, `ambientWeatherCode`, `ambientWeatherDay`, `initWeatherFX()`, `syncWeatherVisuals()` references from `app.js`. Removed related CSS (`#weather-canvas`) and all animation mentions from the DEV_LOG.

I removed dead code: unused `normalizeSearchText()` function, unused `toggleRotation()` function, orphan `btn-rotate` DOM reference in `stopRotation()`, unused `import math` in `server.py`, and dead `.station-marker` CSS classes from the old MeteoSwiss integration.

I added comprehensive code comments throughout `app.js` — every function and section now has a comment explaining what it does.

I replaced the H/W/P stats panel (Humidity, Wind, Pressure) with a MeteoSuisse-style temperature and precipitation chart. The chart canvas shows today's data with a red temperature curve (Bezier-smoothed), blue precipitation bars, a "now" marker, temperature labels on the left Y-axis, rain mm values above bars, and hour labels at the bottom. Backend updated to return hourly `precipitation` data and use `timezone: auto` for correct local times.

I upgraded the forecast section from hourly 3h cards to a 7-day daily forecast. Backend now requests `daily` data from Open-Meteo (temp max/min, precipitation sum, weather code) with `forecast_days: 7`. Frontend shows day name, weather icon, max/min temperature, and daily rain total for each of the next 7 days.

I added French/English internationalization (i18n). All user-visible strings are stored in an `I18N` object with `en` and `fr` translations. A `t(key)` function returns the correct string for the current language. HTML elements use `data-i18n` and `data-i18n-placeholder` attributes for static text. A language toggle button (EN/FR) was added to the top-right bar. The default language is detected from the browser (`navigator.language`). Switching language updates all UI text, re-renders the weather panel and forecast.

I made the app fully responsive for all device sizes. Added CSS media queries for tablets (max 900px), phones (max 600px), small phones (max 380px), and large screens (min 1200px). On phones the weather panel slides from the bottom instead of the left and takes full width. The topbar compresses (logo text hidden, smaller search bar and buttons). Forecast cells, chart, and hero section scale down proportionally. Added touch-friendly minimum tap targets (44px) via `pointer: coarse` query. Added landscape phone support (max-height 500px) with reduced panel height. The weather panel is now scrollable on all screen sizes to handle small viewports.

I fixed marker icon misalignment. The weather icon was a separate Cesium billboard positioned at the same lat/lon with a pixel offset, which caused the icon to drift away from the tooltip when the camera tilted or rotated. Fix: the icon is now drawn directly into the marker canvas using `loadIconImage()` + `ctx.drawImage()`. Both city pills and active tooltips are now single billboards containing background, icon, and text in one canvas. Removed the unused `resolveWeatherIconSource()` function. The active marker tooltip was widened to 130px to fit icon + city name + temperature side by side.

I replaced all 84 weather icons with the official MeteoSwiss SVG icons downloaded from `https://www.meteoschweiz.admin.ch/static/resources/weather-symbols/{code}.svg`. The old 40x40 PNGs were blurry when upscaled. The official SVGs are vector graphics that scale perfectly at any size. Deleted all PNG files, kept only SVGs. Hero icon restored to 88px. The server already checks `.svg` before `.png`, so the new icons are served automatically via `/api/icon/{code}`.

I simplified the weather backend to use a single data source. Removed OpenWeatherMap and MeteoSwiss API integrations entirely — the app now uses only Open-Meteo for all weather data (current conditions + forecasts) and Nominatim for geocoding. This eliminates the need for any API key.

Changes:
- `server.py`: removed `OWM_KEY`, `CH_BOUNDS`, `in_switzerland()`, MeteoSwiss endpoints (`/api/meteoswiss/stations`, `/api/meteoswiss/forecast`, `/api/meteoswiss/point`), and all OWM fallback branches in `/api/weather`, `/api/forecast`, and `/api/geocode`.
- `public/app.js`: removed `CH_BOUNDS`, `isOverSwitzerland()`, `buildMSForecastList()`, `meteoCodeToOwm()`, and updated forecast source label to always show "Open-Meteo".
- `docker-compose.yml`: removed `OWM_API_KEY` environment variable.
- `README.md`: updated to reflect Open-Meteo as sole weather source, removed OWM key references.
- Local weather icons (`public/icons/`) are still used for all display.

I updated the project for the exam version and cleaned the interaction flow.

I fully updated the report file `rapport_station_meteo_eink_v3.docx` so it now matches the new MeteoGlobe 3D project instead of the old e-ink base. The report now follows the `laboratoire - CFC28.pdf` structure and explains clearly which APIs are used, how data is extracted and normalized, how caching is handled, how security is done, and how testing was performed.

I also updated `public/app.js` for usability. Weather selection is now left click only, and right click is no longer used for weather interaction. I kept the idle visual behavior you asked for by improving the screensaver mode so that after inactivity the globe rotates automatically, and when the user interacts again the screensaver closes and that automatic idle rotation stops.

I ran a JavaScript syntax check after the changes with `node --check public/app.js` and the check passed.

After user feedback, I applied a correction pass.

Right click on the globe is now explicitly blocked again (`contextmenu` disabled) and weather pick is forced to left click only (`ev.button === 0`) so right click cannot open weather anymore.

I also reduced idle timeout from 90 seconds to 20 seconds so the idle behavior is clearly visible in normal use. When idle starts, the globe auto-rotates; when user activity returns, the screensaver exits and idle-started rotation is stopped.

I fixed city weather markers by adding a backend fallback in `server.py` for `/api/cities`: if OpenWeatherMap fails or the API key is missing, the service now fetches current conditions from Open-Meteo and maps them to the frontend schema. This keeps city markers and weather visible instead of returning an empty list.

I also added a frontend resilience guard in `loadCityMarkers()`: if a city refresh returns an empty list, the app keeps existing marker cache instead of clearing the globe, and it shows a hint message when city weather cannot be loaded.

I bumped the frontend script version in `public/index.html` (`app.js?v=nasa3d4`) so browsers load the latest JavaScript immediately and do not keep stale interaction behavior from cache.

I made `OWM_API_KEY` optional by adding an Open-Meteo fallback for `/api/weather` in `server.py`. With this change, current weather, forecast, and city markers can still work without OpenWeatherMap credentials (OWM remains recommended as primary provider when a key is available).

I hardened fallback quality after more bug reports. `/api/weather` now adds best-effort reverse geocoding (Nominatim) so the weather panel can still show a readable city/country without OWM. I also rate-limited concurrent `/api/cities` upstream calls with an async semaphore to reduce burst failures that could hide all city markers.

I bumped frontend cache-busting again to `app.js?v=nasa3d5` in `public/index.html` so the newest click/marker fixes are loaded without stale browser JS.

I tightened idle Earth rotation again: idle delay is now 10 seconds and screensaver start forces a fresh globe rotation every time (stop old timer, then start rotation). I also bumped cache-busting to `app.js?v=nasa3d6`.

I hardened right-click blocking again after repeated reports. Weather picking now uses left-button `mouseup` only, ignores Ctrl/Cmd click variants, and blocks `contextmenu` + `auxclick` propagation on the globe canvas. Cache-busting bumped to `app.js?v=nasa3d7`.

I changed Earth rotation direction to the opposite way (negative heading step) so idle spin matches user preference. I also made `/api/cities` fully resilient: when upstream providers fail, backend now returns deterministic fallback city weather entries instead of empty results, so city labels and weather markers remain visible. Cache-busting bumped to `app.js?v=nasa3d8`.

I patched a WorldWind render-loop crash (`GpuResourceCache.putResource` from placemark label textures). City and active marker labels are now sanitized to ASCII-safe text with finite temperature values, and custom label font overrides were removed to avoid invalid text texture creation. Cache-busting bumped to `app.js?v=nasa3d9`.

I applied a strict stability fallback: placemark text labels are now fully disabled in the 3D layer to eliminate WorldWind text-texture crashes (`GpuResourceCache.putResource`). Weather markers/icons and panel weather data remain active. Cache-busting bumped to `app.js?v=nasa3d10`.

I implemented round marker bubbles with city names directly inside marker SVG images (no WorldWind text-label path), so city name + temperature stay visible while avoiding the texture crash loop. I also hardened right-click blocking with anti-ghost-click suppression on the globe canvas (`mousedown/contextmenu/auxclick` suppression + guarded left-button `mouseup` pick). Cache-busting bumped to `app.js?v=nasa3d11`.

I switched round marker bubbles to MeteoSwiss icons by embedding `/api/icon/{code}` in the marker SVG composition, while keeping city name + temperature text in the bubble. Cache-busting bumped to `app.js?v=nasa3d12`.

I refreshed the screensaver behavior and look. Idle mode now returns to Earth view, hides the panel, then starts globe rotation with a slower speed profile (`ROTATION_STEP_DEG=0.08`, `ROTATION_TICK_MS=45`) and a short delayed start for smoother motion. Idle timeout is now 15 seconds. I also modernized the screensaver UI with a glass card layout and bumped cache-busting to `app.js?v=nasa3d13`.

I applied a final interaction hardening pass: removed built-in `CompassLayer` and `ViewControlsLayer` to reduce WorldWind render noise/crash risk, and added global capture-phase right-click suppression (`contextmenu` + non-primary `auxclick`) so right-click cannot trigger weather even with browser/device quirks. Cache-busting bumped to `app.js?v=nasa3d14`.

I added a stricter mouse pick gate: weather fetch now requires a valid left-button down+up sequence on canvas (with drag cancellation and suppression windows), so right-click/aux-click/cmd-click cannot enter the weather pick path. I also made active screensaver non-blocking for UI controls (`pointer-events: none`) and disabled cache for HTML/JS/CSS responses in `server.py` to prevent stale frontend code from persisting between Docker restarts. Cache-busting bumped to `app.js?v=nasa3d15`.

I fixed the city marker regression and icon mismatch. City marker render now defines `iconCode` correctly and composes each marker as two placemarks: a round name/temperature bubble plus a dedicated MeteoSwiss icon placemark (`/api/icon/{code}`), ensuring actual MeteoSwiss pictograms are displayed. I also removed incompatible controls from the UI (`btn-map`, `btn-night`) and made control binding null-safe. Cache-busting bumped to `app.js?v=nasa3d17`.

I removed emoji fallbacks from the visible UI flow. Country display and search badges now use plain text (no flag emoji), weather icon fallbacks use `N/A` or `--`, and icon-endpoint fallback SVG no longer draws emoji glyphs. Cache-busting bumped to `app.js?v=nasa3d19`.

I enforced city-name placement under markers: each city marker now includes a dedicated name-strip placemark rendered below the round weather bubble, and the active selected marker gets the same under-label treatment. Cache-busting bumped to `app.js?v=nasa3d20`.

I slowed screensaver activation to 60 seconds idle (from 15 seconds) for normal day-to-day use, and bumped cache-busting to app.js?v=nasa3d21.

I fixed the marker stacking bug visible on selected cities (example: Lagos). The city base marker is now temporarily hidden when the same location is selected as the active marker, so we no longer render two markers on top of each other.

I corrected marker layout offsets in `public/app.js` so the weather icon is anchored inside the round bubble and the city name strip stays under the bubble for both city markers and active markers.

I fixed icon fallback behavior in the frontend by mapping fallback rendering to the weather condition code (OWM code), not the MeteoSwiss pictogram id. This prevents wrong or blank fallback visuals.

I upgraded backend icon fallback in `server.py` (`/api/icon/{code}`): when MeteoSwiss icon fetch fails, it now returns weather-style SVG symbols (sun/cloud/rain/snow/thunder/fog) instead of the generic placeholder.

I bumped frontend cache-busting to `app.js?v=nasa3d22` in `public/index.html` to force browsers to load the latest marker/icon fixes.

I expanded the global `CITIES` list in `public/app.js` to include many more major cities across North America, South America, Europe, Africa, Middle East, Asia, and Oceania, so the globe displays broader worldwide coverage instead of only a small subset.

I replaced `download_icons.py` so it now downloads only official MeteoSwiss icons for all 84 expected codes (1-42 and 101-142) and exits with an error if any icon is missing. There is no generated icon fallback anymore.

I also changed `server.py` icon serving to strict local-only behavior for `/api/icon/{code}`: only supported MeteoSwiss codes are accepted, icons are served from `public/icons` (SVG first, then PNG), and missing files return HTTP 404 instead of any synthetic fallback or remote runtime fetch.

I updated the Docker build note in `Dockerfile` to reflect strict official icon download at build time.

I replaced icon sourcing again to guarantee real local MeteoSwiss assets without runtime fetch. `download_icons.py` now downloads MeteoSwiss' official weather-symbol workbook (XLSX) and extracts the embedded official icon images by row/code mapping into `public/icons/{code}.png` for all 84 codes (1-42 and 101-142). No synthetic fallback is used.

I verified local icon inventory after extraction: 84 PNG files, 0 SVG files. `/api/icon/{code}` serves these local files only (no CDN runtime fallback).

After confirming icons are now vendored locally, I removed `download_icons.py` from the project and updated `Dockerfile` to stop copying/running it during image build. The build now uses the committed `public/icons` directory directly.

I fixed city-marker layout and icon sharpness issues reported on map view. Marker labels are now rendered inside the same SVG bubble asset (instead of a separate placemark), which prevents name-strip drift. I also reintroduced dedicated weather icon placemarks sourced from local `/api/icon/{code}` files with reduced scale to avoid blurry upscaling. Cache-busting bumped to `app.js?v=nasa3d23`.

I moved all weather icons to local files to eliminate the external CDN dependency entirely.

All MeteoSwiss CDN URL patterns tried previously now return 404 (the URLs have changed or been removed). Instead of relying on external icon fetching, I created `download_icons.py` — a standalone script that generates all 84 weather icons (codes 1–42 day, 101–142 night) as SVG files into `public/icons/`. The icons use a consistent dark-theme style (`#0d1b33` background, rounded corners) with proper SVG shapes for each weather condition (sun/moon/cloud/rain/snow/thunder/fog and combinations). The `Dockerfile` now runs `python download_icons.py` at build time so icons are always present in the image. In `server.py`, the `/api/icon/{code}` endpoint now checks `public/icons/{code}.svg` (then `.png`) before attempting any network fetch — at runtime, icons are served from disk with zero external requests.

I fixed three performance and visual issues reported after the second test.

First, city marker rendering was rebuilding (destroy + recreate) all WorldWind placemarks on every zoom tier change, flushing the GPU texture cache each time. Fixed by storing placemark references in `cityPlacemarkMap` (Map&lt;name, {pm, pmName, tier}&gt;) and adding `updateCityTierVisibility()` which only flips `pm.enabled / pmName.enabled` — no GPU texture reload. `renderCityMarkers` still does a full rebuild when weather data changes or active target changes.

Second, the mouse-wheel handler was calling `wwd.redraw()` synchronously on every wheel tick (potentially hundreds per second). Fixed with RAF throttling: all ticks within one animation frame are coalesced into a single `wwd.redraw()` + `updateCityTierVisibility()` call, capping redraw rate at ~60 fps.

Third, `fallback_icon_svg()` in `server.py` was generating SVGs with no background (transparent), making the weather shapes invisible or hard to read on dark UI. Added a dark rounded-rectangle background (`#0d1b33`, rx=14) as the first element of every fallback SVG. Also added the MeteoSwiss app production icon URL (`app-prod-ws.meteoswiss-app.ch/v1/productimage/weathericon/meteo/large/{c}.png`) as the first candidate in `ICON_URLS` so actual MeteoSwiss pictograms are tried before the CDN fallback paths.

I fixed two root-cause bugs in city marker rendering. First, the separate icon placemark used a wrong `imageOffset` (Y=-0.38) that placed the weather icon ~20px above the geographic anchor instead of ~49px where the circle center actually sits, so the icon was appearing inside the temperature badge area or behind it. Second, because the bubble placemark was added to the layer before the icon placemark, the opaque badge rectangle covered the icon in WorldWind's render order. Fix: removed the separate icon placemark entirely and embedded the weather emoji directly inside the bubble SVG at the correct circle-center coordinates. City markers now use two placemarks each (bubble+emoji, name strip) instead of three.

I fixed the overlapping city labels and icons by implementing zoom-based progressive city disclosure. Each city in `CITIES` now carries a tier value (`t: 1/2/3`). A `getMaxCityTier(range)` function maps the current camera range to a maximum tier, and `renderCityMarkers` skips cities above that tier. At global view (range > 5 000 km) only ~22 megacities are shown; at continental zoom (1 500–5 000 km) ~62 major cities appear; at country/city zoom (< 1 500 km) all 93 cities are visible. The wheel event handler detects tier-boundary crossings and schedules a debounced re-render (150 ms) so markers update smoothly as the user zooms in or out.

I removed remaining browser console outputs from public/app.js (Google Maps load catch, MeteoSwiss point fallback, search fallback, and city marker refresh fallback) to keep production console clean while preserving silent fallback behavior.

I added explicit configuration comments in docker-compose.yml (including GOOGLE_MAPS_API_KEY and GOOGLE_MAPS_MAP_ID), added public runtime config endpoint /api/config in server.py, and documented the Google Maps setup in README.md. I also added concise inline comments in public/app.js around Google config loading and city-tier visibility logic.

I fixed a runtime crash in public/app.js where main() still called the removed ensureWorldWindLoaded() function after migrating to Google Maps. main() now calls ensureGoogleMapsLoaded() and validates window.google.maps, with an updated error hint for GOOGLE_MAPS_API_KEY. I also replaced leftover keyboard navigation code that referenced wwd.navigator with Google Maps center panning logic for arrow keys, updated the map attribution text in index.html, and bumped frontend cache-busting to app.js?v=nasa3d24.

I removed remaining legacy frontend runtime leftovers from the old WorldWind migration path. In public/app.js, hidePanel() no longer references markerLayer (it now calls clearActiveMarkers()), and legacy function names were renamed to map-native names (onMapPick/initMap) so no old WorldWind code path remains in active runtime. I also removed the unused #wwd-canvas CSS block from public/style.css and bumped frontend cache-busting to app.js?v=nasa3d25.

I aligned Google Maps integration with current official recommendations. In public/app.js, the JS API loader now uses loading=async and imports the marker library via google.maps.importLibrary('marker'). City/active markers were migrated from deprecated google.maps.Marker to google.maps.marker.AdvancedMarkerElement wrappers, and map init now sets a map id (GOOGLE_MAPS_MAP_ID or DEMO_MAP_ID) for advanced marker compatibility. I also updated geolocation flow to avoid automatic permission prompts unless permission is already granted, which prevents repeated browser-blocked geolocation warnings; manual locate still works from the locate button. Cache-busting bumped to app.js?v=nasa3d26.

I fixed two regressions after the official Google migration pass. First, map startup no longer hard-fails when advanced marker library/mapId is unavailable: the app now falls back to classic google.maps.Marker so the map still renders. Second, I restored public/index.html to clean UTF-8/ASCII UI strings and logo/loader text (removing mojibake text like �...), and bumped cache-busting to app.js?v=nasa3d27.

I removed the remaining deprecated Google marker path in `public/app.js` to stop the `google.maps.Marker is deprecated` console warning. `createImageMarker()` now uses `google.maps.marker.AdvancedMarkerElement` only (with a safe no-op object if the library is unavailable), and `initMap()` now always sets a map ID (`GOOGLE_MAPS_MAP_ID` when configured, otherwise `DEMO_MAP_ID`) so advanced markers stay enabled. I also bumped frontend cache-busting to `app.js?v=nasa3d28` in `public/index.html`.

Follow-up update: I explicitly recorded the Google Maps deprecation fix in this log after final verification. The frontend no longer uses `google.maps.Marker`; marker rendering now relies on `google.maps.marker.AdvancedMarkerElement`, map init enforces a map id (`GOOGLE_MAPS_MAP_ID` or `DEMO_MAP_ID`), and cache-busting is set to `app.js?v=nasa3d28`.

I investigated a blank-map runtime case where UI controls loaded but map tiles were not visible. In `public/app.js`, I added Google auth diagnostics (`window.gm_authFailure`) with explicit on-screen guidance, plus a map initialization watchdog that retries progressively simpler map modes (hybrid+mapId -> roadmap+mapId -> hybrid -> roadmap). If tiles still do not load, the app now shows a clear persistent hint to check `GOOGLE_MAPS_API_KEY` localhost referrer and billing instead of silently staying on an empty background.
I also bumped frontend cache-busting to `app.js?v=nasa3d29` in `public/index.html` so this diagnostics/fallback patch is loaded immediately.

I migrated the frontend globe engine from Google Maps to CesiumJS so the app can render a true 3D Earth without Google API key restrictions. In `public/app.js`, I replaced the Google loader with a Cesium loader (`unpkg` script + widgets CSS), introduced a Cesium map adapter (click picking, zoom/pan, heading/tilt, drag/zoom events), and switched marker rendering from AdvancedMarkerElement to Cesium billboard entities while keeping existing weather marker logic, city-tier visibility, controls, search, and panel behavior. I also updated default attribution text to CesiumJS/OpenStreetMap and bumped frontend cache-busting to `app.js?v=nasa3d30` in `public/index.html`.


I fixed the persistent blue planet issue. The root cause was that `createNaturalEarthFallbackProvider` used `UrlTemplateImageryProvider` with `GeographicTilingScheme` and `maximumLevel: 5`, which did not match the actual NaturalEarthII TMS tile layout (only levels 0-2 with its own metadata). This caused silent tile-load failures, leaving the globe showing Cesium's default blue base color. Fix: replaced with `TileMapServiceImageryProvider.fromUrl()` which reads the `tilemapresource.xml` descriptor for correct tiling, set `globe.baseColor` to dark (`#0a1628`) so even during async imagery load the globe never appears blue, added the viewer with `baseLayer: false` to avoid any default imagery, and added a fallback to public OpenStreetMap tiles if NaturalEarthII is unavailable from the CDN.

I also fixed the temperature labels on globe markers. `tempBadgeText()` was rendering "+23C" without a degree symbol, while the panel's `displayTemp()` correctly showed "23°C". Added the Unicode degree sign (`\u00B0`) to marker SVG temperature badges so they now show "+23°C" consistently. Cache-busting bumped to `app.js?v=nasa3d37`.

I replaced the globe imagery with Esri ArcGIS World Imagery (free satellite tiles) to give a Google Earth-like appearance. The `addBaseImageryLayer()` function now tries providers in order: (1) Esri World Imagery satellite, (2) Cesium NaturalEarthII via TMS, (3) public OpenStreetMap tiles. The globe base color remains dark `#0a1628` to prevent any blue flash during async imagery loading. Attribution updated to reflect Esri imagery. Cache-busting bumped to `app.js?v=nasa3d38`.


I redesigned city markers to Google Maps-style labels. City markers are now clean white text with a colored dot and temperature below (no dark bubbles or pill shapes). Active/selected markers use a compact glass card with city name and temperature. Weather icons are positioned next to the label. The old `buildRoundMarkerDataUrl` and `buildNameStripDataUrl` functions were replaced by `buildCityLabelDataUrl` and `buildActiveMarkerDataUrl`.

I hid the Cesium Ion credit logo and attribution text via CSS (`.cesium-widget-credits`, `.cesium-credit-logoContainer`, `.cesium-credit-textContainer` set to `display: none`).

I fixed city marker rendering issues. Removed SVG `feDropShadow` filters from marker data URLs (unsupported in Cesium WebGL texture pipeline, caused blank markers). Replaced with `paint-order: stroke` text outlines for legibility. Fixed `eyeOffset` Z sign in `createImageMarker` (was positive, pushing markers behind the globe; now negative to bring them forward). Simplified marker anchor offsets for correct positioning. Weather icons now appear below the city label text. Cache-busting bumped to `app.js?v=nasa3d40`.

I added Esri World Boundaries and Places as a transparent label overlay on top of satellite imagery. This provides Google Maps-style city, village, road, and boundary labels natively on the map, replacing the need for hardcoded city name labels. City weather markers are now compact temperature pills (just temp + weather icon) since the Esri overlay handles place names.

I fixed cities from the other side of the globe showing through the Earth (e.g. Auckland/Sydney visible over Switzerland). Root cause: `disableDepthTestDistance: Number.POSITIVE_INFINITY` disabled depth testing, so all billboards rendered regardless of occlusion. Fix: set `disableDepthTestDistance: 0` so Cesium's depth test hides markers behind the globe surface.

Added code comments to new marker functions and key rendering logic. Cache-busting bumped to `app.js?v=nasa3d41`.

I redesigned city weather markers to a modern frosted glass pill style: dark translucent rounded pill with a subtle white border, a colored temperature-accent dot on the left, and the weather icon floating above the pill. Active/selected markers use a sleek glass card with city name, bold colored temperature, and a colored accent bar at the bottom. Cache-busting bumped to `app.js?v=nasa3d42`.

I made the city weather icons larger (36x36, up from 22x22) and repositioned them higher above the temperature pill for better visibility. Cache-busting bumped to `app.js?v=nasa3d43`.

I fixed the forecast panel being stuck on "Loading..." for Swiss locations. Root cause: MeteoSwiss API returned `currentWeather` with all null values, which was truthy in JS, so the frontend skipped the OWM fallback and built an empty forecast list. Fix: added null checks for `currentWeather.time` and `forecast3h/forecast1h` array lengths before using MeteoSwiss data. Cache-busting bumped to `app.js?v=nasa3d44`.

I removed MeteoSwiss integration entirely from the frontend. Removed `fetchSwissPointWeather()`, the MeteoSwiss forecast path in `loadForecast()`, and the MeteoSwiss source labels in `showPanel()`. Forecasts now use OpenWeatherMap directly with Open-Meteo as fallback. I also removed the rotate button (`btn-rotate`) from the UI and its `toggleRotation()` event listener (screensaver auto-rotation still works independently). Cache-busting bumped to `app.js?v=nasa3d45`.

I upgraded marker SVGs to 4x resolution for crisp text rendering in Cesium's WebGL texture pipeline. `buildCityLabelDataUrl` now renders at 384x136 displayed at 96x34 (4x), and `buildActiveMarkerDataUrl` renders at 480x184 displayed at 120x46 (4x). This eliminates pixelated temperature numbers on city pills and active tooltips. The active marker was also redesigned as a compact tooltip with city name on top and bold colored temperature below. Cache-busting bumped to `app.js?v=nasa3d46`.

I fixed the screensaver globe rotation. The previous rotation changed camera heading (rotated the view direction) which was barely visible. Replaced with `camera.rotate(Cartesian3.UNIT_Z, ...)` in the Cesium map adapter for smooth continuous globe spin without jumps. Increased rotation speed (`ROTATION_STEP_DEG=0.15`, `ROTATION_TICK_MS=30`) and zoomed out further during screensaver (`HOME_VIEW.range * 1.5`). UI elements (topbar, controls, hint, attribution) fade out during screensaver and city markers are hidden, keeping only the clock card visible for a clean cinematic look. Cache-busting bumped to `app.js?v=nasa3d47`.

I upgraded marker SVGs from 4x to 6x resolution for even crisper text in WebGL. City pills now render at 576x204 (displayed at 96x34) and active tooltips at 720x276 (displayed at 120x46). Removed Visibility, Sunrise, and Sunset stat items from the weather panel (HTML + JS) as they were not needed. Added Cloudflare Tunnel setup guide link to README.md. Cache-busting bumped to `app.js?v=nasa3d48`.

I repositioned weather icons to sit inside the marker pills at the same vertical level as the temperature text, instead of floating above. City pill icons are 22x22 centered on the left dot area, active tooltip icons are 22x22 positioned left of the temperature line. Also made pill backgrounds more opaque (0.92), text bolder (weight 800) with subtle dark stroke outlines for better contrast and readability. Cache-busting bumped to `app.js?v=nasa3d51`.

I replaced SVG data URL markers with Canvas-rendered textures to fix persistent pixelated text. SVG data URLs get rasterized at native size then resampled by Cesium's WebGL pipeline, causing blur. Canvas rendering uses the browser's native font rasterizer with proper sub-pixel anti-aliasing. The canvas is rendered at exactly 2x display size (192x68 for 96x34 pill, 240x92 for 120x46 tooltip) with `billboard.scale = 0.5`, so Cesium maps canvas pixels 1:1 to screen pixels without resampling. The previous approach of rendering at 4-6x with explicit `width`/`height` forced Cesium to resample the texture down, destroying text quality. Cache-busting bumped to `app.js?v=nasa3d54`.

I optimized and cleaned up `public/app.js`:
- Reduced screensaver zoom from `HOME_VIEW.range * 0.4` (too close) to `HOME_VIEW.range * 0.65` (~7.8M m) for a better compromise between showing weather markers and keeping a cinematic globe view.
- Simplified `fetchPointWeather` from a redundant wrapper function to a `const` alias of `fetchWeatherAt`.
- Simplified `normalizeLon()` from a while-loop approach to a single modulo expression.
- Net result: ~67 lines removed, no functional changes beyond the screensaver zoom adjustment.

### README install guide

Added a complete step-by-step install guide to `README.md` covering Docker installation on Raspberry Pi / Debian (GPG key, apt repo, package install, user group setup), git clone, and `docker compose up`. This replaces the previous single-line Docker link.

### Screensaver improvements

- Slowed globe rotation from 0.15°/tick to 0.04°/tick (~4x slower) for a more cinematic feel.
- City weather markers now stay visible during screensaver (previously hidden).
- Screensaver zoom adjusted to `HOME_VIEW.range * 0.4` for a closer globe view showing weather markers clearly.

### Reverse geocoding fix (Nominatim 429 rate-limiting)

Root cause of "Selected location" instead of city names: Nominatim was returning HTTP 429 (Too Many Requests). Fix:
- Added a Nominatim rate-limiter (`_nominatim_lock` + `_nominatim_last_call`) ensuring max 1 request per 1.1 seconds.
- Extracted `_extract_place_name()` helper so both fresh and cached Nominatim responses are parsed consistently (previously the cache-hit path only checked `data.name` instead of the full address hierarchy).
- Added `Accept-Language: en` header to all Nominatim requests so place names are always returned in English.
- Added logging for geocode failures.

### City weather performance fix

The `/api/cities` endpoint was calling `reverse_geocode_brief()` for every city (~90), each waiting 1.1s in the Nominatim rate-limiter queue. Fix: added `place_name_override` parameter to `weather_payload()` so the cities endpoint passes the known city name directly and skips Nominatim entirely. City weather now loads in seconds instead of minutes.

### Satellite tile disk caching

Added a new endpoint `/api/sat/{layer}/{z}/{x}/{y}` that proxies Esri World Imagery and World Boundaries tiles with persistent disk caching:
- First request fetches from Esri and saves the tile as a PNG file under `tile_cache/{layer}/{z}/{x}/{y}.png`.
- Subsequent requests serve the file directly from disk — same quality, zero external API calls.
- Frontend updated to route satellite and label imagery through this local proxy instead of calling Esri directly.
- Docker volume `sat-tiles` added to `docker-compose.yml` so the tile cache persists across container restarts.
- Max zoom capped at 17 to avoid excessive tile counts at very high zoom levels.

### Aggressive caching strategy

Increased cache TTLs across the entire stack to reduce API calls:

**Server-side (in-memory):**
- Current weather: 10 min → 15 min (weather doesn't change that fast)
- Forecast: 10 min → 30 min (forecasts change even slower)
- Reverse geocode (Nominatim): 24h → 30 days (place names don't move)
- Geocode search (Nominatim): 1h → 7 days (search results are stable)

**Browser-side (Cache-Control headers):**
- Satellite/label tiles: 7 days (new)
- Weather icons: 1 day → 30 days (icons never change)
- Static assets (images, fonts): 1h → 30 days
- HTML/JS/CSS: kept at no-store for development

### Server code documentation

Added comprehensive comments and docstrings to `server.py`:
- Module-level docstring explaining the server's role
- Section headers separating logical blocks (helpers, config, caches, external APIs, geocoding, weather assembly, FastAPI setup, routes)
- Docstrings on every function and API route
- Inline comments on configuration variables explaining their purpose

### Marker text crispness fix (HiDPI)

Fixed blurry temperature text on city pills and active tooltip markers on high-DPI screens. Root cause was not the marker canvas resolution — it was Cesium's viewer rendering at CSS pixel resolution by default, letting the browser upscale the WebGL output to device pixels (which softens everything on the globe, including our billboard textures). Fix in `initMap()`: set `viewer.useBrowserRecommendedResolution = false` and `viewer.resolutionScale = Math.min(window.devicePixelRatio || 1, 2)` so Cesium renders natively at device pixels (clamped to 2x to avoid GPU cost on 3x/4x retina). Marker canvases remain at the original 2x supersampling with `billboard.scale = 0.5` — that was already correct; the blur was upstream. Cache-busting bumped to `app.js?v=svg-icons-5`.

### On-demand rendering for battery / mobile

Enabled `viewer.scene.requestRenderMode = true` and `maximumRenderTimeChange = Infinity` in `initMap()` so Cesium only repaints when the scene actually changes (camera move, entity update, imagery load) instead of running a steady 60 fps loop. Big GPU and battery win on phones when the globe sits idle (panel open, reading forecast). Camera rotations (including screensaver spin) and marker updates both trigger re-renders automatically, so behavior is unchanged. Cache-busting bumped to `app.js?v=svg-icons-6`.

### Cities endpoint cleanup — remove dead latitude fallback

Removed the latitude-based temperature approximation in `/api/cities` ([server.py:438-450](server.py#L438-L450)). Open-Meteo has global grid coverage so the fallback only fired on network panics, and even then it was producing a fake reading rather than a visible error. Failed cities are now filtered out of the response; `renderCityMarkers` already skips entries without `weather`, so nothing breaks visually. If every city fails the result is an empty list, which the frontend handles via the existing `cityUnavail` hint + retry path. Net -17 lines, no behavior change under normal conditions, no more "fake" temperatures in the UI.

### Dead code sweep

- Removed unused `.globe-marker`, `.marker-bubble`, `.marker-temp`, `.marker-city`, `.m-emoji` CSS block in `public/style.css` — left over from the pre-canvas DOM marker implementation, no longer referenced anywhere.
- Removed unused `@keyframes pulse-ring` and `.pulse-ring` class from the same file.
- Removed unused local `const list = data?.list || []` in `loadForecast()` ([app.js:731](public/app.js#L731)).

### Line-by-line comment pass

Added targeted inline comments to `server.py`, `public/app.js`, `public/index.html`, and `public/style.css` for non-obvious lines (MeteoSwiss icon code ranges, Python ISO-8601 `Z`-suffix quirk, forecast grace window, probability clamping, rough sunrise/sunset approximation, zoom↔range formula anchor, Unicode combining-mark strip in `safeCityName`, longitude-normalization `+540` trick, latitude/range clamps, design-token comments in `:root`, responsive-breakpoint intent). Skipped self-explanatory lines to avoid clutter.

### Mobile lag + sheet polish

Fixed heavy lag on phones and tightened the weather panel on small screens.

- `initMap()` now detects touch devices (`navigator.userAgent` regex) and drops `resolutionScale` to 1 and disables `enableLighting` on mobile. On an iPhone with DPR=3 this is ~9x fewer fragment-shader invocations than desktop-quality settings plus no sun-angle shader cost — interactions feel smooth again.
- `public/style.css` phone breakpoint (max-width 600px): panel now caps at `min(68vh, 100vh - 140px)` so ~1/3 of the globe stays visible behind the sheet, respects `env(safe-area-inset-bottom)` for notched phones, gets a proper drag-handle pill at the top (`#weather-panel::after`), rounded on all four corners, and sits with a small 8/10 px gap from the screen edges for a sheet feel rather than a flush full-width slab.
- Cache-busting bumped to `app.js?v=svg-icons-7`, `style.css?v=svg-icons-2`.

### City names on pills + visibility/screensaver fixes

Added the city name to each weather pill (name on top, temperature below, weather icon left). Pill grew from 96x34 to 116x40 to fit the name. This caused a cascade of secondary issues that all traced to one root cause.

- **`buildCityLabelCanvas` reworked** to render city name (700 weight, 9px) above the temperature (800 weight, 13px, color-coded), with the weather icon clipped to a circle on the left. Marker anchors and `cityPlacemarkMap` entries updated to store `lat/lon` for the new collision logic.
- **Screen-space collision detection** added to `updateCityTierVisibility()`: pills are projected to window coordinates, sorted by tier (megacity wins), and any pill whose AABB overlaps an already-placed pill is hidden. Prevents the cluttered overlap that the bigger pills caused, especially in dense regions like Europe.
- **Backside culling** via `Cesium.EllipsoidalOccluder` so pills on the far side of the globe stop bleeding through (the "Mumbai floating in space" bug). Runs before screen projection.
- **Cesium API rename compatibility**: `C.SceneTransforms.wgs84ToWindowCoordinates` was renamed to `worldToWindowCoordinates` in Cesium ≥1.110. The function now picks whichever the loaded build exposes. **This rename was the actual root cause of the screensaver-rotation regression** — `updateCityTierVisibility()` threw a `TypeError` inside `showScreensaver()` *before* the line that schedules `startRotation()`, so the spin never started. Spent several rounds guessing at render-mode toggles, `setView` vs `camera.rotate`, and `requestRender` calls before checking the browser console revealed the real cause.
- **Screensaver rotation rewritten** to use the canonical Cesium pattern: `scene.preRender` event listener with `requestRenderMode = false` for the duration of the spin, and a frame-rate-independent angular velocity (`radPerSec * dt`). Replaces the old `setInterval` + `camera.rotate` approach. `stopRotation` restores `requestRenderMode = true` to keep the GPU/battery savings when idle.
- **Camera snapshot on screensaver entry, restore on dismiss**: previously, when the screensaver zoomed in to `HOME_VIEW.range * 0.65` and rotated, dismissing left the camera wherever the spin had drifted it. `showScreensaver()` now captures lat/lon/range; `dismissScreensaver()` flies back to that snapshot (or `HOME_VIEW` if none) over 1.2s, then re-runs the visibility pass.
- **`move_end` listener skipped during rotation** ([app.js:1685](public/app.js#L1685)) so the collision recompute doesn't fight the spin every frame.
- **`map.rotateLon` adapter method removed** (was only called by the old setInterval-based rotation, now dead code).
- Cache-busting bumped iteratively from `app.js?v=svg-icons-10` → `svg-icons-17` across the debugging session.

### WebGL initialization, fullscreen, and resize hardening

The previous Cesium 1.126 + Chrome 147 combination produced repeated `RuntimeError: The browser supports WebGL, but initialization failed` errors and shader compile failures during fullscreen / window resize. Diagnosed and fixed:

- **Wrote a standalone diagnostic page** (`public/webgl-test.html`, since deleted) that probes WebGL2/WebGL1 with multiple option sets, queries `WEBGL_debug_renderer_info`, attempts to allocate up to 32 simultaneous contexts, and renders a real triangle. Confirmed the dev machine (RTX 3050 Laptop, ANGLE/D3D11) can do both WebGL1 and WebGL2 with default and relaxed options — so the failure was specific to Cesium, not the browser.
- **Pinned Cesium to 1.119** in [public/app.js:330](public/app.js#L330): the last release that still honors `contextOptions.requestWebgl1`. Newer Cesium ships GLSL ES 3.00 shaders (with `flat` qualifiers) that fail to compile on WebGL1 contexts.
- **Switched CDN from unpkg to jsDelivr**. Once Cesium initialized, unpkg was returning runtime asset XHRs (skybox textures, IAU2006 ephemerides, worker scripts) without `Access-Control-Allow-Origin` headers, blocking them. jsDelivr serves the same packages with permissive CORS.
- **Wrapped `new C.Viewer(...)` in try/catch** with an inline fallback panel (globe icon + "3D globe unavailable" message) for devices that genuinely can't get any WebGL context, so the whole app no longer dies on a single Cesium failure.
- **Stripped `contextOptions` to bare minimum**: only `failIfMajorPerformanceCaveat: false` is set now, letting Cesium pick its own defaults for `alpha` / `antialias` / WebGL version. Maximizes the chance the GPU accepts the request.
- **Hid Cesium's built-in error panel** via CSS (`.cesium-widget-errorPanel { display: none !important }`) since it positions poorly in fullscreen and showed up as a cropped dark-blue mess.

### Resize / fullscreen → page reload

Replaced the in-place resize handler with a debounced page reload. The previous version called `viewer.resize()` + capped `resolutionScale` to keep Cesium happy through every resize event, but on weak GPUs this still triggered shader recompile failures and framebuffer-realloc crashes when entering fullscreen.

- On any window resize or `fullscreenchange` event, the loading screen reappears instantly (overriding its 0.7s opacity transition with `style.transition = 'none'`) and a 250ms-debounced `location.reload()` fires after the resize settles.
- The reload guarantees Cesium reinitializes cleanly at the new viewport size — no shader recompile risk, no surprises.
- Removed the old `handleResize` rAF-coalesced handler, the `MAX_LOW_POWER_PIXELS` constant, and the staggered `onFullscreenChange` retries (`setTimeout(handleResize, 150/400)`) since they're all moot when the page is about to reload.
- Simplified the render-error recovery from a 4-step gradual degradation (lighting off → 0.5x → 0.25x → flashHint) to a single recovery attempt, since the most common failure path (resize-triggered) is now eliminated by the reload approach.

Cache-busting bumped iteratively across the debugging session: `webgl-fix-1` → `resize-fix-1` → `cesium-1.131` → `cesium-latest` → `cesium-webgl1` → `cesium-webgl2-fix` → `fullscreen-recovery` → `cesium-1.119-webgl1` → `cesium-jsdelivr` → `resize-reload` → `resize-reload-fast` → `cleanup-1`.

### Deployment note: CPU-only / GPU-less devices

For devices without working GPU drivers (Pi without Mesa, headless server, etc.), modern Chrome since v110 refuses to provide a WebGL context unless launched with an explicit flag. The application already has `failIfMajorPerformanceCaveat: false` so it accepts software rendering when offered — but Chrome will not offer it without the launch flag.

**Launch command for CPU-only deployment:**

```bash
chromium-browser --enable-unsafe-swiftshader http://localhost:3000
```

Or on the Pi as part of the kiosk autostart script. Performance on a CPU-only device is approximately 1–5 fps for the 3D globe — acceptable for a passive kiosk display, not for interactive use. With any working GPU (including the Pi's VideoCore), no flag is needed and the globe runs at 30–60 fps.