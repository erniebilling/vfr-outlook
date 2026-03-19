const LEGEND = [
  { label: 'VFR', color: 'bg-green-500', range: '85-100' },
  { label: 'MVFR', color: 'bg-lime-500', range: '65-84' },
  { label: 'Marginal', color: 'bg-yellow-500', range: '45-64' },
  { label: 'Poor', color: 'bg-orange-500', range: '25-44' },
  { label: 'IFR', color: 'bg-red-500', range: '0-24' },
]

export default function LegendBar() {
  return (
    <div className="flex flex-wrap gap-3 text-xs text-gray-300">
      {LEGEND.map(item => (
        <div key={item.label} className="flex items-center gap-1.5">
          <div className={`${item.color} w-3 h-3 rounded-sm`} />
          <span>{item.label}</span>
          <span className="text-gray-500">({item.range})</span>
        </div>
      ))}
    </div>
  )
}
