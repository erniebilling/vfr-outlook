# VFR Outlook

A 14-day VFR probability dashboard for GA pilots. Enter any US airport ICAO code and instantly see color-coded flying conditions for every airport within your chosen radius — no account, no login, no fluff.

## What it does

- **Regional heatmap** — airport × day grid showing VFR scores 0–100 for up to 20 airports at once
- **Radius selector** — 50 / 100 / 150 / 200 / 300 miles from your base airport
- **Full airport database** — ~12,000 US public airports (OurAirports), not just a hardcoded list
- **14-day horizon** — days 0–7 from NOAA hourly aviation forecasts, days 8–14 from Open-Meteo ensemble models
- **Current METAR** — today's score is always anchored to the latest observation
- **Detail drill-down** — click any airport row to expand wind, visibility, ceiling, precip, and confidence

## Scoring

Each day gets a 0–100 VFR probability score:

| Score | Label    | Color  | Meaning                        |
|-------|----------|--------|-------------------------------|
| 85–100 | VFR     | Green  | Good day to fly               |
| 65–84  | MVFR    | Lime   | Marginal but likely flyable   |
| 45–64  | Marginal | Yellow | Borderline — check carefully  |
| 25–44  | Poor     | Orange | Likely not flyable VFR        |
| 0–24   | IFR     | Red    | Not VFR                       |

Score weights: wind 30% · visibility 25% · ceiling 25% · precipitation 20%

Confidence tiers reflect data source age: **high** (days 0–3, NOAA), **medium** (days 4–7, NOAA), **low** (days 8–14, Open-Meteo).

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Browser (React + TypeScript + Tailwind)                │
│                                                         │
│  SearchBar → useRegion hook → RegionDashboard grid      │
│                             → ForecastTable (on click)  │
└─────────────────────┬───────────────────────────────────┘
                      │  /api/v1/region?icao=KBDN&radius=100
                      ▼
┌─────────────────────────────────────────────────────────┐
│  FastAPI (Python)                                       │
│                                                         │
│  GET /api/v1/region          haversine radius search    │
│  GET /api/v1/airport/{icao}  single airport forecast    │
│  GET /api/v1/airports/search full-text ICAO search      │
└─────────┬──────────────────────────┬────────────────────┘
          │                          │
          ▼                          ▼
 aviationweather.gov          Open-Meteo API
 - METAR (current obs)        - Hourly wind / cloud / precip
 - NOAA hourly forecasts        extended 16-day model
   (days 0–7)                   (days 0–16)
```

## Running locally

### Prerequisites

- Python 3.12+
- Node 22+

### Backend

```bash
pip install -r backend/requirements.txt
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

API available at `http://localhost:8000` · Swagger UI at `http://localhost:8000/docs`

### Frontend

```bash
cd frontend
npm install
npm run dev
```

App available at `http://localhost:5173`

The Vite dev server proxies all `/api` requests to the backend automatically.

### Dev container (VS Code)

Open the repo in VS Code and choose **Reopen in Container**. Dependencies install automatically via `postCreateCommand`. Ports 8000 and 5173 are forwarded to your host.

## API reference

### `GET /api/v1/region`

Returns 14-day forecasts for all K-prefix airports within a radius of a center airport.

| Parameter | Type | Default | Range | Description |
|-----------|------|---------|-------|-------------|
| `icao` | string | required | — | Center airport (e.g. `KBDN`) |
| `radius` | int | 100 | 25–300 | Search radius in miles |

Response: `RegionResponse` with up to 20 airports, each containing 14 `DayForecast` objects.

### `GET /api/v1/airport/{icao}/forecast`

Single airport 14-day forecast.

### `GET /api/v1/airports/search?q=`

Full-text search over ~12,000 US public airports. Returns `[{icao, name}]`.

## Data sources

| Source | Coverage | Used for |
|--------|----------|---------|
| [aviationweather.gov](https://aviationweather.gov/api/data/metar) | Real-time METAR | Current conditions (day 0) |
| [api.weather.gov](https://api.weather.gov) | NOAA NWS hourly | Days 0–7 |
| [open-meteo.com](https://open-meteo.com) | Global ensemble | Days 0–16 fallback / extension |
| [OurAirports](https://ourairports.com/data/) | 12,000 US airports | Airport database + coordinates |

All external APIs are free and require no API key.

## Project layout

```
vfr-outlook/
├── backend/
│   ├── main.py                  FastAPI app + CORS
│   ├── routers/airport.py       API endpoints
│   ├── services/
│   │   ├── airports.py          OurAirports DB + haversine search
│   │   ├── weather.py           METAR / NOAA / Open-Meteo fetching
│   │   └── scorer.py            VFR scoring algorithm
│   ├── models/forecast.py       Pydantic response models
│   ├── data/airports_us.json    11,864 US public airports
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.tsx              Root component + layout
│   │   ├── components/
│   │   │   ├── RegionDashboard.tsx  Airport × day heatmap grid
│   │   │   ├── ForecastTable.tsx    Single airport 14-day detail
│   │   │   ├── SearchBar.tsx        ICAO search with autocomplete
│   │   │   ├── ScoreCell.tsx        Color-coded score badge
│   │   │   └── LegendBar.tsx        Score legend
│   │   ├── hooks/
│   │   │   ├── useRegion.ts     React Query hook for region endpoint
│   │   │   └── useForecast.ts   React Query hook for single airport
│   │   ├── types/forecast.ts    TypeScript interfaces
│   │   └── lib/score.ts         Score colors, labels, date formatting
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── package.json
└── .devcontainer/devcontainer.json
```

## Safety notice

VFR Outlook is a planning aid only. Always obtain a full weather briefing from Flight Service (1-800-WX-BRIEF) or [1800wxbrief.com](https://www.1800wxbrief.com) before flight. Check NOTAMs and TFRs. You are PIC — the final go/no-go decision is always yours.
