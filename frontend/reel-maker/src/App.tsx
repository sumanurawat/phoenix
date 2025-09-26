import React, { useState } from 'react'
import ProjectSidebar from './components/ProjectSidebar'
import ProjectWorkspace from './components/ProjectWorkspace'
import { useProjects } from './hooks/useProjects'

interface SelectedProject {
  projectId: string
  title: string
}

function App() {
  const [selectedProject, setSelectedProject] = useState<SelectedProject | null>(null)
  const { data: projects, isLoading, error, refetch } = useProjects()

  if (isLoading) {
    return (
      <div className="reel-maker-container">
        <div className="loading-state">
          <i className="fas fa-spinner fa-spin"></i>
          <p>Loading projects...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="reel-maker-container">
        <div className="error-state">
          <i className="fas fa-exclamation-triangle"></i>
          <p>Error loading projects: {error.message}</p>
          <button onClick={() => refetch()} className="btn btn-primary">
            Try Again
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="reel-maker-container">
      <div className="reel-maker-layout">
        <ProjectSidebar
          projects={projects || []}
          selectedProject={selectedProject}
          onSelectProject={setSelectedProject}
          onProjectsChange={refetch}
        />
        <ProjectWorkspace
          selectedProject={selectedProject}
          onProjectChange={refetch}
        />
      </div>
    </div>
  )
}

export default App