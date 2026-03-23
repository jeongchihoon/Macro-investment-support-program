import { useState, useEffect } from 'react'
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'
import { Sparkles } from 'lucide-react'
import { macroAPI } from '../../api/index'
import NewsFeed from '../shared/NewsFeed'

const INDICATOR_KEYS = [
  { key: 'GDP',      label: 'GDP',            color: '#6366f1' },
  { key: 'UNRATE',   label: '실업률',          color: '#ef4444' },
  { key: 'CPIAUCSL', label: 'CPI (물가지수)', color: '#f97316' },
  { key: 'FEDFUNDS', label: '기준금리',        color: '#10b981' },
  { key: 'UMCSENT',  label: '소비자심리지수',  color: '#3b82f6' },
  { key: 'INDPRO',   label: '산업생산지수',    color: '#8b5cf6' },
]

const STATE_STYLE = {
  '확장 국면':       { bg: 'bg-emerald-50', border: 'border-emerald-200', text: 'text-emerald-600' },
  '침체 국면':       { bg: 'bg-red-50',     border: 'border-red-200',     text: 'text-red-600' },
  '고인플레이션 국면': { bg: 'bg-amber-50',  border: 'border-amber-200',   text: 'text-amber-600' },
  '과도기 / 둔화 국면': { bg: 'bg-blue-50', border: 'border-blue-200',    text: 'text-blue-600' },
}

function IndicatorCard({ data }) {
  const val = data?.value
  return (
    <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
      <p className="text-xs text-slate-500">{data?.name}</p>
      <p className="text-lg font-bold text-slate-800 mt-1">
        {val != null ? val.toLocaleString(undefined, { maximumFractionDigits: 2 }) : '-'}
        <span className="text-xs text-slate-400 ml-1">{data?.unit}</span>
      </p>
      <p className="text-xs text-slate-400 mt-0.5">{data?.date}</p>
    </div>
  )
}

function MiniChart({ seriesId, color }) {
  const [data, setData] = useState([])

  useEffect(() => {
    macroAPI.getIndicator(seriesId, 40)
      .then(r => setData(r.data.data?.filter(d => d.value != null) || []))
      .catch(() => {})
  }, [seriesId])

  if (!data.length) return <div className="h-32 flex items-center justify-center text-slate-400 text-xs">로딩 중...</div>

  return (
    <ResponsiveContainer width="100%" height={130}>
      <AreaChart data={data} margin={{ top: 5, right: 5, bottom: 0, left: 0 }}>
        <defs>
          <linearGradient id={`g${seriesId}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor={color} stopOpacity={0.15} />
            <stop offset="95%" stopColor={color} stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
        <XAxis dataKey="date" hide />
        <YAxis hide domain={['auto', 'auto']} />
        <Tooltip
          contentStyle={{ background: '#ffffff', border: '1px solid #e2e8f0', fontSize: 11, borderRadius: 8 }}
          formatter={v => [v?.toFixed(2), '']}
          labelFormatter={l => l}
        />
        <Area type="monotone" dataKey="value" stroke={color} strokeWidth={1.5} fill={`url(#g${seriesId})`} dot={false} />
      </AreaChart>
    </ResponsiveContainer>
  )
}

export default function MacroView() {
  const [overview, setOverview] = useState({})
  const [marketState, setMarketState] = useState(null)
  const [aiResult, setAiResult] = useState(null)
  const [aiLoading, setAiLoading] = useState(false)

  useEffect(() => {
    macroAPI.getOverview().then(r => setOverview(r.data.indicators || {})).catch(() => {})
    macroAPI.getMarketState().then(r => setMarketState(r.data)).catch(() => {})
  }, [])

  const handleAi = () => {
    setAiLoading(true)
    macroAPI.aiAnalyze()
      .then(r => setAiResult(r.data))
      .finally(() => setAiLoading(false))
  }

  const style = marketState ? (STATE_STYLE[marketState.state] || STATE_STYLE['과도기 / 둔화 국면']) : null

  return (
    <div className="p-6 space-y-6 overflow-y-auto h-full">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-bold text-slate-800">거시경제 대시보드</h2>
        <button
          onClick={handleAi}
          disabled={aiLoading}
          className="flex items-center gap-2 px-3 py-1.5 bg-indigo-50 border border-indigo-200 text-indigo-600 rounded-lg text-sm hover:bg-indigo-100 transition-all disabled:opacity-50"
        >
          <Sparkles size={14} />
          {aiLoading ? 'AI 분석 중...' : 'AI 시장 분석'}
        </button>
      </div>

      {/* 시장 상태 배너 */}
      {marketState && style && (
        <div className={`rounded-xl border p-4 ${style.bg} ${style.border}`}>
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs text-slate-500 mb-1">현재 시장 상태</p>
              <p className={`text-xl font-bold ${style.text}`}>{marketState.state}</p>
            </div>
            <div className="grid grid-cols-2 gap-x-6 gap-y-1 text-right">
              {[
                { label: 'GDP 성장(QoQ)', val: marketState.metrics?.gdp_growth_qoq, unit: '%' },
                { label: '실업률', val: marketState.metrics?.unemployment, unit: '%' },
                { label: 'CPI YoY', val: marketState.metrics?.cpi_yoy, unit: '%' },
                { label: '기준금리', val: marketState.metrics?.fed_rate, unit: '%' },
              ].map(m => (
                <div key={m.label}>
                  <p className="text-xs text-slate-500">{m.label}</p>
                  <p className="text-sm font-semibold text-slate-700">
                    {m.val != null ? `${m.val}${m.unit}` : '-'}
                  </p>
                </div>
              ))}
            </div>
          </div>

          <div className="mt-3 grid grid-cols-2 gap-4">
            <div>
              <p className="text-xs text-slate-500 mb-1">유리한 섹터</p>
              <div className="flex flex-wrap gap-1">
                {marketState.recommended_sectors?.map(s => (
                  <span key={s} className="text-xs bg-emerald-100 text-emerald-700 px-2 py-0.5 rounded">{s}</span>
                ))}
              </div>
            </div>
            <div>
              <p className="text-xs text-slate-500 mb-1">주의 섹터</p>
              <div className="flex flex-wrap gap-1">
                {marketState.caution_sectors?.map(s => (
                  <span key={s} className="text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded">{s}</span>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* AI 분석 결과 */}
      {aiResult && (
        <div className={`p-4 rounded-xl text-xs leading-relaxed border whitespace-pre-wrap ${
          aiResult.status === 'disabled'
            ? 'bg-amber-50 text-amber-700 border-amber-200'
            : aiResult.status === 'success'
            ? 'bg-indigo-50 text-slate-600 border-indigo-200'
            : 'bg-red-50 text-red-600 border-red-200'
        }`}>
          {aiResult.analysis || aiResult.message}
        </div>
      )}

      {/* 주요 지표 카드 */}
      <div className="grid grid-cols-3 gap-3">
        {INDICATOR_KEYS.slice(0, 6).map(({ key }) => (
          <IndicatorCard key={key} data={overview[key]} />
        ))}
      </div>

      {/* 지표 차트 */}
      <div className="grid grid-cols-2 gap-4">
        {INDICATOR_KEYS.map(({ key, label, color }) => (
          <div key={key} className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
            <p className="text-xs font-medium text-slate-500 mb-2">{label}</p>
            <MiniChart seriesId={key} color={color} />
          </div>
        ))}
      </div>

      {/* 거시 뉴스 */}
      <NewsFeed ticker={null} />
    </div>
  )
}
