import { useState, useEffect, useCallback, useMemo, useRef } from 'react';

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
  audit?: { quality_passed: boolean; sensitive_passed: boolean };
}

export interface ProjectDetail extends Project {
  pipeline_id?: string | null;
  llm?: { model?: string; reasoning_effort?: string; [key: string]: unknown };
}

async function fetchJSON<T>(url: string, opts?: RequestInit): Promise<T> {
  const res = await fetch(url, opts);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

export function useNovelOS(projectId?: string) {
  const [projects, setProjects] = useState<Project[]>([]);
  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [pipeline, setPipeline] = useState<PipelineStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const projectsLoadingRef = useRef(false);
  const projectLoadingRef = useRef(false);
  const pipelineLoadingRef = useRef(false);

  const loadProjects = useCallback(async () => {
    if (projectsLoadingRef.current) return;
    projectsLoadingRef.current = true;
    try {
      const data = await fetchJSON<{ code: number; data: Project[] }>(`${API_BASE}/projects`);
      setProjects(data.data);
    } catch (e: any) {
      setError(e.message);
    } finally {
      projectsLoadingRef.current = false;
    }
  }, []);

  const loadProject = useCallback(async () => {
    if (!projectId) return;
    if (projectLoadingRef.current) return;
    projectLoadingRef.current = true;
    try {
      const data = await fetchJSON<{ code: number; data: ProjectDetail }>(
        `${API_BASE}/projects/${encodeURIComponent(projectId)}`
      );
      setProject(data.data);
    } catch (e: any) {
      console.error('Failed to load project detail:', e);
    } finally {
      projectLoadingRef.current = false;
    }
  }, [projectId]);

  const loadPipeline = useCallback(async () => {
    if (!projectId) return;
    if (pipelineLoadingRef.current) return;
    pipelineLoadingRef.current = true;
    try {
      const data = await fetchJSON<{ code: number; data: PipelineStatus }>(
        `${API_BASE}/projects/${encodeURIComponent(projectId)}/pipeline`
      );
      setPipeline(data.data);
    } catch (e: any) {
      setError(e.message);
    } finally {
      pipelineLoadingRef.current = false;
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
    if (!projectId) {
      setProject(null);
      return;
    }
    loadProject();
  }, [loadProject, projectId]);

  useEffect(() => {
    if (!projectId) {
      setPipeline(null);
      return;
    }
    loadPipeline();
    const id = setInterval(loadPipeline, 3000);
    return () => clearInterval(id);
  }, [loadPipeline, projectId]);

  const result = useMemo(
    () => ({
      projects,
      project,
      pipeline,
      loading,
      error,
      loadProjects,
      loadProject,
      loadPipeline,
      startPipeline,
      pausePipeline,
      stopPipeline,
    }),
    [projects, project, pipeline, loading, error, loadProjects, loadProject, loadPipeline, startPipeline, pausePipeline, stopPipeline]
  );

  // 如果 projectId 为空字符串，返回默认值，避免下游组件拿到可变引用触发重渲染
  if (projectId === '') {
    return {
      projects: result.projects,
      project: null,
      pipeline: null,
      loading: false,
      error: null,
      loadProjects: result.loadProjects,
      loadProject: result.loadProject,
      loadPipeline: result.loadPipeline,
      startPipeline: result.startPipeline,
      pausePipeline: result.pausePipeline,
      stopPipeline: result.stopPipeline,
    };
  }

  return result;
}
