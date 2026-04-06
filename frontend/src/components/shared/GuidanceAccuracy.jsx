import { useState, useEffect } from 'react'
import { Target, CheckCircle2, XCircle, TrendingUp, TrendingDown } from 'lucide-react'
import { stockAPI } from '../../api/index'

/* -- 원형 게이지 -- */
function CircularGauge({ value, size = 120 }) {
  const radius = (size - 16) / 2
  const circumference = 2 * Math.PI * radius
  const pct = value != null ? value / 100 : 0
  const offset = circumference * (1 - pct)
  const color = value >= 70 ? '#10b981' : value >= 50 ? '#f59e0b' : '#ef4444'

  return (
    <svg width={size} height={size} className="transform -rotate-90">
      <circle
        cx={size / 2} cy={size / 2} r={radius}
        fill="none" stroke="#e2e8f0" strokeWidth={8}
      />
      <circle
        cx={size / 2} cy={size / 2} r={radius}
        fill="none" stroke={color} strokeWidth={8}
        strokeDasharray={circumference}
        strokeDashoffset={offset}
        strokeLinecap="round"
        className="transition-all duration-700 ease-out"
      />
      <text
        x={size / 2} y={size / 2}
        textAnchor="middle" dominantBaseline="central"
        className="transform rotate-90 origin-center"
        fill={color} fontSize={size * 0.22} fontWeight="bold"
      >
        {value != null ? `${value}%` : '-'}
      </text>
    </svg>
  )
}

/* -- 분기 카드 -- */
function QuarterCard({ q }) {
  const borderColor = q.correct ? 'border-emerald-200' : 'border-red-200'
  const bgColor = q.correct ? 'bg-emerald-50/50' : 'bg-red-50/50'

  return (
    <div className={`rounded-xl border ${borderColor} ${bgColor} p-4 space-y-3`}>
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <span className="text-sm font-semibold text-slate-700">
          {q.period || q.period_end}
        </span>
        {q.correct
          ? <CheckCircle2 size={18} className="text-emerald-500" />
          : <XCircle size={18} className="text-red-400" />
        }
      </div>

      {/* 가이던스 vs 실제 비교 */}
      <div className="grid grid-cols-2 gap-3 text-xs">
        <div className="space-y-1">
          <div className="text-slate-400 font-medium">가이던스 감성</div>
          <div className="flex items-center gap-1">
            {q.guidance_positive
              ? <TrendingUp size={14} className="text-emerald-500" />
              : <TrendingDown size={14} className="text-red-400" />
            }
            <span className={`font-bold ${q.guidance_positive ? 'text-emerald-600' : 'text-red-500'}`}>
              {q.sentiment_score}점
            </span>
            <span className="text-slate-400">
              ({q.guidance_positive ? '긍정' : '부정'})
            </span>
          </div>
        </div>
        <div className="space-y-1">
          <div className="text-slate-400 font-medium">실제 결과</div>
          <div className="flex items-center gap-1">
            {q.actually_beat
              ? <TrendingUp size={14} className="text-emerald-500" />
              : <TrendingDown size={14} className="text-red-400" />
            }
            <span className={`font-bold ${q.actually_beat ? 'text-emerald-600' : 'text-red-500'}`}>
              {q.surprise_pct > 0 ? '+' : ''}{q.surprise_pct.toFixed(2)}%
            </span>
            <span className="text-slate-400">
              ({q.actually_beat ? 'Beat' : 'Miss'})
            </span>
          </div>
        </div>
      </div>

      {/* 1일 주가 반응 */}
      {q.reaction_1d != null && (
        <div className="text-xs text-slate-500">
          발표 후 1일:{' '}
          <span className={`font-mono font-bold ${q.reaction_1d > 0 ? 'text-emerald-600' : 'text-red-500'}`}>
            {q.reaction_1d > 0 ? '+' : ''}{q.reaction_1d.toFixed(2)}%
          </span>
        </div>
      )}

      {/* 테마 태그 */}
      {q.themes?.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {q.themes.map((t, i) => (
            <span key={i} className="text-[10px] px-1.5 py-0.5 rounded-full bg-slate-100 text-slate-500 border border-slate-200">
              {t}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}

/* -- 메인 컴포넌트 -- */
export default function GuidanceAccuracy({ ticker }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!ticker) return
    let cancelled = false
    setLoading(true)
    setError(null)

    stockAPI.getGuidanceAccuracy(ticker)
      .then(res => {
        if (!cancelled) setData(res.data)
      })
      .catch(err => {
        if (!cancelled) setError(err.response?.data?.detail || '가이던스 정확도 조회 실패')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => { cancelled = true }
  }, [ticker])

  /* 로딩 */
  if (loading) {
    return (
      <div className="bg-white rounded-2xl border border-slate-200 p-6 animate-pulse">
        <div className="h-5 w-48 bg-slate-200 rounded mb-4" />
        <div className="h-32 bg-slate-100 rounded-xl" />
      </div>
    )
  }

  /* 에러 */
  if (error) {
    return (
      <div className="bg-white rounded-2xl border border-slate-200 p-6">
        <div className="text-sm text-red-500">{error}</div>
      </div>
    )
  }

  /* 데이터 없음 */
  if (!data || data.accuracy == null || !data.quarters?.length) {
    return (
      <div className="bg-white rounded-2xl border border-slate-200 p-6">
        <div className="flex items-center gap-2 mb-2">
          <Target size={18} className="text-slate-400" />
          <h3 className="font-semibold text-slate-700">가이던스 정확도</h3>
        </div>
        <p className="text-sm text-slate-400">
          {data?.message || '비교 가능한 가이던스 데이터가 없습니다. 가이던스 분석을 먼저 실행해 주세요.'}
        </p>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-2xl border border-slate-200 p-6 space-y-5">
      {/* 헤더 + 게이지 */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Target size={18} className="text-indigo-500" />
            <h3 className="font-semibold text-slate-700">가이던스 정확도</h3>
          </div>
          <p className="text-xs text-slate-400">
            가이던스 감성(긍정/부정)이 실제 어닝 서프라이즈(Beat/Miss)를 맞춘 비율
          </p>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-bold text-slate-800">{data.accuracy}%</span>
            <span className="text-sm text-slate-400">
              ({data.correct}/{data.total} 분기 적중)
            </span>
          </div>
        </div>
        <CircularGauge value={data.accuracy} />
      </div>

      {/* 분기별 카드 */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {data.quarters.map((q, i) => (
          <QuarterCard key={q.period_end || i} q={q} />
        ))}
      </div>
    </div>
  )
}
