import React from 'react'
import { useProject } from '../hooks/useProjects'
import { useGenerationStream } from '../hooks/useGenerationStream'
import PromptEditor from './PromptEditor'
import ClipGallery from './ClipGallery'
import StitchPanel from './StitchPanel'

interface ProjectWorkspaceProps {
  selectedProject: { projectId: string; title: string } | null
  onProjectChange: () => void
}

function ProjectWorkspace({ selectedProject, onProjectChange }: ProjectWorkspaceProps) {
  const { data: project, isLoading, error } = useProject(selectedProject?.projectId || null)
  const { events, isConnected, clearEvents } = useGenerationStream(selectedProject?.projectId || null)

  if (!selectedProject) {
    return (
      <div className="project-workspace">
        <div className="workspace-empty">
          <i className="fas fa-arrow-left fa-3x mb-4"></i>
          <h3>Select a Project</h3>
          <p>Choose a project from the sidebar to start creating your reel</p>
          <div className="features-preview">
            <div className="feature">
              <i className="fas fa-edit"></i>
              <span>Write video prompts</span>
            </div>
            <div className="feature">
              <i className="fas fa-magic"></i>
              <span>Generate AI videos</span>
            </div>
            <div className="feature">
              <i className="fas fa-film"></i>
              <span>Stitch clips together</span>
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="project-workspace">
        <div className="workspace-loading">
          <i className="fas fa-spinner fa-spin fa-2x"></i>
          <p>Loading project...</p>
        </div>
      </div>
    )
  }

  if (error || !project) {
    return (
      <div className="project-workspace">
        <div className="workspace-error">
          <i className="fas fa-exclamation-triangle fa-2x"></i>
          <h3>Error Loading Project</h3>
          <p>{error?.message || 'Project not found'}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="project-workspace">
      <div className="workspace-header">
        <h2>{project.title}</h2>
        <div className="project-config">
          <span className="config-item">
            <i className="fas fa-mobile-alt"></i>
            {project.orientation === 'portrait' ? 'Portrait' : 'Landscape'}
          </span>
          <span className="config-item">
            <i className="fas fa-clock"></i>
            {project.durationSeconds}s
          </span>
          <span className="config-item">
            <i className="fas fa-compress"></i>
            {project.compression}
          </span>
          <span className="config-item">
            <i className="fas fa-brain"></i>
            {project.model}
          </span>
          {project.audioEnabled && (
            <span className="config-item">
              <i className="fas fa-volume-up"></i>
              Audio
            </span>
          )}
        </div>
        
        {isConnected && (
          <div className="connection-status connected">
            <i className="fas fa-wifi"></i>
            <span>Connected</span>
          </div>
        )}
      </div>

      <div className="workspace-content">
        <div className="workspace-main">
          <PromptEditor
            project={project}
            events={events}
            onProjectChange={onProjectChange}
            onClearEvents={clearEvents}
          />
          
          <ClipGallery
            project={project}
            events={events}
          />
        </div>

        <div className="workspace-sidebar">
          <StitchPanel
            project={project}
            events={events}
            onProjectChange={onProjectChange}
          />
        </div>
      </div>
    </div>
  )
}

export default ProjectWorkspace