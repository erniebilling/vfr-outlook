import { useState, useRef } from 'react'

interface Suggestion {
  icao: string
  name: string
}

interface Props {
  onSearch: (icao: string) => void
  loading?: boolean
}

export default function SearchBar({ onSearch, loading }: Props) {
  const [input, setInput] = useState('')
  const [suggestions, setSuggestions] = useState<Suggestion[]>([])
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const handleChange = (value: string) => {
    setInput(value)
    if (debounceRef.current) clearTimeout(debounceRef.current)

    if (value.length < 2) {
      setSuggestions([])
      return
    }

    debounceRef.current = setTimeout(async () => {
      try {
        const res = await fetch(`/api/v1/airports/search?q=${encodeURIComponent(value)}`)
        if (res.ok) setSuggestions(await res.json())
      } catch {
        setSuggestions([])
      }
    }, 300)
  }

  const handleSubmit = (icao?: string) => {
    const target = (icao ?? input).toUpperCase().trim()
    if (target) {
      setInput(target)
      setSuggestions([])
      onSearch(target)
    }
  }

  return (
    <div className="relative w-full max-w-md">
      <div className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={e => handleChange(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleSubmit()}
          placeholder="Enter ICAO code (e.g. KBDN)"
          className="flex-1 bg-gray-800 border border-gray-600 rounded-lg px-4 py-2 text-white placeholder-gray-400 focus:outline-none focus:border-blue-500 uppercase"
          maxLength={4}
          spellCheck={false}
        />
        <button
          onClick={() => handleSubmit()}
          disabled={loading || !input.trim()}
          className="bg-blue-600 hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed px-4 py-2 rounded-lg font-medium transition-colors"
        >
          {loading ? 'Loading…' : 'Check'}
        </button>
      </div>

      {suggestions.length > 0 && (
        <ul className="absolute top-full mt-1 w-full bg-gray-800 border border-gray-600 rounded-lg shadow-xl z-10 overflow-hidden">
          {suggestions.map(s => (
            <li
              key={s.icao}
              onClick={() => handleSubmit(s.icao)}
              className="px-4 py-2 cursor-pointer hover:bg-gray-700 flex gap-3"
            >
              <span className="font-mono font-bold text-blue-400">{s.icao}</span>
              <span className="text-gray-300 text-sm truncate">{s.name}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
