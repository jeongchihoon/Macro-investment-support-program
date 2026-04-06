import { useState, useEffect } from 'react'
import { Scale, TrendingUp, TrendingDown, Minus, BarChart2 } from 'lucide-react'
import { stockAPI } from '../../api/index'

/* ── 추천 등급 배지 색상 ── */
const REC_COLORS = {
  buy:        { bg: 'bg-emerald-100', text: 'text-emerald-700', label: 'Buy' },
  strongbuy:  { bg: 'bg-emerald-200', text: 'text-emerald-800', label: 'Strong Buy' },
  strong_buy: { bg: 'bg-emerald-200', text: 'text-emerald-800', label: 'Strong Buy' },
  overweight: { bg: 'bg-emerald-100', text: 'text-emerald-700', label: 'Overweight' },
  hold:       { bg: 'bg-amber-100',   text: 'text-amber-700',   label: 'Hold' },
  neutral:    { bg: 'bg-amber-100',   text: 'text-amber-700',   label: 'Neutral' },
  sell:       { bg: 'bg-red-100',     text: 'text-red-700',     label: 'Sell' },
  strongsell: { bg: 'bg-red-200',     text: 'text-red-800',     label: 'Strong Sell' },
  strong_sell:{ bg: 'bg-red-200',     text: 'text-red-800',     label: 'Strong Sell' },
  underweight:{ bg: 'bg-red-100',     text: 'text-red-700',     label: 'Underweight' },
}

function getRecStyle(rec) {
  if (!rec) return { bg: 'bg-slate-100', text: 'text-slate-500', label: '-' }
  const key = rec.toLowerCase().replace(/[\s-]/g, '')
  return REC_COLORS[key] || { bg: 'bg-slate-100', text: 'text-slate-600', label: rec }
}

/* ── 감성 점수 → 색상 ── */
function sentimentColor(score) {
  if (score == null) return 'text-slate-400'
  if (score >= 65) return 'text-emerald-600'
  if (score >= 55) return 'text-emerald-500'
  if (score >= 45) return 'text-amber-500'
  if (score >= 35) return 'text-orange-500'
  return 'text-red-500'
}

function sentimentBg(score) {
  if (score == null) return 'bg-slate-100'
  if (score >= 65) return 'bg-emerald-50'
  if (score >= 55) return 'bg-emerald-50/50'
  if (score >= 45) return 'bg-amber-50'
  if (score >= 35) return 'bg-orange-50'
  return 'bg-red-50'
}

/* ── 일치/불일치 판정 ── */
function getAlignment(analyst, ai) {
  if (!analyst || !ai) return null

  const analystBullish = analyst.implied_upside != null && analyst.implied_upside > 5
  const analystBearish = analyst.implied_upside != null && analyst.implied_upside < -5
  const aiBullish = ai.trend === 'positive'
  const aiBearish = ai.trend === 'negative'

  if ((analystBullish && aiBullish) || (analystBearish && aiBearish)) {
    return { level: 'agree', label: '의견 일치', color: 'text-emerald-600', bg: 'bg-emerald-50', border: 'border-emerald-200' }
  }
  if ((analystBullish && aiBearish) || (analystBearish && aiBullish)) {
    return { level: 'disagree', label: '의견 불일치', color: 'text-red-600', bg: 'bg-red-50', border: 'border-red-200' }
  }
  return { level: 'partial', label: '부분 일치', color: 'text-amber-600', bg: 'bg-amber-50', border: 'border-amber-200' }
}

