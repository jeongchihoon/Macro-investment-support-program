import { useState, useEffect } from 'react'
import { Calendar, Clock, Star } from 'lucide-react'
import { stockAPI } from '../../api/index'

/* ── D-day 계산 ── */
function daysUntil(dateStr) {
  if (!dateStr) return null
  const target = new Date(dateStr + 'T00:00:00')
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  return Math.ceil((target - today) / (1000 * 60 * 60 * 24))
}

/* ── 날짜 포매팅 ── */
function formatDate(dateStr) {
  if (!dateStr) return '-'
  const d = new Date(dateStr + 'T00:00:00')
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

/* ── D-day 배지 ── */
function DdayBadge({ days }) {
  if (days == null) return null
  if (days < 0) {
    return <span className="text-[11px] font-semibold text-slate-400">완료</span>
  }
  if (days === 0) {
    return <span className="text-[11px] font-bold text-red-600 bg-red-50 px-2 py-0.5 rounded-full">오늘</span>
  }
  if (days <= 7) {
    return <span className="text-[11px] font-bold text-amber-600 bg-amber-50 px-2 py-0.5 rounded-full">D-{days}</span>
  }
  if (days <= 30) {
    return <span className="text-[11px] font-semibold text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded-full">D-{days}</span>
  }
  return <span className="text-[11px] font-medium text-slate-500 bg-slate-100 px-2 py-0.5 rounded-full">D-{days}</span>
}

export default function EarningsCalendar({ ticker }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!ticker) return
    setLoading(true)
    setError(null)
    stockAPI.getEarningsCalendar(ticker)
      .then(res => setData(res.data))
      .catch(err => setError(err.response?.data?.detail || '실적 일정을 불러올 수 없습니다'))
      .finally(() => setLoading(false))
  }, [ticker])

  /* ── 로딩 ── */
  if (loading) {
    return (
      <div className="bg-white rounded-2xl border border-slate-200 p-6">
        <div className="flex items-center gap-2 mb-4">
          <div className="h-5 w-5 bg-slate-200 rounded animate-pulse" />
          <div className="h-5 w-40 bg-slate-200 rounded animate-pulse" />
        </div>
        <div className="space-y-3">
          {[1, 2, 3].map(i => (
            <div key={i} className="h-14 bg-slate-100 rounded-xl animate-pulse" />
          ))}
        </div>
      </div>
    )
  }

  /* ── 에러 ── */
  if (error) {
    return (
      <div className="bg-white rounded-2xl border border-slate-200 p-6">
        <div className="flex items-center gap-2 mb-2">
          <Calendar className="w-5 h-5 text-slate-400" />
          <h3 className="text-base font-bold text-slate-800">실적 발표 캘린더</h3>
        </div>
        <p className="text-sm text-red-500">{error}</p>
      </div>
    )
  }

  const calendar = data?.calendar || []

  /* ── 빈 상태 ── */
  if (calendar.length === 0) {
    return (
      <div className="bg-white rounded-2xl border border-slate-200 p-6">
        <div className="flex items-center gap-2 mb-4">
          <Calendar className="w-5 h-5 text-indigo-500" />
          <h3 className="text-base font-bold text-slate-800">실적 발표 캘린더</h3>
        </div>
        <div className="flex flex-col items-center justify-center py-8 text-slate-400">
          <Clock className="w-8 h-8 mb-2" />
          <p className="text-sm">예정된 실적 발표 일정이 없습니다</p>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-2xl border border-slate-200 p-6">
      {/* 헤더 */}
      <div className="flex items-center gap-2 mb-5">
        <Calendar className="w-5 h-5 text-indigo-500" />
        <h3 className="text-base font-bold text-slate-800">실적 발표 캘린더</h3>
        <span className="text-xs text-slate-400 ml-auto">{calendar.length}개 종목</span>
      </div>

      {/* 타임라인 */}
      <div className="relative">
        {/* 세로 라인 */}
        <div className="absolute left-[18px] top-2 bottom-2 w-px bg-slate-200" />

        <div className="space-y-1">
          {calendar.map((item, idx) => {
            const days = daysUntil(item.earnings_date)
            const isMain = item.is_main
            const isPast = days != null && days < 0

            return (
              <div
                key={item.ticker + idx}
                className={`
                  relative flex items-center gap-4 pl-10 pr-4 py-3 rounded-xl transition-colors
                  ${isMain
                    ? 'bg-indigo-50 border border-indigo-200'
                    : 'hover:bg-slate-50'
                  }
                  ${isPast ? 'opacity-50' : ''}
                `}
              >
                {/* 타임라인 도트 */}
                <div className={`
                  absolute left-[13px] w-[11px] h-[11px] rounded-full border-2
                  ${isMain
                    ? 'bg-indigo-500 border-indigo-300'
                    : days != null && days <= 7
                      ? 'bg-amber-400 border-amber-200'
                      : 'bg-slate-300 border-slate-200'
                  }
                `} />

                {/* 종목 정보 */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className={`text-sm font-bold ${isMain ? 'text-indigo-700' : 'text-slate-800'}`}>
                      {item.ticker}
                    </span>
                    {isMain && <Star className="w-3.5 h-3.5 text-indigo-400 fill-indigo-400" />}
                    <span className="text-xs text-slate-400 truncate" title={item.name}>{item.name}</span>
                  </div>
                  <div className="text-xs text-slate-500 mt-0.5">
                    {formatDate(item.earnings_date)}
                  </div>
                </div>

                {/* D-day */}
                <DdayBadge days={days} />
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
