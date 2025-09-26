import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiService, Project } from '../services/api'

export function useProjects() {
  return useQuery({
    queryKey: ['projects'],
    queryFn: () => apiService.listProjects()
  })
}

export function useProject(projectId: string | null) {
  return useQuery({
    queryKey: ['project', projectId],
    queryFn: () => projectId ? apiService.getProject(projectId) : null,
    enabled: !!projectId
  })
}

export function useCreateProject() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: (title: string) => apiService.createProject(title),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] })
    }
  })
}

export function useUpdateProject() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: ({ 
      projectId, 
      updates 
    }: { 
      projectId: string
      updates: Partial<Pick<Project, 'title' | 'orientation' | 'audioEnabled'>>
    }) => apiService.updateProject(projectId, updates),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['projects'] })
      queryClient.setQueryData(['project', data.projectId], data)
    }
  })
}

export function useDeleteProject() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: (projectId: string) => apiService.deleteProject(projectId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] })
    }
  })
}

export function useGenerateVideos() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: ({ 
      projectId, 
      prompts 
    }: { 
      projectId: string
      prompts: string[]
    }) => apiService.generateVideos(projectId, prompts),
    onSuccess: (data, variables) => {
      // Refresh project data after starting generation
      queryClient.invalidateQueries({ queryKey: ['project', variables.projectId] })
    }
  })
}

export function useStitchVideos() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: (projectId: string) => apiService.stitchVideos(projectId),
    onSuccess: (data, projectId) => {
      // Refresh project data after starting stitching
      queryClient.invalidateQueries({ queryKey: ['project', projectId] })
    }
  })
}