/* ── 목표가 레인지 바 ── */
function TargetRangeBar({ low, mean, high, current }) {
  if (!low || !high || !current) return null

  const min = Math.min(low, current) * 0.95
  const max = Math.max(high, current) * 1.05
  const range = max - min || 1

  const lowPct = ((low - min) / range) * 100
  const highPct = ((high - min) / range) * 100
  const meanPct = ((mean - min) / range) * 100
  const currentPct = ((current - min) / range) * 100

  return (
    <div className="mt-3">
      <div className="flex justify-between text-[10px] text-slate-400 mb-1">
        <span>${low?.toFixed(0)}</span>
        <span>${high?.toFixed(0)}</span>
      </div>
      <div className="relative h-3 bg-slate-100 rounded-full overflow-hidden">
        {/* Range bar */}
        <div
          className="absolute top-0 h-full bg-indigo-100 rounded-full"
          style={{ left: `${lowPct}%`, width: `${highPct - lowPct}%` }}
        />
        {/* Mean marker */}
        <div
          className="absolute top-0 h-full w-0.5 bg-indigo-500"
          style={{ left: `${meanPct}%` }}
        />
        {/* Current price marker */}
        <div
          className="absolute -top-0.5 w-4 h-4 bg-white border-2 border-slate-700 rounded-full shadow-sm"
          style={{ left: `${currentPct}%`, transform: 'translateX(-50%)' }}
        />
      </div>
      <div className="flex justify-between items-center mt-1.5">
        <span className="text-[10px] text-slate-400">저가</span>
        <span className="text-[10px] font-medium text-indigo-600">평균 ${mean?.toFixed(0)}</span>
        <span className="text-[10px] text-slate-400">고가</span>
      </div>
    </div>
  )
}

/* ── 감성 게이지 ── */
function SentimentGauge({ score }) {
  if (score == null) return <span className="text-xs text-slate-400">데이터 없음</span>

  const clampedScore = Math.max(0, Math.min(100, score))
  const rotation = (clampedScore / 100) * 180 - 90

  return (
    <div className="flex flex-col items-center">
      <div className="relative w-28 h-16 overflow-hidden">
        {/* Background arc */}
        <div className="absolute bottom-0 left-0 right-0 h-28 w-28 rounded-full border-[8px] border-slate-100"
          style={{ clipPath: 'inset(0 0 50% 0)' }}
        />
        {/* Colored sections */}
        <svg viewBox="0 0 120 60" className="w-full h-full">
          <path d="M 10 58 A 50 50 0 0 1 44 12" fill="none" stroke="#fca5a5" strokeWidth="7" strokeLinecap="round" />
          <path d="M 44 12 A 50 50 0 0 1 76 12" fill="none" stroke="#fcd34d" strokeWidth="7" strokeLinecap="round" />
          <path d="M 76 12 A 50 50 0 0 1 110 58" fill="none" stroke="#6ee7b7" strokeWidth="7" strokeLinecap="round" />
          {/* Needle */}
          <line
            x1="60" y1="58" x2="60" y2="18"
            stroke="#334155" strokeWidth="2" strokeLinecap="round"
            transform={`rotate(${rotation}, 60, 58)`}
          />
          <circle cx="60" cy="58" r="4" fill="#334155" />
        </svg>
      </div>
      <p className={`text-lg font-bold mt-1 ${sentimentColor(score)}`}>{score?.toFixed(0)}</p>
      <p className="text-[10px] text-slate-400">/ 100</p>
    </div>
  )
}

/* ── 트렌드 아이콘 ── */
function TrendIcon({ trend }) {
  if (trend === 'positive') return <TrendingUp size={16} className="text-emerald-500" />
  if (trend === 'negative') return <TrendingDown size={16} className="text-red-500" />
  return <Minus size={16} className="text-amber-500" />
}

const TREND_LABELS = { positive: '긍정적', negative: '부정적', neutral: '중립' }

/* ══════════════════════════════════════════════════════
   메인 컴포넌트
   ══════════════════════════════════════════════════════ */
