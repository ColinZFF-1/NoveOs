/**
 * Vite dev-server plugin: expose local filesystem as fallback API
 */

import type { Plugin, ViteDevServer } from 'vite'
import { readFileSync, readdirSync, statSync } from 'fs'
import { join, resolve } from 'path'
import { fileURLToPath } from 'url'

const BOOKS_ROOT = resolve(fileURLToPath(import.meta.url), '..', '..', '..', 'books')

interface LocalProject {
  project_id: string
  name: string
  genre: string
  platform: string
  total_chapters: number
  total_words_target: number
  words_per_chapter: number
  base_path: string
  status: string
}

interface LocalChapter {
  chapter_num: number
  title: string | null
  word_count: number
  mode: 'PASS' | null
  created_at: string | null
  filename: string
}

function parseYamlFront(text: string): Record<string, string | number> {
  const out: Record<string, string | number> = {}
  for (const line of text.split('\n')) {
    const m = line.match(/^(\w+):\s*(.*)$/)
    if (!m) continue
    const [, k, v] = m
    const trimmed = v.trim().replace(/^["']|["']$/g, '')
    const num = Number(trimmed)
    out[k] = Number.isNaN(num) ? trimmed : num
  }
  return out
}

function countCjkChars(text: string): number {
  const matches = text.match(/[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]/g)
  return matches ? matches.length : 0
}

function scanProjects(): LocalProject[] {
  const projects: LocalProject[] = []
  try {
    const dirs = readdirSync(BOOKS_ROOT)
    for (const dir of dirs) {
      const fullPath = join(BOOKS_ROOT, dir)
      try {
        if (!statSync(fullPath).isDirectory()) continue
      } catch { continue }

      let yaml: Record<string, string | number> = {}
      try {
        const yamlPath = join(fullPath, 'book.yaml')
        const yamlText = readFileSync(yamlPath, 'utf-8')
        yaml = parseYamlFront(yamlText)
      } catch { /* no yaml */ }

      const name = (yaml.project as string) || dir
      projects.push({
        project_id: dir,
        name,
        genre: (yaml.genre as string) || '未知',
        platform: (yaml.platform as string) || 'other',
        total_chapters: (yaml.chapters_target as number) || 48,
        total_words_target: (yaml.total_words_target as number) || 216000,
        words_per_chapter: (yaml.words_per_chapter as number) || 3200,
        base_path: fullPath,
        status: 'idle',
      })
    }
  } catch (e) {
    console.error('[localFs] scanProjects error:', e)
  }
  return projects
}

function scanChapters(projectId: string): LocalChapter[] {
  const chapters: LocalChapter[] = []
  try {
    const chDir = join(BOOKS_ROOT, projectId, 'chapters')
    const files = readdirSync(chDir)
      .filter((f) => f.startsWith('第') && f.endsWith('.txt'))
      .sort((a, b) => {
        const na = Number(a.match(/\d+/)?.[0] ?? 0)
        const nb = Number(b.match(/\d+/)?.[0] ?? 0)
        return na - nb
      })

    for (const file of files) {
      const numMatch = file.match(/第(\d+)章/)
      if (!numMatch) continue
      const chapterNum = Number(numMatch[1])

      const fullPath = join(chDir, file)
      const stat = statSync(fullPath)
      const content = readFileSync(fullPath, 'utf-8')

      const firstLine = content.split('\n').find((l) => l.trim()) || ''
      const titleMatch = firstLine.match(/第\d+章[：:\s]+(.+)/)
      let title = titleMatch ? titleMatch[1].trim() : null
      // Fallback: extract from filename "第NNN章_标题.txt"
      if (!title) {
        const nameMatch = file.match(/第\d+章_(.+)\.txt$/)
        if (nameMatch) title = nameMatch[1].trim()
      }

      const wordCount = countCjkChars(content)

      chapters.push({
        chapter_num: chapterNum,
        title,
        word_count: wordCount,
        mode: 'PASS',
        created_at: stat.mtime.toISOString(),
        filename: file,
      })
    }
  } catch (e) {
    console.error('[localFs] scanChapters error:', e)
  }
  return chapters
}

export default function localFsPlugin(): Plugin {
  return {
    name: 'local-fs-api',
    configureServer(server: ViteDevServer) {
      // Use raw connect middleware without path prefix so we can handle exact matching
      server.middlewares.use((req, res, next) => {
        if (req.method !== 'GET') return next()
        const url = (req.url ?? '').split('?')[0]

        if (url === '/local-api/projects') {
          const projects = scanProjects()
          res.setHeader('Content-Type', 'application/json; charset=utf-8')
          res.end(JSON.stringify({ code: 200, data: projects }))
          return
        }

        const m = url.match(/^\/local-api\/projects\/(.+?)\/chapters$/)
        if (m) {
          const projectId = decodeURIComponent(m[1])
          const chapters = scanChapters(projectId)
          res.setHeader('Content-Type', 'application/json; charset=utf-8')
          res.end(JSON.stringify({ code: 200, data: chapters }))
          return
        }

        next()
      })
    },
  }
}
