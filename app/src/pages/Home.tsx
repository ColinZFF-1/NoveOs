import React from 'react';
import TopNav from '@/components/layout/TopNav';
import LeftPanel from '@/components/layout/LeftPanel';
import PipelineFlow from '@/components/pipeline/PipelineFlow';
import ChapterPreview from '@/components/chapter/ChapterPreview';
import EmotionCurve from '@/components/emotion/EmotionCurve';
import AuditGrid from '@/components/audit/AuditGrid';
import CharacterPanel from '@/components/character/CharacterPanel';
import LogStream from '@/components/log/LogStream';
import Footer from '@/components/layout/Footer';
import { useProject } from '@/context/ProjectContext';
import { useNovelOS } from '@/hooks/useNovelOS';

const Home: React.FC = () => {
  const { projectId } = useProject();
  const { pipeline } = useNovelOS(projectId);

  return (
    <div className="h-screen flex flex-col bg-[#F3F4F6] overflow-hidden">
      {/* Top Navigation */}
      <TopNav />

      {/* Main Content */}
      <div className="flex-1 flex gap-3 p-3 overflow-hidden">
        {/* Left Panel */}
        <LeftPanel projectId={projectId} />

        {/* Center Stage */}
        <main className="flex-1 flex flex-col gap-3 min-w-0 overflow-y-auto scrollbar-thin">
          <PipelineFlow projectId={projectId} />
          <div className="flex-1 min-h-0">
            <ChapterPreview
              projectId={projectId}
              currentChapter={pipeline?.current_step_index || 0}
              status={pipeline?.is_running ? 'writing' : (pipeline?.status || '')}
            />
          </div>
          <EmotionCurve projectId={projectId} />
          <AuditGrid projectId={projectId} />
        </main>

        {/* Right Panel */}
        <aside className="w-72 shrink-0 flex flex-col gap-3 overflow-y-auto">
          <CharacterPanel projectId={projectId} />
          <div className="flex-1 min-h-0">
            <LogStream projectId={projectId} />
          </div>
        </aside>
      </div>

      {/* Footer */}
      <Footer />
    </div>
  );
};

export default Home;
