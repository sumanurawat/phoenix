import React from 'react'
import { Project } from '../services/api'
import { GenerationEvent } from '../hooks/useGenerationStream'
import { apiService } from '../services/api'

interface ClipGalleryProps {
  project: Project
  events: GenerationEvent[]
}

function ClipGallery({ project, events }: ClipGalleryProps) {
  const { clipFilenames = [], clipUrls = [] } = project

  if (clipFilenames.length === 0) {
    return (
      <div className="clip-gallery">
        <div className="gallery-header">
          <h3>Generated Clips</h3>
          <span className="clip-count">0 clips</span>
        </div>
        
        <div className="gallery-empty">
          <i className="fas fa-film fa-3x mb-3"></i>
          <h4>No clips generated yet</h4>
          <p>Use the prompt editor above to generate video clips</p>
        </div>
      </div>
    )
  }

  const getClipStatus = (filename: string, index: number) => {
    // Check if this clip is currently being generated
    const generatingEvent = events.find(e => 
      e.type === 'generation.started' && e.data.prompt_index === index
    )
    const completedEvent = events.find(e => 
      e.type === 'generation.completed' && e.data.prompt_index === index
    )
    const failedEvent = events.find(e => 
      e.type === 'generation.failed' && e.data.prompt_index === index
    )

    if (failedEvent) return 'failed'
    if (completedEvent) return 'completed'
    if (generatingEvent) return 'generating'
    return 'ready'
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'generating': return 'fas fa-spinner fa-spin text-info'
      case 'completed': return 'fas fa-check text-success'
      case 'failed': return 'fas fa-times text-danger'
      case 'ready': return 'fas fa-film text-primary'
      default: return 'fas fa-question'
    }
  }

  const getStatusText = (status: string) => {
    switch (status) {
      case 'generating': return 'Generating...'
      case 'completed': return 'Generated'
      case 'failed': return 'Failed'
      case 'ready': return 'Ready'
      default: return 'Unknown'
    }
  }

  return (
    <div className="clip-gallery">
      <div className="gallery-header">
        <h3>Generated Clips</h3>
        <span className="clip-count">{clipFilenames.length} clips</span>
      </div>

      <div className="gallery-grid">
        {clipFilenames.map((filename, index) => {
          const status = getClipStatus(filename, index)
          const videoUrl = clipUrls[index] || apiService.getClipUrl(project.projectId, filename)
          
          return (
            <div key={filename} className={`clip-item ${status}`}>
              <div className="clip-preview">
                {status === 'generating' ? (
                  <div className="clip-placeholder generating">
                    <i className="fas fa-spinner fa-spin fa-2x"></i>
                    <p>Generating...</p>
                  </div>
                ) : status === 'failed' ? (
                  <div className="clip-placeholder failed">
                    <i className="fas fa-exclamation-triangle fa-2x"></i>
                    <p>Generation Failed</p>
                  </div>
                ) : videoUrl ? (
                  <video
                    src={videoUrl}
                    controls
                    preload="metadata"
                    className="clip-video"
                    poster=""
                  >
                    Your browser does not support video playback.
                  </video>
                ) : (
                  <div className="clip-placeholder">
                    <i className="fas fa-film fa-2x"></i>
                    <p>Loading...</p>
                  </div>
                )}
                
                <div className="clip-overlay">
                  <div className="clip-status">
                    <i className={getStatusIcon(status)}></i>
                    <span>{getStatusText(status)}</span>
                  </div>
                </div>
              </div>
              
              <div className="clip-info">
                <div className="clip-filename" title={filename}>
                  {filename}
                </div>
                <div className="clip-meta">
                  <span className="clip-index">Clip {index + 1}</span>
                  {project.promptList[index] && (
                    <div className="clip-prompt" title={project.promptList[index]}>
                      "{project.promptList[index].substring(0, 50)}..."
                    </div>
                  )}
                </div>
              </div>
              
              <div className="clip-actions">
                {videoUrl && status === 'ready' && (
                  <>
                    <button 
                      className="btn btn-sm btn-outline-primary"
                      onClick={() => window.open(videoUrl, '_blank')}
                      title="Open in new tab"
                    >
                      <i className="fas fa-external-link-alt"></i>
                    </button>
                    <button 
                      className="btn btn-sm btn-outline-secondary"
                      onClick={() => {
                        const link = document.createElement('a')
                        link.href = videoUrl
                        link.download = filename
                        link.click()
                      }}
                      title="Download"
                    >
                      <i className="fas fa-download"></i>
                    </button>
                  </>
                )}
              </div>
            </div>
          )
        })}
      </div>

      {/* Real-time generation feedback */}
      {project.status === 'generating' && (
        <div className="generation-status">
          <div className="status-header">
            <i className="fas fa-magic"></i>
            <span>Generating videos...</span>
          </div>
          <div className="status-progress">
            {events.filter(e => e.type === 'generation.started').length > 0 && (
              <div className="progress-text">
                Processing prompts with AI video generation...
              </div>
            )}
          </div>
        </div>
      )}

      {/* Error state */}
      {project.status === 'error' && project.errorInfo && (
        <div className="generation-error">
          <div className="alert alert-danger">
            <i className="fas fa-exclamation-triangle"></i>
            <strong>Generation Error:</strong> {project.errorInfo.message}
          </div>
        </div>
      )}
    </div>
  )
}

export default ClipGallery