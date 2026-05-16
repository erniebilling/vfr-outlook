import { useState } from 'react'
import SearchBar from './components/SearchBar'
import LegendBar from './components/LegendBar'
import ScoringPanel from './components/ScoringPanel'
import RegionDashboard from './components/RegionDashboard'
import TripPlanner from './components/TripPlanner'
import { useRegion } from './hooks/useRegion'
import { useNearby } from './hooks/useNearby'

type Tab = 'region' | 'trip'

interface GeoCoords { lat: number; lon: number }

export default function App() {
  const [tab, setTab] = useState<Tab>('region')
  const [selectedIcao, setSelectedIcao] = useState<string | null>(null)
  const [geoCoords, setGeoCoords] = useState<GeoCoords | null>(null)
  const [geoError, setGeoError] = useState<string | null>(null)
  const [geoLoading, setGeoLoading] = useState(false)
  const [radius, setRadius] = useState(115)   // 100 nm in miles
  const [maxAirports, setMaxAirports] = useState(20)
  const [useNm, setUseNm] = useState(true)
  const [minRwyFt, setMinRwyFt] = useState(2000)
  const [hardSurface, setHardSurface] = useState(true)

  const useLocation = geoCoords !== null && selectedIcao === null

  const regionQuery = useRegion(selectedIcao, radius, maxAirports, minRwyFt, hardSurface)
  const nearbyQuery = useNearby(
    useLocation
      ? { lat: geoCoords.lat, lon: geoCoords.lon, radius, maxAirports, minRwyFt, hardSurface }
      : null
  )

  const { data, isLoading, isError, error } = useLocation ? nearbyQuery : regionQuery

  function handleLocate() {
    if (!navigator.geolocation) {
      setGeoError('Geolocation is not supported by your browser.')
      return
    }
    setGeoLoading(true)
    setGeoError(null)
    setSelectedIcao(null)
    navigator.geolocation.getCurrentPosition(
      pos => {
        setGeoCoords({ lat: pos.coords.latitude, lon: pos.coords.longitude })
        setGeoLoading(false)
      },
      err => {
        setGeoError(err.message)
        setGeoLoading(false)
      },
      { timeout: 10000 }
    )
  }

  function handleSearch(icao: string) {
    setGeoCoords(null)
    setGeoError(null)
    setSelectedIcao(icao)
  }

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      <header className="border-b border-gray-800 px-4 sm:px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between gap-4 flex-wrap">
          <div>
            <h1 className="text-xl font-bold tracking-tight">✈ VFR Outlook</h1>
            <p className="text-xs text-gray-500">14-day VFR probability forecast</p>
          </div>
          <div className="flex items-center gap-4 flex-1 min-w-0">
            <button
              onClick={() => setUseNm(v => !v)}
              className="text-xs px-3 py-1.5 rounded border border-gray-700 bg-gray-800 hover:bg-gray-700 transition-colors text-gray-300 shrink-0"
              title="Toggle distance units"
            >
              {useNm ? 'NM' : 'mi'}
            </button>
            {tab === 'region' && (
              <div className="flex-1 min-w-0 flex gap-2">
                <div className="flex-1 min-w-0">
                  <SearchBar onSearch={handleSearch} loading={isLoading && !useLocation} />
                </div>
                <button
                  onClick={handleLocate}
                  disabled={geoLoading || (isLoading && useLocation)}
                  title="Show airports near my current location"
                  className="shrink-0 px-3 py-2 rounded-lg border border-gray-600 bg-gray-800 hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-gray-300 text-sm"
                >
                  {geoLoading || (isLoading && useLocation) ? '…' : '⊕ My Location'}
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Tabs */}
        <div className="max-w-7xl mx-auto mt-3 flex gap-1">
          <button
            onClick={() => setTab('region')}
            className={`px-4 py-1.5 rounded-t text-sm font-medium transition-colors ${
              tab === 'region'
                ? 'bg-gray-800 text-white border-b-2 border-blue-500'
                : 'text-gray-500 hover:text-gray-300'
            }`}
          >
            Regional<span className="hidden sm:inline"> Dashboard</span>
          </button>
          <button
            onClick={() => setTab('trip')}
            className={`px-4 py-1.5 rounded-t text-sm font-medium transition-colors ${
              tab === 'trip'
                ? 'bg-gray-800 text-white border-b-2 border-blue-500'
                : 'text-gray-500 hover:text-gray-300'
            }`}
          >
            Trip Planner
          </button>
        </div>
      </header>

      <div className="border-b border-yellow-700/50 bg-yellow-950/40 px-6 py-2">
        <p className="max-w-7xl mx-auto text-xs text-yellow-300/80 text-center">
          <span className="font-semibold text-yellow-300">Planning aid only.</span>{' '}
          Always obtain a full weather briefing from Flight Service (1-800-WX-BRIEF) or{' '}
          <a href="https://www.1800wxbrief.com" target="_blank" rel="noopener noreferrer" className="underline hover:text-yellow-200">
            1800wxbrief.com
          </a>{' '}
          before flight. Check NOTAMs and TFRs. You are PIC — the final go/no-go decision is always yours.
        </p>
      </div>

      <main className="max-w-7xl mx-auto px-3 py-4 sm:px-6 sm:py-8 space-y-6 min-h-screen">
        <LegendBar />
        <ScoringPanel />

        {tab === 'region' && (
          <>
            {!selectedIcao && !geoCoords && !geoLoading && (
              <div className="text-center py-20 text-gray-500">
                <div className="text-5xl mb-4">✈</div>
                <p className="text-lg">Enter an airport code or use your current location</p>
                <p className="text-sm mt-2">Shows all airports within your chosen radius — e.g. KBDN, KSFO, KSEA</p>
              </div>
            )}

            {geoError && (
              <div className="bg-red-900/30 border border-red-700/50 rounded-xl p-4 text-center">
                <div className="text-red-400 text-sm">Could not get your location: {geoError}</div>
              </div>
            )}

            {isLoading && (
              <div className="text-center py-20 text-gray-400">
                <div className="animate-spin text-4xl mb-4">⟳</div>
                <p>{useLocation ? 'Fetching forecasts for airports near your location…' : `Fetching forecasts for airports near ${selectedIcao}…`}</p>
                <p className="text-sm text-gray-600 mt-1">Querying weather APIs in parallel</p>
              </div>
            )}

            {isError && (
              <div className="bg-red-900/30 border border-red-700/50 rounded-xl p-6 text-center">
                <div className="text-red-400 font-medium mb-1">Could not load region forecast</div>
                <div className="text-red-300 text-sm">{error?.message}</div>
              </div>
            )}

            {data && !isLoading && (
              <RegionDashboard
                data={data}
                radius={radius}
                onRadiusChange={setRadius}
                maxAirports={maxAirports}
                onMaxAirportsChange={setMaxAirports}
                useNm={useNm}
                minRwyFt={minRwyFt}
                onMinRwyFtChange={setMinRwyFt}
                hardSurface={hardSurface}
                onHardSurfaceChange={setHardSurface}
              />
            )}
          </>
        )}

        {tab === 'trip' && (
          <TripPlanner
            useNm={useNm}
            minRwyFt={minRwyFt}
            onMinRwyFtChange={setMinRwyFt}
            hardSurface={hardSurface}
            onHardSurfaceChange={setHardSurface}
          />
        )}
      </main>

    </div>
  )
}
