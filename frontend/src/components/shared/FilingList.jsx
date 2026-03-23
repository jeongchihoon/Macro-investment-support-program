import { useState, useEffect } from 'react'
import { FileText, ExternalLink } from 'lucide-react'
import { stockAPI } from '../../api/index'

const FORM_COLORS = {
  '10-K':    'bg-blue-50 text-blue-600 border border-blue-200',
  '10-Q':    'bg-indigo-50 text-indigo-600 border border-indigo-200',
  '8-K':     'bg-amber-50 text-amber-600 border border-amber-200',
  'DEF 14A': 'bg-purple-50 text-purple-600 border border-purple-200',
  'SC 13G':  'bg-teal-50 text-teal-600 border border-teal-200',
}

export default function FilingList({ ticker }) {
  const [filings, setFilings] = useState([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!ticker) return
    setLoading(true)
    stockAPI.getFilings(ticker)
      .then(r => setFilings(r.data.filings || []))
      .catch(() => setFilings([]))
      .finally(() => setLoading(false))
  }, [ticker])

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
      <h3 className="text-sm font-semibold text-slate-700 mb-3 flex items-center gap-2">
        <FileText size={15} className="text-slate-400" />
        SEC 공시
      </h3>

      {loading ? (
        <p className="text-slate-400 text-sm">로딩 중...</p>
      ) : filings.length === 0 ? (
        <p className="text-slate-400 text-sm">공시 데이터를 불러올 수 없습니다.</p>
      ) : (
        <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
          {filings.map((f, i) => (
            <div key={i} className="flex items-center justify-between py-2 border-b border-slate-100 last:border-0">
              <div className="flex items-center gap-3 min-w-0">
                <span className={`text-xs px-2 py-0.5 rounded font-mono flex-shrink-0 ${FORM_COLORS[f.form] || 'bg-slate-100 text-slate-500'}`}>
                  {f.form}
                </span>
                <span className="text-xs text-slate-500 flex-shrink-0">{f.date}</span>
              </div>
              <a
                href={f.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-indigo-500 hover:text-indigo-700 flex-shrink-0 ml-2"
              >
                <ExternalLink size={13} />
              </a>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
