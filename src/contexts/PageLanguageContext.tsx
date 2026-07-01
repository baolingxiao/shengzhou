/* eslint-disable react-refresh/only-export-components */
import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'

export type PageLanguage = 'zh' | 'en'

type PageLanguageContextValue = {
  language: PageLanguage
  setLanguage: (language: PageLanguage) => void
}

const STORAGE_KEY = 'jarvis.pageLanguage'

const PageLanguageContext = createContext<PageLanguageContextValue>({
  language: 'zh',
  setLanguage: () => {},
})

function readInitialLanguage(): PageLanguage {
  if (typeof window === 'undefined') return 'zh'
  const raw = window.localStorage.getItem(STORAGE_KEY)
  return raw === 'en' ? 'en' : 'zh'
}

export function PageLanguageProvider({ children }: { children: ReactNode }) {
  const [language, setLanguage] = useState<PageLanguage>(readInitialLanguage)

  useEffect(() => {
    window.localStorage.setItem(STORAGE_KEY, language)
    document.documentElement.lang = language === 'zh' ? 'zh-CN' : 'en'
  }, [language])

  const value = useMemo(
    () => ({
      language,
      setLanguage,
    }),
    [language],
  )

  return <PageLanguageContext.Provider value={value}>{children}</PageLanguageContext.Provider>
}

export function usePageLanguage(): PageLanguageContextValue {
  return useContext(PageLanguageContext)
}
