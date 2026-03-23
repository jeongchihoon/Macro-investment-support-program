import { useState, useEffect } from 'react'
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'
import { stockAPI } from '../../api/index'

const PERIODS = [
  { label: '1일',   value: '1d' },
  { label: '3일',   value: '3d' },
  { label: '5일',   value: '5d' },
  { label: '1개월', value: '1mo' },
  { label: '3개월', value: '3mo' },
  { label: '6개월', value: '6mo' },
  { label: '1년',   value: '1y' },
  { label: '3년',   value: '3y' },
  { label: '5년',   value: '5y' },
  { label: '10년',  value: '10y' },
  { label: '전체',  value: 'max' },
]

export default function PriceChart({ ticker }) {
  const [data, setData] = useState([])
  const [period, setPeriod] = useState('1y')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!ticker) return
    setLoading(true)
    stockAPI.getPrice(ticker, period)
      .then(r => setData(r.data.data || []))
      .catch(() => setData([]))
      .finally(() => setLoading(false))
  }, [ticker, period])

  const isUp = data.length >= 2 && data[data.length - 1].close >= data[0].close
  const color = isUp ? '#10b981' : '#ef4444'
  const gradientId = `priceGrad_${ticker}_${period}`

  const formatDate = (d) => {
    if (!d) return ''
    if (d.includes(' ')) return d.split(' ')[1] // HH:MM for intraday
    if (['10y', 'max', '5y', '3y'].includes(period)) return d.slice(0, 7)
    return d.slice(5)
  }

  const CustomTooltip = ({ active, payload, label }) => {
    if (!active || !payload?.length) return null
    return (
      <div className="bg-white border border-slate-200 rounded-xl px-3.5 py-2.5 text-xs shadow-lg">
        <p className="text-slate-400 text-[10px]">{label}</p>
        <p className="text-slate-800 font-bold text-sm mt-0.5">${payload[0].value?.toFixed(2)}</p>
      </div>
    )
  }

  // 가격 변동 계산
  const startPrice = data.length > 0 ? data[0].close : null
  const endPrice = data.length > 0 ? data[data.length - 1].close : null
  const changeAmt = startPrice && endPrice ? (endPrice - startPrice) : null
  const changePct = startPrice && endPrice ? ((endPrice - startPrice) / startPrice * 100) : null

  return (
    <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm">
      <div className="flex items-center justify-between mb-1">
        <div>
          <h3 className="text-sm font-bold text-slate-800">주가 차트</h3>
          {changeAmt != null && (
            <p className={`text-xs mt-0.5 font-medium ${changePct >= 0 ? 'text-emerald-600' : 'text-red-500'}`}>
              {changePct >= 0 ? '+' : ''}{changeAmt.toFixed(2)} ({changePct >= 0 ? '+' : ''}{changePct.toFixed(2)}%)
            </p>
          )}
        </div>
      </div>

      {/* 기간 선택 버튼 */}
      <div className="flex flex-wrap gap-1 mb-4">
        {PERIODS.map(p => (
          <button
            key={p.value}
            onClick={() => setPeriod(p.value)}
            className={`px-2.5 py-1 text-[11px] rounded-lg font-medium transition-all ${
              period === p.value
                ? 'bg-indigo-600 text-white shadow-sm shadow-indigo-200'
                : 'text-slate-400 hover:text-slate-600 hover:bg-slate-100'
            }`}
          >
            {p.label}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="h-56 flex items-center justify-center text-slate-400 text-sm">
          <div className="w-5 h-5 border-2 border-indigo-400 border-t-transparent rounded-full animate-spin mr-2" />
          로딩 중...
        </div>
      ) : data.length === 0 ? (
        <div className="h-56 flex items-center justify-center text-slate-400 text-sm">데이터 없음</div>
      ) : (
        <ResponsiveContainer width="100%" height={260}>
          <AreaChart data={data} margin={{ top: 5, right: 5, bottom: 0, left: 0 }}>
            <defs>
              <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={color} stopOpacity={0.15} />
                <stop offset="95%" stopColor={color} stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 10, fill: '#94a3b8' }}
              tickFormatter={formatDate}
              interval="preserveStartEnd"
              minTickGap={40}
            />
            <YAxis
              tick={{ fontSize: 10, fill: '#94a3b8' }}
              tickFormatter={v => `$${v}`}
              width={60}
              domain={['auto', 'auto']}
            />
            <Tooltip content={<CustomTooltip />} />
            <Area
              type="monotone"
              dataKey="close"
              stroke={color}
              strokeWidth={2}
              fill={`url(#${gradientId})`}
              dot={false}
            />
          </AreaChart>
        </ResponsiveContainer>
      )}
    </div>
  )
}
