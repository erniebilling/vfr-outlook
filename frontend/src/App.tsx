import { useState } from 'react'
import SearchBar from './components/SearchBar'
import LegendBar from './components/LegendBar'
import ScoringPanel from './components/ScoringPanel'
import RegionDashboard from './components/RegionDashboard'
import { useRegion } from './hooks/useRegion'

export default function App() {
  const [selectedIcao, setSelectedIcao] = useState<string | null>(null)
  const [radius, setRadius] = useState(115)   // 100 nm in miles
  const [maxAirports, setMaxAirports] = useState(20)
  const [useNm, setUseNm] = useState(true)
  const [minRwyFt, setMinRwyFt] = useState(2000)
  const { data, isLoading, isError, error } = useRegion(selectedIcao, radius, maxAirports, minRwyFt)

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      <header className="border-b border-gray-800 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between gap-4 flex-wrap">
          <div>
            <h1 className="text-xl font-bold tracking-tight">✈ VFR Watch</h1>
            <p className="text-xs text-gray-500">14-day VFR probability — regional dashboard</p>
          </div>
          <div className="flex items-center gap-4">
            <button
              onClick={() => setUseNm(v => !v)}
              className="text-xs px-3 py-1.5 rounded border border-gray-700 bg-gray-800 hover:bg-gray-700 transition-colors text-gray-300"
              title="Toggle distance units"
            >
              {useNm ? 'NM' : 'mi'}
            </button>
            <SearchBar onSearch={setSelectedIcao} loading={isLoading} />
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8 space-y-6">
        <LegendBar />
        <ScoringPanel />

        {!selectedIcao && (
          <div className="text-center py-20 text-gray-500">
            <div className="text-5xl mb-4">✈</div>
            <p className="text-lg">Enter an airport ICAO code to see the regional VFR dashboard</p>
            <p className="text-sm mt-2">Shows all airports within your chosen radius — e.g. KBDN, KSFO, KSEA</p>
          </div>
        )}

        {isLoading && (
          <div className="text-center py-20 text-gray-400">
            <div className="animate-spin text-4xl mb-4">⟳</div>
            <p>Fetching forecasts for airports near {selectedIcao}…</p>
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
          />
        )}
      </main>
    </div>
  )
}
