import React, { useState, useEffect } from 'react'
import { Project } from '../services/api'
import { GenerationEvent } from '../hooks/useGenerationStream'
import { useGenerateVideos } from '../hooks/useProjects'

interface PromptEditorProps {
  project: Project
  events: GenerationEvent[]
  onProjectChange: () => void
  onClearEvents: () => void
}

function PromptEditor({ project, events, onProjectChange, onClearEvents }: PromptEditorProps) {
  const [promptsJson, setPromptsJson] = useState('')
  const [validatedPrompts, setValidatedPrompts] = useState<string[]>([])
  const [isValid, setIsValid] = useState(false)
  const [error, setError] = useState('')
  const generateVideos = useGenerateVideos()

  // Load existing prompts when project changes
  useEffect(() => {
    if (project.promptList.length > 0) {
      setPromptsJson(JSON.stringify(project.promptList, null, 2))
      setValidatedPrompts(project.promptList)
      setIsValid(true)
    } else {
      setPromptsJson('')
      setValidatedPrompts([])
      setIsValid(false)
    }
  }, [project.projectId, project.promptList])

  const samplePrompts = [
    "A cat playing piano in a jazz bar, cinematic lighting",
    "Slow orbital shot of a futuristic eco city at sunrise",
    "Drone flyover of terraced rice fields with morning mist"
  ]

  const validatePrompts = (jsonText: string) => {
    setError('')
    
    if (!jsonText.trim()) {
      setError('Input is empty')
      setIsValid(false)
      return
    }

    try {
      const parsed = JSON.parse(jsonText)
      
      if (!Array.isArray(parsed)) {
        setError('JSON must be an array of strings')
        setIsValid(false)
        return
      }

      if (parsed.length === 0) {
        setError('Array is empty. Provide at least one prompt.')
        setIsValid(false)
        return
      }

      if (parsed.length > 50) {
        setError(`Too many prompts (${parsed.length}). Limit to 50.`)
        setIsValid(false)
        return
      }

      for (let i = 0; i < parsed.length; i++) {
        if (typeof parsed[i] !== 'string' || !parsed[i].trim()) {
          setError(`Element at index ${i} is not a non-empty string`)
          setIsValid(false)
          return
        }
        if (parsed[i].length > 400) {
          setError(`Prompt at index ${i} exceeds 400 characters`)
          setIsValid(false)
          return
        }
      }

      setValidatedPrompts(parsed)
      setIsValid(true)
    } catch (e) {
      setError(`Invalid JSON: ${e instanceof Error ? e.message : 'Unknown error'}`)
      setIsValid(false)
    }
  }

  const handleValidate = () => {
    validatePrompts(promptsJson)
  }

  const handleGenerate = async () => {
    if (!isValid || validatedPrompts.length === 0) return

    try {
      onClearEvents()
      await generateVideos.mutateAsync({
        projectId: project.projectId,
        prompts: validatedPrompts
      })
      onProjectChange()
    } catch (error) {
      console.error('Generation failed:', error)
    }
  }

  const handleLoadSample = () => {
    setPromptsJson(JSON.stringify(samplePrompts, null, 2))
    setError('')
  }

  const handleClear = () => {
    setPromptsJson('')
    setValidatedPrompts([])
    setIsValid(false)
    setError('')
  }

  const isGenerating = project.status === 'generating'

  return (
    <div className="prompt-editor">
      <div className="editor-header">
        <h3>Prompt Editor</h3>
        <div className="editor-actions">
          <button 
            className="btn btn-outline-secondary btn-sm"
            onClick={handleLoadSample}
            disabled={isGenerating}
          >
            <i className="fas fa-paste"></i> Load Sample
          </button>
          <button 
            className="btn btn-outline-danger btn-sm"
            onClick={handleClear}
            disabled={isGenerating}
          >
            <i className="fas fa-eraser"></i> Clear
          </button>
        </div>
      </div>

      <div className="editor-content">
        <textarea
          className={`form-control prompt-textarea ${error ? 'is-invalid' : ''}`}
          value={promptsJson}
          onChange={(e) => setPromptsJson(e.target.value)}
          placeholder={`[\n  "A cat playing piano",\n  "A sunset over cyberpunk city"\n]`}
          rows={12}
          disabled={isGenerating}
        />

        {error && (
          <div className="invalid-feedback d-block">
            <strong>Invalid Input:</strong> {error}
            <br />
            <small>
              Sample Format:
              <pre className="mt-1 mb-0">
{`[
  "prompt1",
  "prompt2",
  "prompt3"
]`}
              </pre>
            </small>
          </div>
        )}

        {isValid && validatedPrompts.length > 0 && (
          <div className="alert alert-success">
            Validated {validatedPrompts.length} prompt(s). Ready for generation.
          </div>
        )}
      </div>

      <div className="editor-footer">
        <button
          className="btn btn-primary"
          onClick={handleValidate}
          disabled={isGenerating}
        >
          <i className="fas fa-check"></i> Validate & Prepare
        </button>

        {isValid && (
          <button
            className="btn btn-success"
            onClick={handleGenerate}
            disabled={!isValid || isGenerating || generateVideos.isPending}
          >
            {isGenerating ? (
              <>
                <i className="fas fa-spinner fa-spin"></i> Generating...
              </>
            ) : (
              <>
                <i className="fas fa-play"></i> Start Generation
              </>
            )}
          </button>
        )}
      </div>

      {/* Generation Progress */}
      {events.length > 0 && (
        <div className="generation-progress">
          <h5>Generation Progress</h5>
          <div className="progress-events">
            {events.map((event, index) => (
              <div key={index} className={`progress-event ${event.type.split('.')[1]}`}>
                <i className={getEventIcon(event.type)}></i>
                <span>{getEventMessage(event)}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function getEventIcon(type: string): string {
  switch (type) {
    case 'generation.started': return 'fas fa-play'
    case 'generation.completed': return 'fas fa-check text-success'
    case 'generation.failed': return 'fas fa-times text-danger'
    case 'generation.job_completed': return 'fas fa-flag-checkered text-success'
    default: return 'fas fa-info'
  }
}

function getEventMessage(event: GenerationEvent): string {
  switch (event.type) {
    case 'generation.started':
      return `Started generating prompt ${event.data.prompt_index + 1}`
    case 'generation.completed':
      return `Completed prompt ${event.data.prompt_index + 1}: ${event.data.filename}`
    case 'generation.failed':
      return `Failed prompt ${event.data.prompt_index + 1}: ${event.data.error}`
    case 'generation.job_completed':
      return `Generation job completed: ${event.data.clip_count} clips generated`
    default:
      return `${event.type}: ${JSON.stringify(event.data)}`
  }
}

export default PromptEditor