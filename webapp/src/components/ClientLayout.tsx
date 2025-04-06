'use client';

import { ThemeProvider } from '@/context/ThemeContext'
import Header from '@/components/Header'

export default function ClientLayout({ children }: { children: React.ReactNode }) {
  return (
    <ThemeProvider>
      <div className="min-h-full">
        <Header />
        <main>
          {children}
        </main>
      </div>
    </ThemeProvider>
  )
} 