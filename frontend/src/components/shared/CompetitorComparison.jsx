import { useState, useEffect } from 'react'
import { Users, TrendingUp, TrendingDown, Minus, Layers } from 'lucide-react'
import { stockAPI } from '../../api/index'

/* ── 숫자 포매팅 헬퍼 ── */
function fmtCap(n) {
  if (n == null) return '-'
  if (Math.abs(n) >= 1e12) return '$' + (n / 1e12).toFixed(2) + 'T'
  if (Math.abs(n) >= 1e9) return '$' + (n / 1e9).toFixed(2) + 'B'
  if (Math.abs(n) >= 1e6) return '$' + (n / 1e6).toFixed(2) + 'M'
  return '$' + n.toLocaleString()
}

function fmtPct(n) {
  if (n == null) return '-'
  return (n * 100).toFixed(1) + '%'
}

function fmtNum(n, decimals = 1) {
  if (n == null) return '-'
  return n.toFixed(decimals)
}

function fmtPrice(n) {
  if (n == null) return '-'
  return '$' + Number(n).toFixed(2)
}

/* ── 비교 지표 정의 ── */
const METRICS = [
  { key: 'current_price', label: '현재가', format: fmtPrice, higherBetter: null },
  { key: 'market_cap', label: '시가총액', format: fmtCap, higherBetter: null },
  { key: 'pe_ratio', label: 'PER', format: v => fmtNum(v, 1), higherBetter: false },
  { key: 'forward_pe', label: 'Forward PE', format: v => fmtNum(v, 1), higherBetter: false },
  { key: 'profit_margin', label: '순이익률', format: fmtPct, higherBetter: true },
  { key: 'revenue_growth', label: '매출성장률', format: fmtPct, higherBetter: true },
  { key: 'roe', label: 'ROE', format: fmtPct, higherBetter: true },
  { key: 'debt_to_equity', label: '부채비율', format: v => fmtNum(v, 2), higherBetter: false },
]

/* ── 셀 색상 ── */
function getRankColor(value, allValues, higherBetter) {
  if (value == null || higherBetter == null) return ''
  const valid = allValues.filter(v => v != null)
  if (valid.length < 2) return ''
  const sorted = [...valid].sort((a, b) => higherBetter ? b - a : a - b)
  const rank = sorted.indexOf(value)
  if (rank === 0) return 'text-emerald-600 bg-emerald-50'
  if (rank === sorted.length - 1) return 'text-red-500 bg-red-50'
  return ''
}

/* ── 사업 영역별 경쟁사 그룹 테이블 ── */
function GroupTable({ group, main, mainTicker }) {
  const allStocks = [main, ...group.peers].filter(Boolean)

  return (
    <div className="mb-5 last:mb-0">
      <div className="flex items-center gap-2 mb-2">
        <Layers size={13} className="text-indigo-400" />
        <span className="text-xs font-semibold text-slate-700">{group.business_area}</span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-slate-100">
              <th className="text-left py-2 px-2 text-slate-400 font-medium w-24">지표</th>
              {allStocks.map(s => (
                <th
                  key={s.ticker}
                  className={`text-center py-2 px-2 font-semibold ${
                    s.ticker === mainTicker ? 'text-indigo-600' : 'text-slate-600'
                  }`}
                >
                  <div>{s.ticker}</div>
                  <div className="font-normal text-[10px] text-slate-400 truncate max-w-[80px] mx-auto" title={s.name}>
                    {s.name}
                  </div>
                  {s.description && (
                    <div className="font-normal text-[9px] text-slate-300 truncate max-w-[100px] mx-auto mt-0.5" title={s.description}>
                      {s.description}
                    </div>
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {METRICS.map(metric => {
              const allValues = allStocks.map(s => s[metric.key])
              return (
                <tr key={metric.key} className="border-b border-slate-50 hover:bg-slate-50/50 transition-colors">
                  <td className="py-2 px-2 text-slate-500 font-medium">{metric.label}</td>
                  {allStocks.map(s => {
                    const val = s[metric.key]
                    const isMain = s.ticker === mainTicker
                    const colorClass = getRankColor(val, allValues, metric.higherBetter)
                    return (
                      <td
                        key={s.ticker}
                        className={`text-center py-2 px-2 tabular-nums ${
                          isMain ? 'font-semibold' : ''
                        } ${colorClass} ${isMain && !colorClass ? 'bg-indigo-50/40' : ''}`}
                      >
                        {metric.format(val)}
                      </td>
                    )
                  })}
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default function CompetitorComparison({ ticker }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!ticker) return
    setLoading(true)
    setError('')
    setData(null)
    stockAPI.getCompetitors(ticker)
      .then(r => setData(r.data))
      .catch(() => setError('경쟁사 데이터를 불러올 수 없습니다.'))
      .finally(() => setLoading(false))
  }, [ticker])

  if (loading) {
    return (
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
        <h3 className="text-sm font-semibold text-slate-700 mb-4 flex items-center gap-2">
          <Users size={15} className="text-indigo-400" />
          AI 경쟁사 분석
        </h3>
        <div className="space-y-3">
          {[1, 2, 3].map(i => (
            <div key={i} className="h-8 bg-slate-100 rounded animate-pulse" />
          ))}
        </div>
        <p className="text-xs text-slate-400 mt-3">AI가 사업 영역별 경쟁사를 분석하고 있습니다...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
        <h3 className="text-sm font-semibold text-slate-700 mb-3 flex items-center gap-2">
          <Users size={15} className="text-indigo-400" />
          AI 경쟁사 분석
        </h3>
        <p className="text-amber-600 text-xs bg-amber-50 border border-amber-200 rounded p-2">{error}</p>
      </div>
    )
  }

  const groups = data?.competitor_groups || []
  const main = data?.main

  if (!data || groups.length === 0) {
    return (
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
        <h3 className="text-sm font-semibold text-slate-700 mb-3 flex items-center gap-2">
          <Users size={15} className="text-indigo-400" />
          AI 경쟁사 분석
        </h3>
        <p className="text-slate-400 text-sm">경쟁사 데이터가 없습니다.</p>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
      {/* 헤더 */}
      <div className="flex items-center justify-between mb-1">
        <h3 className="text-sm font-semibold text-slate-700 flex items-center gap-2">
          <Users size={15} className="text-indigo-400" />
          AI 경쟁사 분석
        </h3>
        <span className="text-xs text-slate-400">
          {data.sector}{data.industry ? ` · ${data.industry}` : ''}
        </span>
      </div>
      <p className="text-[10px] text-slate-400 mb-4">Gemini AI가 사업 영역별로 실제 경쟁 관계를 분석했습니다</p>

      {/* 사업 영역별 비교 테이블 */}
      {groups.map((group, i) => (
        <GroupTable
          key={i}
          group={group}
          main={main}
          mainTicker={ticker.toUpperCase()}
        />
      ))}

      {/* 범례 */}
      <div className="flex items-center gap-4 mt-4 text-[10px] text-slate-400">
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-emerald-400" /> 그룹 내 최고
        </span>
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-red-400" /> 그룹 내 최저
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block w-3 h-2 bg-indigo-100 rounded" /> 현재 종목
        </span>
      </div>
    </div>
  )
}
