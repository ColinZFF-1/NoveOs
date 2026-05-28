import React, { createContext, useContext, useState, useEffect, useCallback, useRef, useMemo } from 'react';
import type { Project } from '@/hooks/useNovelOS';

const API_BASE = '/api/v1';

interface ProjectContextType {
  projectId: string;
  setProjectId: (id: string) => void;
  projects: Project[];
  refreshProjects: () => void;
  isLoading: boolean;
}

const ProjectContext = createContext<ProjectContextType | undefined>(undefined);

export const ProjectProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [projectId, setProjectId] = useState<string>('');
  const [projects, setProjects] = useState<Project[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const hasFetchedRef = useRef(false);
  const loadingRef = useRef(false);

  const refreshProjects = useCallback(async () => {
    if (loadingRef.current) return;
    loadingRef.current = true;
    setIsLoading(true);
    try {
      const res = await fetch(`${API_BASE}/projects`);
      if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
      const json = await res.json();
      setProjects(json.data || []);
    } catch (e) {
      console.error('Failed to load projects:', e);
    } finally {
      setIsLoading(false);
      loadingRef.current = false;
    }
  }, []);

  useEffect(() => {
    if (!hasFetchedRef.current) {
      hasFetchedRef.current = true;
      refreshProjects();
    }
  }, [refreshProjects]);

  useEffect(() => {
    if (projects.length > 0 && !projectId) {
      setProjectId(projects[0].project_id);
    }
  }, [projects, projectId]);

  const value = useMemo(
    () => ({ projectId, setProjectId, projects, refreshProjects, isLoading }),
    [projectId, projects, refreshProjects, isLoading]
  );

  return (
    <ProjectContext.Provider value={value}>
      {children}
    </ProjectContext.Provider>
  );
};

export const useProject = (): ProjectContextType => {
  const ctx = useContext(ProjectContext);
  if (!ctx) {
    throw new Error('useProject must be used within a ProjectProvider');
  }
  return ctx;
};
