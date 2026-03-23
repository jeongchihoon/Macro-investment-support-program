import { create } from 'zustand'

const useAppStore = create((set) => ({
  currentView: 'macro',          // 'macro' | 'stock' | 'portfolio'
  setView: (view) => set({ currentView: view }),

  selectedTicker: null,          // 종목 분석 탭에서 선택된 티커
  setSelectedTicker: (ticker) => set({ selectedTicker: ticker }),

  portfolioSelectedId: null,     // 포트폴리오에서 펼친 종목 id
  setPortfolioSelectedId: (id) => set({ portfolioSelectedId: id }),
}))

export default useAppStore
