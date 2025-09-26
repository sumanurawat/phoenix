import React, { useState } from 'react'
import { Project } from '../services/api'
import { useCreateProject, useDeleteProject } from '../hooks/useProjects'
import ProjectForm from './ProjectForm'

interface ProjectSidebarProps {
  projects: Project[]
  selectedProject: { projectId: string; title: string } | null
  onSelectProject: (project: { projectId: string; title: string } | null) => void
  onProjectsChange: () => void
}

function ProjectSidebar({ 
  projects, 
  selectedProject, 
  onSelectProject, 
  onProjectsChange 
}: ProjectSidebarProps) {
  const [showCreateForm, setShowCreateForm] = useState(false)
  const createProject = useCreateProject()
  const deleteProject = useDeleteProject()

  const handleCreateProject = async (title: string) => {
    try {
      const newProject = await createProject.mutateAsync(title)
      setShowCreateForm(false)
      onSelectProject({
        projectId: newProject.projectId,
        title: newProject.title
      })
      onProjectsChange()
    } catch (error) {
      console.error('Failed to create project:', error)
    }
  }

  const handleDeleteProject = async (projectId: string) => {
    if (window.confirm('Are you sure you want to delete this project?')) {
      try {
        await deleteProject.mutateAsync(projectId)
        if (selectedProject?.projectId === projectId) {
          onSelectProject(null)
        }
        onProjectsChange()
      } catch (error) {
        console.error('Failed to delete project:', error)
      }
    }
  }

  const getStatusBadge = (status: Project['status']) => {
    const badges = {
      draft: { class: 'badge-secondary', text: 'Draft' },
      generating: { class: 'badge-info', text: 'Generating' },
      ready: { class: 'badge-success', text: 'Ready' },
      error: { class: 'badge-danger', text: 'Error' }
    }
    const badge = badges[status] || badges.draft
    return <span className={`badge ${badge.class}`}>{badge.text}</span>
  }

  const formatDate = (dateStr: string) => {
    try {
      return new Date(dateStr).toLocaleDateString()
    } catch {
      return 'Unknown'
    }
  }

  return (
    <div className="project-sidebar">
      <div className="sidebar-header">
        <h3>Projects</h3>
        <button 
          className="btn btn-primary btn-sm"
          onClick={() => setShowCreateForm(true)}
          disabled={createProject.isPending}
        >
          <i className="fas fa-plus"></i> New Project
        </button>
      </div>

      <div className="project-list">
        {projects.length === 0 ? (
          <div className="empty-state">
            <i className="fas fa-video fa-2x mb-3"></i>
            <p>No projects yet</p>
            <p className="text-muted small">Create your first reel project</p>
          </div>
        ) : (
          projects.map((project) => (
            <div
              key={project.projectId}
              className={`project-item ${
                selectedProject?.projectId === project.projectId ? 'selected' : ''
              }`}
              onClick={() => onSelectProject({
                projectId: project.projectId,
                title: project.title
              })}
            >
              <div className="project-header">
                <h4 className="project-title">{project.title}</h4>
                <div className="project-actions">
                  <button
                    className="btn btn-sm btn-outline-danger"
                    onClick={(e) => {
                      e.stopPropagation()
                      handleDeleteProject(project.projectId)
                    }}
                    disabled={deleteProject.isPending}
                  >
                    <i className="fas fa-trash"></i>
                  </button>
                </div>
              </div>
              
              <div className="project-meta">
                <div className="project-status">
                  {getStatusBadge(project.status)}
                </div>
                <div className="project-stats">
                  <span className="stat">
                    <i className="fas fa-film"></i> {project.clipFilenames.length}
                  </span>
                  {project.stitchedFilename && (
                    <span className="stat stitched">
                      <i className="fas fa-link"></i> Stitched
                    </span>
                  )}
                </div>
              </div>
              
              <div className="project-date">
                Created: {formatDate(project.createdAt)}
              </div>
              
              {project.errorInfo && (
                <div className="project-error">
                  <i className="fas fa-exclamation-triangle"></i>
                  <span className="error-message">{project.errorInfo.message}</span>
                </div>
              )}
            </div>
          ))
        )}
      </div>

      {showCreateForm && (
        <ProjectForm
          onSubmit={handleCreateProject}
          onCancel={() => setShowCreateForm(false)}
          isSubmitting={createProject.isPending}
        />
      )}
    </div>
  )
}

export default ProjectSidebar