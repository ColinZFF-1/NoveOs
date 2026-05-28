import { useState, useEffect, useCallback } from 'react';

const API_BASE = '/api/v1';

export interface Project {
  project_id: string;
  name: string;
  genre: string;
  platform: string;
  status: string;
  current_chapter: number;
  total_chapters: number;
}

export interface PipelineStatus {
  pipeline_id: string | null;
  status: string;
  current_step_index: number;
  can_start: boolean;
  is_running: boolean;
}

async function fetchJSON<T>(url: string, opts?: RequestInit): Promise<T> {
  const res = await fetch(url, opts);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

export function useNovelOS(projectId?: string) {
  const [projects, setProjects] = useState<Project[]>([]);
  const [pipeline, setPipeline] = useState<PipelineStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadProjects = useCallback(async () => {
    try {
      const data = await fetchJSON<{ code: number; data: Project[] }>(`${API_BASE}/projects`);
      setProjects(data.data);
    } catch (e: any) {
      setError(e.message);
    }
  }, []);

  const loadPipeline = useCallback(async () => {
    if (!projectId) return;
    try {
      const data = await fetchJSON<{ code: number; data: PipelineStatus }>(
        `${API_BASE}/projects/${encodeURIComponent(projectId)}/pipeline`
      );
      setPipeline(data.data);
    } catch (e: any) {
      setError(e.message);
    }
  }, [projectId]);

  const startPipeline = useCallback(
    async (range: string, resume = false) => {
      if (!projectId) return;
      setLoading(true);
      setError(null);
      try {
        await fetchJSON(`${API_BASE}/projects/${encodeURIComponent(projectId)}/pipeline/start`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ chapter_range: range, resume }),
        });
        await loadPipeline();
      } catch (e: any) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    },
    [projectId, loadPipeline]
  );

  const pausePipeline = useCallback(async () => {
    if (!projectId) return;
    await fetchJSON(`${API_BASE}/projects/${encodeURIComponent(projectId)}/pipeline/pause`, {
      method: 'POST',
    });
    await loadPipeline();
  }, [projectId, loadPipeline]);

  const stopPipeline = useCallback(async () => {
    if (!projectId) return;
    await fetchJSON(`${API_BASE}/projects/${encodeURIComponent(projectId)}/pipeline/stop`, {
      method: 'POST',
    });
    await loadPipeline();
  }, [projectId, loadPipeline]);

  useEffect(() => {
    loadProjects();
  }, [loadProjects]);

  useEffect(() => {
    loadPipeline();
    const id = setInterval(loadPipeline, 3000);
    return () => clearInterval(id);
  }, [loadPipeline]);

  return {
    projects,
    pipeline,
    loading,
    error,
    loadProjects,
    loadPipeline,
    startPipeline,
    pausePipeline,
    stopPipeline,
  };
}
