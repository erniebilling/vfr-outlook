import { useState } from 'react'
import SearchBar from './components/SearchBar'
import ForecastTable from './components/ForecastTable'
import LegendBar from './components/LegendBar'
import { useForecast } from './hooks/useForecast'

export default function App() {
  const [selectedIcao, setSelectedIcao] = useState<string | null>(null)
  const { data, isLoading, isError, error } = useForecast(selectedIcao)

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      {/* Header */}
      <header className="border-b border-gray-800 px-6 py-4">
        <div className="max-w-4xl mx-auto flex items-center justify-between gap-4 flex-wrap">
          <div>
            <h1 className="text-xl font-bold tracking-tight">
              ✈ VFR Watch
            </h1>
            <p className="text-xs text-gray-500">14-day VFR probability forecast</p>
          </div>
          <SearchBar onSearch={setSelectedIcao} loading={isLoading} />
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-6 py-8 space-y-6">
        {/* Legend */}
        <LegendBar />

        {/* States */}
        {!selectedIcao && (
          <div className="text-center py-20 text-gray-500">
            <div className="text-5xl mb-4">✈</div>
            <p className="text-lg">Enter an airport ICAO code to see the VFR forecast</p>
            <p className="text-sm mt-2">e.g. KBDN, KSFO, KPDX</p>
          </div>
        )}

        {isLoading && (
          <div className="text-center py-20 text-gray-400">
            <div className="animate-spin text-4xl mb-4">⟳</div>
            <p>Fetching weather data for {selectedIcao}…</p>
          </div>
        )}

        {isError && (
          <div className="bg-red-900/30 border border-red-700/50 rounded-xl p-6 text-center">
            <div className="text-red-400 font-medium mb-1">Could not load forecast</div>
            <div className="text-red-300 text-sm">{error?.message}</div>
          </div>
        )}

        {data && !isLoading && <ForecastTable data={data} />}
      </main>
    </div>
  )
}
