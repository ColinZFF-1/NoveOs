import React from 'react';
import TopNav from '@/components/layout/TopNav';
import LeftPanel from '@/components/layout/LeftPanel';
import PipelineFlow from '@/components/pipeline/PipelineFlow';
import ChapterPreview from '@/components/chapter/ChapterPreview';
import WritingPreview from '@/components/writing/WritingPreview';
import EmotionCurve from '@/components/emotion/EmotionCurve';
import AuditGrid from '@/components/audit/AuditGrid';
import CharacterPanel from '@/components/character/CharacterPanel';
import LogStream from '@/components/log/LogStream';
import Footer from '@/components/layout/Footer';
import { useProject } from '@/context/ProjectContext';
import { useNovelOS } from '@/hooks/useNovelOS';
import { useWebSocket } from '@/hooks/useWebSocket';

const Home: React.FC = () => {
  const { projectId } = useProject();
  const { pipeline } = useNovelOS(projectId);
  const { events } = useWebSocket();

  const status = pipeline?.is_running ? 'writing' : (pipeline?.status || '');
  const currentChapter = pipeline?.current_step_index || 0;

  return (
    <div className="h-screen flex flex-col bg-apple-gray-50 overflow-hidden">
      {/* Top Navigation - Glassmorphism */}
      <TopNav />

      {/* Main Content */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-[240px_1fr] xl:grid-cols-[240px_1fr_288px] gap-4 p-4 overflow-hidden">
        {/* Left Panel */}
        <div className="hidden lg:flex flex-col overflow-hidden">
          <LeftPanel projectId={projectId} />
        </div>

        {/* Center Stage */}
        <main className="flex flex-col gap-4 min-w-0 overflow-hidden">
          <div className="flex-1 overflow-y-auto scrollbar-thin flex flex-col gap-4">
            <PipelineFlow projectId={projectId} />
            <WritingPreview
              projectId={projectId}
              currentChapter={currentChapter}
              status={status}
              events={events}
            />
            <div className="flex-1 min-h-0 overflow-hidden">
              <ChapterPreview
                projectId={projectId}
                currentChapter={currentChapter}
                status={status}
              />
            </div>
            <EmotionCurve projectId={projectId} />
            <AuditGrid projectId={projectId} />
          </div>
        </main>

        {/* Right Panel */}
        <aside className="hidden xl:flex flex-col gap-4 overflow-hidden">
          <div className="flex-1 flex flex-col gap-4 overflow-y-auto scrollbar-thin">
            <CharacterPanel projectId={projectId} />
            <div className="flex-1 min-h-0">
              <LogStream projectId={projectId} />
            </div>
          </div>
        </aside>
      </div>

      {/* Footer */}
      <Footer />
    </div>
  );
};

export default Home;
