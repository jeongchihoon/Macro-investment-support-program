import { useState, useEffect } from 'react'
import { Newspaper, ExternalLink } from 'lucide-react'
import { stockAPI, macroAPI } from '../../api/index'

export default function NewsFeed({ ticker = null }) {
  const [articles, setArticles] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    setLoading(true)
    setError('')
    const req = ticker ? stockAPI.getNews(ticker) : macroAPI.getNews()
    req
      .then(r => {
        const data = r.data
        if (data.error) setError(data.error)
        setArticles(data.articles || [])
      })
      .catch(() => setError('뉴스를 불러올 수 없습니다.'))
      .finally(() => setLoading(false))
  }, [ticker])

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
      <h3 className="text-sm font-semibold text-slate-700 mb-3 flex items-center gap-2">
        <Newspaper size={15} className="text-slate-400" />
        {ticker ? `${ticker} 관련 뉴스` : '거시경제 뉴스'}
      </h3>

      {loading && <p className="text-slate-400 text-sm">로딩 중...</p>}
      {error && (
        <p className="text-amber-600 text-xs bg-amber-50 border border-amber-200 rounded p-2">{error}</p>
      )}

      <div className="space-y-3 max-h-80 overflow-y-auto pr-1">
        {articles.map((a, i) => (
          <a
            key={i}
            href={a.url}
            target="_blank"
            rel="noopener noreferrer"
            className="block group"
          >
            <div className="py-2 border-b border-slate-100 last:border-0 hover:border-indigo-200 transition-colors">
              <p className="text-sm text-slate-700 group-hover:text-indigo-600 leading-snug line-clamp-2 transition-colors">
                {a.title}
              </p>
              <div className="flex items-center gap-2 mt-1">
                <span className="text-xs text-slate-400">{a.source}</span>
                <span className="text-xs text-slate-300">{a.published_at?.slice(0, 10)}</span>
                <ExternalLink size={10} className="text-slate-300 ml-auto" />
              </div>
            </div>
          </a>
        ))}
        {!loading && articles.length === 0 && !error && (
          <p className="text-slate-400 text-sm">뉴스 없음</p>
        )}
      </div>
    </div>
  )
}
