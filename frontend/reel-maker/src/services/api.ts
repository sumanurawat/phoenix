export interface Project {
  projectId: string
  title: string
  orientation: 'portrait' | 'landscape'
  durationSeconds: number
  compression: string
  model: string
  audioEnabled: boolean
  promptList: string[]
  clipFilenames: string[]
  stitchedFilename: string | null
  status: 'draft' | 'generating' | 'error' | 'ready'
  errorInfo?: {
    code: string
    message: string
  }
  createdAt: string
  updatedAt: string
  clipUrls?: string[]
  stitchedUrl?: string
}

export interface ApiResponse<T> {
  success: boolean
  data?: T
  error?: string
}

class ApiService {
  private baseUrl = '/api/reel'

  private async getCsrfToken(): Promise<string> {
    try {
      const response = await fetch('/api/csrf-token')
      const data = await response.json()
      return data.csrf_token || ''
    } catch (error) {
      console.warn('Failed to get CSRF token:', error)
      return ''
    }
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`
    
    const defaultHeaders: HeadersInit = {
      'Content-Type': 'application/json'
    }

    // Add CSRF token for mutating operations
    if (['POST', 'PUT', 'DELETE'].includes(options.method || 'GET')) {
      const csrfToken = await this.getCsrfToken()
      if (csrfToken) {
        defaultHeaders['X-CSRFToken'] = csrfToken
      }
    }

    const response = await fetch(url, {
      ...options,
      headers: {
        ...defaultHeaders,
        ...options.headers
      }
    })

    if (!response.ok) {
      if (response.status === 401) {
        window.location.href = '/login'
        throw new Error('Authentication required')
      }
      
      let errorMessage = `HTTP ${response.status}`
      try {
        const errorData = await response.json()
        errorMessage = errorData.error || errorMessage
      } catch {
        // Ignore JSON parsing errors
      }
      
      throw new Error(errorMessage)
    }

    return response.json()
  }

  // Project CRUD operations
  async listProjects(): Promise<Project[]> {
    const response = await this.request<{ projects: Project[] }>('/projects')
    return response.projects || []
  }

  async createProject(title: string): Promise<Project> {
    const response = await this.request<{ project: Project }>('/projects', {
      method: 'POST',
      body: JSON.stringify({ title })
    })
    return response.project
  }

  async getProject(projectId: string): Promise<Project> {
    const response = await this.request<{ project: Project }>(`/projects/${projectId}`)
    return response.project
  }

  async updateProject(
    projectId: string,
    updates: Partial<Pick<Project, 'title' | 'orientation' | 'audioEnabled'>>
  ): Promise<Project> {
    const response = await this.request<{ project: Project }>(`/projects/${projectId}`, {
      method: 'PUT',
      body: JSON.stringify(updates)
    })
    return response.project
  }

  async deleteProject(projectId: string): Promise<void> {
    await this.request(`/projects/${projectId}`, {
      method: 'DELETE'
    })
  }

  // Video generation operations
  async generateVideos(projectId: string, prompts: string[]): Promise<{ job_id: string; message: string }> {
    const response = await this.request<{ job_id: string; message: string }>(`/projects/${projectId}/generate`, {
      method: 'POST',
      body: JSON.stringify({ prompts })
    })
    return response
  }

  async stitchVideos(projectId: string): Promise<{ job_id: string; message: string }> {
    const response = await this.request<{ job_id: string; message: string }>(`/projects/${projectId}/stitch`, {
      method: 'POST'
    })
    return response
  }

  // Server-Sent Events for real-time updates
  createEventSource(projectId: string): EventSource {
    return new EventSource(`${this.baseUrl}/projects/${projectId}/status/stream`)
  }

  // Clip access
  getClipUrl(projectId: string, filename: string): string {
    return `${this.baseUrl}/projects/${projectId}/clips/${filename}`
  }
}

export const apiService = new ApiService()