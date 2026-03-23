import { useState, useEffect, useRef, useCallback } from 'react'
import { Search, TrendingUp, TrendingDown, X } from 'lucide-react'
import { stockAPI } from '../../api/index'
import StockDetail from '../shared/StockDetail'

const POPULAR = ['AAPL', 'MSFT', 'NVDA', 'GOOGL', 'AMZN', 'META', 'TSLA', 'SPY', 'QQQ']

/* 프리페치: 호버 시 overview 데이터 미리 로드 */
const _prefetchedTickers = new Set()
function prefetchOverview(ticker) {
  if (_prefetchedTickers.has(ticker)) return
  _prefetchedTickers.add(ticker)
  stockAPI.getOverview(ticker).catch(() => {}) // 백그라운드 캐시 워밍
}

/* 미니 스파크라인 SVG */
function MiniSparkline({ data, positive }) {
  if (!data || data.length < 2) return null
  const min = Math.min(...data)
  const max = Math.max(...data)
  const range = max - min || 1
  const w = 60, h = 24
  const points = data.map((v, i) => {
    const x = (i / (data.length - 1)) * w
    const y = h - ((v - min) / range) * h
    return `${x},${y}`
  }).join(' ')

  return (
    <svg width={w} height={h} className="flex-shrink-0">
      <polyline
        points={points}
        fill="none"
        stroke={positive ? '#10b981' : '#ef4444'}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

export default function StockView() {
  const [query, setQuery] = useState('')
  const [ticker, setTicker] = useState(null)
  const [suggestions, setSuggestions] = useState([])
  const [showDropdown, setShowDropdown] = useState(false)
  const [loading, setLoading] = useState(false)
  const [selectedIdx, setSelectedIdx] = useState(-1)
  const inputRef = useRef(null)
  const dropdownRef = useRef(null)
  const debounceRef = useRef(null)
  const requestIdRef = useRef(0)         // 요청 시퀀스 ID (레이스 컨디션 방지)
  const enrichAbortRef = useRef(null)     // enrich 요청 취소용

  // 디바운스 검색 (250ms) — 2단계 로딩 (플리커 방지)
  const fetchSuggestions = useCallback((q) => {
    if (debounceRef.current) clearTimeout(debounceRef.current)
    if (enrichAbortRef.current) {
      enrichAbortRef.current.abort()
      enrichAbortRef.current = null
    }

    if (!q.trim() || q.trim().length < 1) {
      setSuggestions([])
      setShowDropdown(false)
      setLoading(false)
      return
    }

    setLoading(true)

    debounceRef.current = setTimeout(async () => {
      const thisRequestId = ++requestIdRef.current
      const trimmed = q.trim()

      try {
        // ── 1단계: 즉시 결과 (이름만, 차트 없음) ──
        const res = await stockAPI.suggest(trimmed, 0)
        if (thisRequestId !== requestIdRef.current) return

        const liteResults = res.data?.results || []
        if (liteResults.length === 0) {
          setSuggestions([])
          setShowDropdown(false)
          setLoading(false)
          return
        }

        // 즉시 드롭다운 표시 (가격 없이)
        setSuggestions(liteResults)
        setShowDropdown(true)
        setSelectedIdx(-1)
        setLoading(false)

        // ── 2단계: 백그라운드로 차트 데이터 보강 ──
        const enrichController = new AbortController()
        enrichAbortRef.current = enrichController
        try {
          const enrichRes = await stockAPI.suggest(trimmed, 1)
          if (enrichController.signal.aborted) return
          if (thisRequestId !== requestIdRef.current) return

          const enrichedResults = enrichRes.data?.results || []
          if (enrichedResults.length > 0) {
            // 기존 결과와 같은 종목 구성인 경우에만 업데이트 (플리커 방지)
            setSuggestions(prev => {
              const prevTickers = prev.map(s => s.ticker).join(',')
              const newTickers = enrichedResults.map(s => s.ticker).join(',')
              return prevTickers === newTickers ? enrichedResults : prev
            })
          }
        } catch {
          // enrich 실패해도 lite 결과는 유지
        }
      } catch {
        if (thisRequestId === requestIdRef.current) {
          setSuggestions(prev => prev.length > 0 ? prev : [])
          setLoading(false)
        }
      }
    }, 250)
  }, [])

  const handleInputChange = (e) => {
    const val = e.target.value
    setQuery(val)
    fetchSuggestions(val)
  }

  const selectStock = (t) => {
    // 진행 중인 요청 모두 취소
    requestIdRef.current++
    if (debounceRef.current) clearTimeout(debounceRef.current)
    if (enrichAbortRef.current) {
      enrichAbortRef.current.abort()
      enrichAbortRef.current = null
    }

    setTicker(t.toUpperCase())
    setQuery(t.toUpperCase())
    setShowDropdown(false)
    setSuggestions([])
    setLoading(false)
  }

  const handleSearch = (e) => {
    e.preventDefault()
    if (selectedIdx >= 0 && suggestions[selectedIdx]) {
      selectStock(suggestions[selectedIdx].ticker)
    } else if (query.trim()) {
      selectStock(query.trim())
    }
  }

  const handleKeyDown = (e) => {
    if (!showDropdown || suggestions.length === 0) return
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setSelectedIdx(prev => Math.min(prev + 1, suggestions.length - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setSelectedIdx(prev => Math.max(prev - 1, -1))
    } else if (e.key === 'Escape') {
      setShowDropdown(false)
    }
  }

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target) &&
          inputRef.current && !inputRef.current.contains(e.target)) {
        setShowDropdown(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // cleanup on unmount
  useEffect(() => {
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current)
      if (enrichAbortRef.current) enrichAbortRef.current.abort()
    }
  }, [])

  return (
    <div className="flex flex-col h-full overflow-hidden bg-slate-50/50">
      {/* 검색 헤더 */}
      <div className="p-6 pb-4 border-b border-slate-200 bg-white flex-shrink-0">
        <h2 className="text-lg font-extrabold text-slate-900 mb-4">종목 분석</h2>

        {/* 검색창 + 드롭다운 */}
        <div className="relative">
          <form onSubmit={handleSearch} className="flex gap-2">
            <div className="relative flex-1" ref={inputRef}>
              <Search size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                value={query}
                onChange={handleInputChange}
                onKeyDown={handleKeyDown}
                onFocus={() => { if (suggestions.length > 0) setShowDropdown(true) }}
                placeholder="종목명 또는 티커 입력 (예: Apple, NVDA, 테슬라, ㅌㅅㄹ)"
                className="w-full pl-10 pr-10 py-3 bg-slate-50 border border-slate-200 rounded-xl text-sm text-slate-700 placeholder-slate-400 focus:outline-none focus:bg-white focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100 transition-all"
                autoComplete="off"
              />
              {query && !loading && (
                <button
                  type="button"
                  onClick={() => {
                    requestIdRef.current++
                    if (debounceRef.current) clearTimeout(debounceRef.current)
                    if (enrichAbortRef.current) enrichAbortRef.current.abort()
                    setQuery('')
                    setSuggestions([])
                    setShowDropdown(false)
                  }}
                  className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                >
                  <X size={14} />
                </button>
              )}
              {loading && (
                <div className="absolute right-3.5 top-1/2 -translate-y-1/2">
                  <div className="w-4 h-4 border-2 border-indigo-400 border-t-transparent rounded-full animate-spin" />
                </div>
              )}
            </div>
            <button
              type="submit"
              className="px-6 py-3 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-sm font-semibold transition-colors shadow-sm shadow-indigo-200"
            >
              검색
            </button>
          </form>

          {/* 연관검색어 드롭다운 */}
          {showDropdown && suggestions.length > 0 && (
            <div
              ref={dropdownRef}
              className="absolute left-0 right-[88px] mt-1.5 bg-white border border-slate-200 rounded-2xl shadow-xl shadow-slate-200/60 z-50 overflow-hidden"
            >
              {suggestions.map((item, idx) => (
                <button
                  key={item.ticker}
                  onClick={() => selectStock(item.ticker)}
                  onMouseEnter={() => prefetchOverview(item.ticker)}
                  className={`w-full flex items-center gap-3 px-4 py-3.5 text-left transition-colors border-b border-slate-100 last:border-b-0 ${
                    idx === selectedIdx
                      ? 'bg-indigo-50'
                      : 'hover:bg-slate-50'
                  }`}
                >
                  {/* 티커 배지 */}
                  <div className="flex-shrink-0">
                    <span className="text-xs font-bold text-indigo-600 bg-indigo-50 border border-indigo-200 px-2.5 py-1 rounded-lg whitespace-nowrap">
                      {item.ticker}
                    </span>
                  </div>

                  {/* 기업명 + 거래소 */}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-slate-700 truncate font-medium">{item.name || item.ticker}</p>
                    <p className="text-[11px] text-slate-400 truncate">
                      {item.exchange}{item.sector ? ` · ${item.sector}` : ''}
                    </p>
                  </div>

                  {/* 미니 스파크라인 */}
                  <MiniSparkline
                    data={item.sparkline}
                    positive={(item.change_pct ?? 0) >= 0}
                  />

                  {/* 가격 + 변동률 */}
                  <div className="text-right flex-shrink-0 w-20">
                    {item.price != null ? (
                      <>
                        <p className="text-sm font-semibold text-slate-700">${item.price}</p>
                        {item.change_pct != null && (
                          <div className={`flex items-center gap-0.5 justify-end text-[11px] font-medium ${
                            item.change_pct >= 0 ? 'text-emerald-600' : 'text-red-500'
                          }`}>
                            {item.change_pct >= 0 ? <TrendingUp size={10} /> : <TrendingDown size={10} />}
                            {item.change_pct >= 0 ? '+' : ''}{item.change_pct}%
                          </div>
                        )}
                      </>
                    ) : (
                      <div className="flex items-center justify-end gap-1">
                        <div className="w-8 h-3 bg-slate-100 rounded animate-pulse" />
                      </div>
                    )}
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* 인기 종목 */}
        <div className="flex gap-2 mt-3 flex-wrap">
          {POPULAR.map(t => (
            <button
              key={t}
              onClick={() => selectStock(t)}
              onMouseEnter={() => prefetchOverview(t)}
              className={`text-xs px-3.5 py-1.5 rounded-full border font-medium transition-all ${
                ticker === t
                  ? 'bg-indigo-50 border-indigo-300 text-indigo-600 shadow-sm'
                  : 'border-slate-200 text-slate-400 hover:text-slate-600 hover:border-slate-300 hover:bg-white'
              }`}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      {/* 종목 상세 */}
      <div className="flex-1 overflow-y-auto p-6">
        <StockDetail ticker={ticker} />
      </div>
    </div>
  )
}