export default function AnalystVsAI({ ticker }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!ticker) return
    setLoading(true)
    setError(null)
    stockAPI.getAnalystVsAI(ticker)
      .then(res => setData(res.data))
      .catch(err => setError(err.response?.data?.detail || '데이터를 불러올 수 없습니다'))
      .finally(() => setLoading(false))
  }, [ticker])

  /* ── 로딩 ── */
  if (loading) {
    return (
      <div className="bg-white rounded-2xl border border-slate-200 p-6 animate-pulse">
        <div className="h-5 w-56 bg-slate-200 rounded mb-6" />
        <div className="grid grid-cols-3 gap-4">
          <div className="h-48 bg-slate-100 rounded-xl" />
          <div className="h-48 bg-slate-100 rounded-xl" />
          <div className="h-48 bg-slate-100 rounded-xl" />
        </div>
      </div>
    )
  }

  /* ── 에러 ── */
  if (error) {
    return (
      <div className="bg-white rounded-2xl border border-red-200 p-6">
        <div className="flex items-center gap-2 text-red-600">
          <Scale size={18} />
          <span className="text-sm font-medium">애널리스트 vs AI 비교</span>
        </div>
        <p className="text-sm text-red-500 mt-2">{error}</p>
      </div>
    )
  }

  if (!data) return null

  const { analyst, ai } = data
  const alignment = getAlignment(analyst, ai)
  const recStyle = getRecStyle(analyst?.recommendation)

  return (
    <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden">
      {/* ── 헤더 ── */}
      <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Scale size={18} className="text-indigo-500" />
          <h3 className="text-sm font-bold text-slate-800">애널리스트 vs AI 분석 비교</h3>
        </div>
        {alignment && (
          <span className={`px-3 py-1 text-xs font-semibold rounded-full border ${alignment.bg} ${alignment.color} ${alignment.border}`}>
            {alignment.label}
          </span>
        )}
      </div>

      {/* ── 메인 3열 그리드 ── */}
      <div className="grid grid-cols-1 md:grid-cols-3 divide-y md:divide-y-0 md:divide-x divide-slate-100">

        {/* ── 좌측: 애널리스트 컨센서스 ── */}
        <div className="p-5">
          <div className="flex items-center gap-2 mb-4">
            <BarChart2 size={14} className="text-indigo-500" />
            <span className="text-xs font-bold text-slate-600 uppercase tracking-wider">Wall Street 컨센서스</span>
          </div>

          {/* 추천 배지 */}
          <div className="flex items-center gap-2 mb-4">
            <span className={`px-3 py-1 text-xs font-bold rounded-full ${recStyle.bg} ${recStyle.text}`}>
              {recStyle.label}
            </span>
          </div>

          {/* 현재가 / 목표가 */}
          <div className="space-y-2 mb-3">
            <div className="flex justify-between text-xs">
              <span className="text-slate-500">현재가</span>
              <span className="font-semibold text-slate-800">
                {analyst?.current_price ? `$${analyst.current_price.toFixed(2)}` : '-'}
              </span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-slate-500">평균 목표가</span>
              <span className="font-semibold text-indigo-600">
                {analyst?.target_mean ? `$${analyst.target_mean.toFixed(2)}` : '-'}
              </span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-slate-500">예상 수익률</span>
              <span className={`font-bold ${
                analyst?.implied_upside > 0 ? 'text-emerald-600' : analyst?.implied_upside < 0 ? 'text-red-600' : 'text-slate-600'
              }`}>
                {analyst?.implied_upside != null ? `${analyst.implied_upside > 0 ? '+' : ''}${analyst.implied_upside}%` : '-'}
              </span>
            </div>
          </div>

          {/* 목표가 레인지 바 */}
          <TargetRangeBar
            low={analyst?.target_low}
            mean={analyst?.target_mean}
            high={analyst?.target_high}
            current={analyst?.current_price}
          />

          {/* Forward PE / EPS */}
          <div className="mt-4 pt-3 border-t border-slate-100 space-y-1.5">
            <div className="flex justify-between text-xs">
              <span className="text-slate-500">Forward PE</span>
              <span className="font-medium text-slate-700">
                {analyst?.forward_pe ? analyst.forward_pe.toFixed(1) : '-'}
              </span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-slate-500">EPS</span>
              <span className="font-medium text-slate-700">
                {analyst?.eps ? `$${analyst.eps.toFixed(2)}` : '-'}
              </span>
            </div>
          </div>
        </div>

        {/* ── 중앙: 비교 요약 ── */}
        <div className="p-5 flex flex-col items-center justify-center">
          {alignment ? (
            <>
              <div className={`w-16 h-16 rounded-full flex items-center justify-center mb-3 ${alignment.bg} ${alignment.border} border-2`}>
                {alignment.level === 'agree' && <TrendingUp size={28} className="text-emerald-500" />}
                {alignment.level === 'disagree' && <TrendingDown size={28} className="text-red-500" />}
                {alignment.level === 'partial' && <Scale size={28} className="text-amber-500" />}
              </div>
              <p className={`text-sm font-bold ${alignment.color}`}>{alignment.label}</p>
              <p className="text-[11px] text-slate-400 text-center mt-2 leading-relaxed max-w-[180px]">
                {alignment.level === 'agree' && '월가 애널리스트와 AI 가이던스 분석이 같은 방향을 가리키고 있습니다.'}
                {alignment.level === 'disagree' && '월가 컨센서스와 AI 분석이 상반된 시각을 보이고 있습니다. 주의가 필요합니다.'}
                {alignment.level === 'partial' && '일부 시각 차이가 있으나 극단적인 불일치는 아닙니다.'}
              </p>

              {/* 수치 비교 */}
              <div className="mt-5 w-full space-y-2">
                {analyst?.implied_upside != null && (
                  <div className="flex items-center justify-between text-xs px-2">
                    <span className="text-slate-400">애널리스트</span>
                    <span className={`font-bold ${analyst.implied_upside > 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                      {analyst.implied_upside > 0 ? '+' : ''}{analyst.implied_upside}%
                    </span>
                  </div>
                )}
                {ai && (
                  <div className="flex items-center justify-between text-xs px-2">
                    <span className="text-slate-400">AI 감성</span>
                    <span className={`font-bold ${sentimentColor(ai.avg_sentiment)}`}>
                      {ai.avg_sentiment?.toFixed(0)}/100
                    </span>
                  </div>
                )}
              </div>
            </>
          ) : (
            <div className="text-center">
              <Scale size={32} className="text-slate-300 mx-auto mb-2" />
              <p className="text-xs text-slate-400">비교 데이터 부족</p>
              <p className="text-[10px] text-slate-300 mt-1">가이던스 분석을 먼저 실행해주세요</p>
            </div>
          )}
        </div>

        {/* ── 우측: AI 가이던스 분석 ── */}
        <div className="p-5">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-4 h-4 rounded bg-gradient-to-br from-violet-500 to-indigo-500 flex items-center justify-center">
              <span className="text-[8px] text-white font-bold">AI</span>
            </div>
            <span className="text-xs font-bold text-slate-600 uppercase tracking-wider">AI 가이던스 분석</span>
          </div>

          {ai ? (
            <>
              {/* 감성 게이지 */}
              <div className="flex justify-center mb-4">
                <SentimentGauge score={ai.latest_sentiment} />
              </div>

              {/* 트렌드 */}
              <div className={`flex items-center justify-center gap-2 mb-4 px-3 py-2 rounded-lg ${sentimentBg(ai.avg_sentiment)}`}>
                <TrendIcon trend={ai.trend} />
                <span className="text-xs font-semibold text-slate-700">
                  트렌드: {TREND_LABELS[ai.trend] || ai.trend}
                </span>
                <span className="text-[10px] text-slate-400">({ai.quarters_analyzed}Q 분석)</span>
              </div>

              {/* 핵심 테마 */}
              {ai.latest_themes && ai.latest_themes.length > 0 && (
                <div className="mb-3">
                  <p className="text-[10px] text-slate-400 mb-1.5 font-medium">핵심 테마</p>
                  <div className="flex flex-wrap gap-1">
                    {ai.latest_themes.map((theme, i) => (
                      <span key={i} className="px-2 py-0.5 text-[10px] bg-indigo-50 text-indigo-600 rounded-full border border-indigo-100">
                        {typeof theme === 'string' ? theme : theme.theme || theme.name || JSON.stringify(theme)}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* 가이던스 요약 */}
              {ai.guidance_summary && (
                <div className="mt-3 pt-3 border-t border-slate-100">
                  <p className="text-[10px] text-slate-400 mb-1 font-medium">최근 가이던스 요약</p>
                  <p className="text-xs text-slate-600 leading-relaxed">
                    {ai.guidance_summary}
                  </p>
                </div>
              )}

              {/* 기간 */}
              {ai.latest_period && (
                <p className="text-[10px] text-slate-300 mt-2 text-right">
                  기준: {ai.latest_period}
                </p>
              )}
            </>
          ) : (
            <div className="flex flex-col items-center justify-center h-48 text-center">
              <div className="w-12 h-12 rounded-full bg-slate-50 flex items-center justify-center mb-2">
                <BarChart2 size={20} className="text-slate-300" />
              </div>
              <p className="text-xs text-slate-400">AI 분석 데이터 없음</p>
              <p className="text-[10px] text-slate-300 mt-1">
                가이던스 분석 탭에서 먼저 분석을 실행해주세요
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
