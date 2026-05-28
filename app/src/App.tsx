import { Component, type ReactNode } from 'react'
import { Routes, Route } from 'react-router'
import { ThemeProvider } from 'next-themes'
import { Toaster } from '@/components/ui/sonner'
import { ProjectProvider } from '@/context/ProjectContext'
import Home from './pages/Home'

class ErrorBoundary extends Component<{ children: ReactNode }, { hasError: boolean }> {
  constructor(props: { children: ReactNode }) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError() {
    return { hasError: true }
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="h-screen flex flex-col items-center justify-center bg-apple-gray-50 text-apple-gray-900 p-8">
          <h1 className="text-xl font-bold mb-2">出错了</h1>
          <p className="text-sm text-apple-gray-400 mb-4">页面渲染失败，请刷新重试</p>
          <button onClick={() => window.location.reload()} className="apple-btn-primary">刷新页面</button>
        </div>
      )
    }
    return this.props.children
  }
}

export default function App() {
  return (
    <ThemeProvider attribute="class" defaultTheme="light" enableSystem={false}>
      <ProjectProvider>
        <ErrorBoundary>
          <Routes>
            <Route path="/" element={<Home />} />
          </Routes>
        </ErrorBoundary>
        <Toaster position="top-right" closeButton richColors />
      </ProjectProvider>
    </ThemeProvider>
  )
}
