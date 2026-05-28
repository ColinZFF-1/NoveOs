import { Routes, Route } from 'react-router'
import { ThemeProvider } from 'next-themes'
import { Toaster } from '@/components/ui/sonner'
import { ProjectProvider } from '@/context/ProjectContext'
import Home from './pages/Home'

export default function App() {
  return (
    <ThemeProvider attribute="class" defaultTheme="light" enableSystem={false}>
      <ProjectProvider>
        <Routes>
          <Route path="/" element={<Home />} />
        </Routes>
        <Toaster position="top-right" closeButton richColors />
      </ProjectProvider>
    </ThemeProvider>
  )
}
