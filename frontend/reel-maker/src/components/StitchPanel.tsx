import React from 'react'
import { Project } from '../services/api'
import { GenerationEvent } from '../hooks/useGenerationStream'
import { useStitchVideos } from '../hooks/useProjects'

interface StitchPanelProps {
  project: Project
  events: GenerationEvent[]
  onProjectChange: () => void
}

function StitchPanel({ project, events, onProjectChange }: StitchPanelProps) {
  const stitchVideos = useStitchVideos()
  
  const { clipFilenames = [], stitchedFilename, stitchedUrl } = project
  const canStitch = clipFilenames.length >= 2 && project.status !== 'generating'
  
  const isStitching = events.some(e => e.type === 'stitching.started')
  const stitchCompleted = events.some(e => e.type === 'stitching.completed')
  const stitchFailed = events.find(e => e.type === 'stitching.failed')

  const handleStitch = async () => {
    try {
      await stitchVideos.mutateAsync(project.projectId)
      onProjectChange()
    } catch (error) {
      console.error('Stitching failed:', error)
    }
  }

  const getStitchStatus = () => {
    if (stitchFailed) return 'failed'
    if (isStitching) return 'stitching'
    if (stitchedFilename || stitchCompleted) return 'completed'
    return 'none'
  }

  const stitchStatus = getStitchStatus()

  return (
    <div className="stitch-panel">
      <div className="panel-header">
        <h3>Stitch Reel</h3>
        <div className="stitch-info">
          <i className="fas fa-info-circle"></i>
          <span>Combine clips into a single reel</span>
        </div>
      </div>

      <div className="panel-content">
        {/* Requirements Check */}
        <div className="requirements-check">
          <div className={`requirement ${clipFilenames.length >= 2 ? 'met' : 'unmet'}`}>
            <i className={`fas ${clipFilenames.length >= 2 ? 'fa-check' : 'fa-times'}`}></i>
            <span>At least 2 clips ({clipFilenames.length} available)</span>
          </div>
          <div className={`requirement ${project.status !== 'generating' ? 'met' : 'unmet'}`}>
            <i className={`fas ${project.status !== 'generating' ? 'fa-check' : 'fa-times'}`}></i>
            <span>Generation completed</span>
          </div>
        </div>

        {/* Stitch Button */}
        <div className="stitch-controls">
          <button
            className={`btn btn-lg ${canStitch ? 'btn-primary' : 'btn-secondary'}`}
            onClick={handleStitch}
            disabled={!canStitch || isStitching || stitchVideos.isPending}
            title={!canStitch ? 'Need at least 2 clips to stitch' : 'Stitch clips into reel'}
          >
            {isStitching ? (
              <>
                <i className="fas fa-spinner fa-spin"></i>
                Stitching...
              </>
            ) : (
              <>
                <i className="fas fa-link"></i>
                Stitch Reel
              </>
            )}
          </button>
        </div>

        {/* Stitching Status */}
        {stitchStatus !== 'none' && (
          <div className="stitch-status">
            {stitchStatus === 'stitching' && (
              <div className="status-item stitching">
                <i className="fas fa-cog fa-spin"></i>
                <div className="status-text">
                  <strong>Stitching in progress...</strong>
                  <small>This may take a few minutes</small>
                </div>
              </div>
            )}

            {stitchStatus === 'completed' && stitchedFilename && (
              <div className="status-item completed">
                <i className="fas fa-check-circle text-success"></i>
                <div className="status-text">
                  <strong>Reel stitched successfully!</strong>
                  <small>{stitchedFilename}</small>
                </div>
              </div>
            )}

            {stitchStatus === 'failed' && stitchFailed && (
              <div className="status-item failed">
                <i className="fas fa-exclamation-triangle text-danger"></i>
                <div className="status-text">
                  <strong>Stitching failed</strong>
                  <small>{stitchFailed.data.error}</small>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Stitched Video Preview */}
        {stitchedUrl && (
          <div className="stitched-preview">
            <h4>Final Reel</h4>
            <div className="video-container">
              <video
                src={stitchedUrl}
                controls
                preload="metadata"
                className="stitched-video"
              >
                Your browser does not support video playback.
              </video>
            </div>
            <div className="video-actions">
              <button
                className="btn btn-outline-primary"
                onClick={() => window.open(stitchedUrl, '_blank')}
              >
                <i className="fas fa-external-link-alt"></i>
                Open Full Screen
              </button>
              <button
                className="btn btn-outline-secondary"
                onClick={() => {
                  const link = document.createElement('a')
                  link.href = stitchedUrl
                  link.download = stitchedFilename || 'reel.mp4'
                  link.click()
                }}
              >
                <i className="fas fa-download"></i>
                Download
              </button>
            </div>
          </div>
        )}

        {/* Stitching Progress Events */}
        {events.filter(e => e.type.startsWith('stitching.')).length > 0 && (
          <div className="stitch-progress">
            <h5>Stitching Progress</h5>
            <div className="progress-events">
              {events
                .filter(e => e.type.startsWith('stitching.'))
                .map((event, index) => (
                  <div key={index} className={`progress-event ${event.type.split('.')[1]}`}>
                    <i className={getStitchEventIcon(event.type)}></i>
                    <span>{getStitchEventMessage(event)}</span>
                  </div>
                ))}
            </div>
          </div>
        )}

        {/* Tips */}
        <div className="stitch-tips">
          <h5>Tips</h5>
          <ul>
            <li>Clips will be stitched in the order they were generated</li>
            <li>All clips will be normalized to match the first clip's properties</li>
            <li>The final reel will maintain your project's audio settings</li>
            <li>Stitching typically takes 1-3 minutes depending on clip count</li>
          </ul>
        </div>
      </div>
    </div>
  )
}

function getStitchEventIcon(type: string): string {
  switch (type) {
    case 'stitching.started': return 'fas fa-play text-info'
    case 'stitching.completed': return 'fas fa-check text-success'
    case 'stitching.failed': return 'fas fa-times text-danger'
    default: return 'fas fa-info'
  }
}

function getStitchEventMessage(event: GenerationEvent): string {
  switch (event.type) {
    case 'stitching.started':
      return `Started stitching ${event.data.clip_count} clips`
    case 'stitching.completed':
      return `Stitching completed: ${event.data.filename}`
    case 'stitching.failed':
      return `Stitching failed: ${event.data.error}`
    default:
      return `${event.type}: ${JSON.stringify(event.data)}`
  }
}

export default StitchPanel