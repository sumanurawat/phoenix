import { useEffect, useState, useCallback } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { apiService } from '../services/api'

export interface GenerationEvent {
  type: 'generation.started' | 'generation.completed' | 'generation.failed' | 'generation.job_completed' | 'stitching.started' | 'stitching.completed' | 'stitching.failed'
  data: any
}

export function useGenerationStream(projectId: string | null) {
  const [events, setEvents] = useState<GenerationEvent[]>([])
  const [isConnected, setIsConnected] = useState(false)
  const queryClient = useQueryClient()

  const clearEvents = useCallback(() => {
    setEvents([])
  }, [])

  useEffect(() => {
    if (!projectId) {
      setIsConnected(false)
      return
    }

    const eventSource = apiService.createEventSource(projectId)
    
    eventSource.onopen = () => {
      setIsConnected(true)
    }

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        const generationEvent: GenerationEvent = {
          type: event.type as GenerationEvent['type'],
          data
        }
        
        setEvents(prev => [...prev, generationEvent])

        // Update project data on completion events
        if (event.type === 'generation.job_completed' || 
            event.type === 'stitching.completed' ||
            event.type === 'generation.completed') {
          queryClient.invalidateQueries({ queryKey: ['project', projectId] })
        }
      } catch (error) {
        console.error('Error parsing SSE message:', error)
      }
    }

    // Handle specific event types
    eventSource.addEventListener('generation.started', (event) => {
      try {
        const data = JSON.parse(event.data)
        setEvents(prev => [...prev, { type: 'generation.started', data }])
      } catch (error) {
        console.error('Error parsing generation.started:', error)
      }
    })

    eventSource.addEventListener('generation.completed', (event) => {
      try {
        const data = JSON.parse(event.data)
        setEvents(prev => [...prev, { type: 'generation.completed', data }])
        queryClient.invalidateQueries({ queryKey: ['project', projectId] })
      } catch (error) {
        console.error('Error parsing generation.completed:', error)
      }
    })

    eventSource.addEventListener('generation.failed', (event) => {
      try {
        const data = JSON.parse(event.data)
        setEvents(prev => [...prev, { type: 'generation.failed', data }])
      } catch (error) {
        console.error('Error parsing generation.failed:', error)
      }
    })

    eventSource.addEventListener('generation.job_completed', (event) => {
      try {
        const data = JSON.parse(event.data)
        setEvents(prev => [...prev, { type: 'generation.job_completed', data }])
        queryClient.invalidateQueries({ queryKey: ['project', projectId] })
      } catch (error) {
        console.error('Error parsing generation.job_completed:', error)
      }
    })

    eventSource.addEventListener('stitching.started', (event) => {
      try {
        const data = JSON.parse(event.data)
        setEvents(prev => [...prev, { type: 'stitching.started', data }])
      } catch (error) {
        console.error('Error parsing stitching.started:', error)
      }
    })

    eventSource.addEventListener('stitching.completed', (event) => {
      try {
        const data = JSON.parse(event.data)
        setEvents(prev => [...prev, { type: 'stitching.completed', data }])
        queryClient.invalidateQueries({ queryKey: ['project', projectId] })
      } catch (error) {
        console.error('Error parsing stitching.completed:', error)
      }
    })

    eventSource.addEventListener('stitching.failed', (event) => {
      try {
        const data = JSON.parse(event.data)
        setEvents(prev => [...prev, { type: 'stitching.failed', data }])
      } catch (error) {
        console.error('Error parsing stitching.failed:', error)
      }
    })

    eventSource.onerror = () => {
      setIsConnected(false)
    }

    return () => {
      eventSource.close()
      setIsConnected(false)
    }
  }, [projectId, queryClient])

  return {
    events,
    isConnected,
    clearEvents
  }
}