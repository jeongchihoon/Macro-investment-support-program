import { useState, useEffect } from 'react'
import { Plus, Trash2, ChevronDown, ChevronUp, TrendingUp, TrendingDown } from 'lucide-react'
import { portfolioAPI } from '../../api/index'
import StockDetail from '../shared/StockDetail'

function AddForm({ onAdd }) {
  const [form, setForm] = useState({ ticker: '', buy_price: '', quantity: '' })
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!form.ticker || !form.buy_price || !form.quantity) return
    setLoading(true)
    try {
      await portfolioAPI.add({
        ticker: form.ticker.toUpperCase(),
        buy_price: parseFloat(form.buy_price),
        quantity: parseFloat(form.quantity),
      })
      setForm({ ticker: '', buy_price: '', quantity: '' })
      onAdd()
    } catch (err) {
      alert('추가 실패')
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex gap-2 items-end">
      {[
        { key: 'ticker',    label: '티커',    placeholder: 'AAPL' },
        { key: 'buy_price', label: '매수가 ($)', placeholder: '150.00' },
        { key: 'quantity',  label: '수량',    placeholder: '10' },
      ].map(f => (
        <div key={f.key} className="flex-1">
          <label className="text-xs text-slate-500 mb-1 block">{f.label}</label>
          <input
            type={f.key === 'ticker' ? 'text' : 'number'}
            step="any"
            value={form[f.key]}
            onChange={e => setForm(prev => ({ ...prev, [f.key]: e.target.value }))}
            placeholder={f.placeholder}
            className="w-full px-3 py-2 bg-white border border-slate-300 rounded-lg text-sm text-slate-700 placeholder-slate-400 focus:outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 transition-all"
          />
        </div>
      ))}
      <button
        type="submit"
        disabled={loading}
        className="flex items-center gap-1 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50 flex-shrink-0 shadow-sm"
      >
        <Plus size={14} />
        추가
      </button>
    </form>
  )
}

export default function PortfolioView() {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(false)
  const [expandedId, setExpandedId] = useState(null)

  const fetchPortfolio = () => {
    setLoading(true)
    portfolioAPI.getAll()
      .then(r => setItems(r.data.items || []))
      .catch(() => {})
      .finally(() => setLoading(false))
  }

  useEffect(() => { fetchPortfolio() }, [])

  const handleDelete = async (id) => {
    await portfolioAPI.remove(id)
    fetchPortfolio()
    if (expandedId === id) setExpandedId(null)
  }

  const totalInvested = items.reduce((s, i) => s + i.invested, 0)
  const totalCurrent  = items.reduce((s, i) => s + i.current_value, 0)
  const totalPL       = totalCurrent - totalInvested
  const totalPct      = totalInvested ? (totalPL / totalInvested * 100) : 0

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <div className="p-6 pb-4 border-b border-slate-200 bg-white flex-shrink-0">
        <h2 className="text-lg font-bold text-slate-800 mb-4">포트폴리오</h2>
        <AddForm onAdd={fetchPortfolio} />

        {/* 포트폴리오 요약 */}
        {items.length > 0 && (
          <div className="mt-4 grid grid-cols-3 gap-3">
            <div className="bg-slate-50 rounded-lg p-3 border border-slate-200">
              <p className="text-xs text-slate-500">총 투자금</p>
              <p className="text-base font-bold text-slate-800">${totalInvested.toLocaleString(undefined, {maximumFractionDigits: 0})}</p>
            </div>
            <div className="bg-slate-50 rounded-lg p-3 border border-slate-200">
              <p className="text-xs text-slate-500">현재 가치</p>
              <p className="text-base font-bold text-slate-800">${totalCurrent.toLocaleString(undefined, {maximumFractionDigits: 0})}</p>
            </div>
            <div className={`rounded-lg p-3 border ${totalPL >= 0 ? 'bg-emerald-50 border-emerald-200' : 'bg-red-50 border-red-200'}`}>
              <p className="text-xs text-slate-500">총 손익</p>
              <p className={`text-base font-bold ${totalPL >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                {totalPL >= 0 ? '+' : ''}{totalPL.toFixed(0)} ({totalPct.toFixed(1)}%)
              </p>
            </div>
          </div>
        )}
      </div>

      <div className="flex-1 overflow-y-auto p-6 space-y-3">
        {loading && <p className="text-slate-400 text-sm">로딩 중...</p>}
        {!loading && items.length === 0 && (
          <p className="text-slate-400 text-sm text-center py-12">보유 종목이 없습니다. 위에서 추가하세요.</p>
        )}

        {items.map(item => {
          const isExpanded = expandedId === item.id
          const isUp = item.profit_loss >= 0
          return (
            <div key={item.id} className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
              {/* 종목 헤더 행 */}
              <div className="flex items-center gap-4 p-4">
                <button
                  onClick={() => setExpandedId(isExpanded ? null : item.id)}
                  className="flex-1 flex items-center gap-4 text-left"
                >
                  <div className="w-12 h-12 rounded-lg bg-indigo-50 border border-indigo-200 flex items-center justify-center text-sm font-bold text-indigo-600">
                    {item.ticker.slice(0, 4)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-semibold text-slate-800">{item.ticker}</p>
                    <p className="text-xs text-slate-400 truncate">{item.company_name}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-semibold text-slate-800">${item.current_value.toLocaleString(undefined, {maximumFractionDigits: 0})}</p>
                    <div className={`flex items-center gap-1 justify-end text-xs ${isUp ? 'text-emerald-600' : 'text-red-500'}`}>
                      {isUp ? <TrendingUp size={11} /> : <TrendingDown size={11} />}
                      {isUp ? '+' : ''}{item.profit_loss.toFixed(0)} ({item.profit_pct.toFixed(1)}%)
                    </div>
                  </div>
                  <div className="text-right text-xs text-slate-400 ml-2">
                    <p>매수가 ${item.buy_price}</p>
                    <p>현재가 ${item.current_price?.toFixed(2)}</p>
                    <p>{item.quantity}주</p>
                  </div>
                  {isExpanded ? <ChevronUp size={16} className="text-slate-400" /> : <ChevronDown size={16} className="text-slate-400" />}
                </button>
                <button
                  onClick={() => handleDelete(item.id)}
                  className="p-2 text-slate-300 hover:text-red-500 transition-colors flex-shrink-0"
                >
                  <Trash2 size={15} />
                </button>
              </div>

              {/* 펼침: StockDetail */}
              {isExpanded && (
                <div className="border-t border-slate-200 p-4 bg-slate-50">
                  <StockDetail ticker={item.ticker} />
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
