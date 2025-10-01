import { CreateProjectPayload, ReelProject, ReelProjectSummary, ReelGenerationJob } from "./types";

const API_BASE = "/api/reel";

function getCsrfToken(): string {
  return (document.querySelector('meta[name="csrf-token"]') as HTMLMetaElement | null)?.content ?? "";
}

async function handleResponse<T extends { success: boolean; error?: { code?: string; message?: string } }>(
  response: Response
): Promise<T> {
  const data = (await response.json()) as T;

  if (!response.ok || !data?.success) {
    const errorMessage = data?.error?.message ?? `Request failed with status ${response.status}`;
    const error = new Error(errorMessage);
    (error as any).code = data?.error?.code;
    throw error;
  }

  return data;
}

export async function fetchProjects(): Promise<ReelProjectSummary[]> {
  const response = await fetch(`${API_BASE}/projects`, {
    method: "GET",
    credentials: "include",
    headers: {
      Accept: "application/json",
    },
  });

  const data = await handleResponse<{ success: boolean; projects?: ReelProjectSummary[] }>(response);
  return data.projects ?? [];
}

export async function fetchProject(projectId: string): Promise<ReelProject> {
  const response = await fetch(`${API_BASE}/projects/${projectId}`, {
    method: "GET",
    credentials: "include",
    headers: {
      Accept: "application/json",
    },
  });

  const data = await handleResponse<{ success: boolean; project: ReelProject }>(response);
  return data.project;
}

export async function createProject(payload: CreateProjectPayload): Promise<ReelProjectSummary> {
  const response = await fetch(`${API_BASE}/projects`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCsrfToken(),
      Accept: "application/json",
    },
    body: JSON.stringify(payload),
  });

  const data = await handleResponse<{ success: boolean; project: ReelProjectSummary }>(response);
  return data.project;
}

export async function renameProject(projectId: string, title: string): Promise<void> {
  await fetch(`${API_BASE}/projects/${projectId}`, {
    method: "PUT",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCsrfToken(),
      Accept: "application/json",
    },
    body: JSON.stringify({ title }),
  }).then((response) => handleResponse<{ success: boolean }>(response));
}

export async function updateProjectPrompts(projectId: string, promptList: string[]): Promise<void> {
  await fetch(`${API_BASE}/projects/${projectId}`, {
    method: "PUT",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCsrfToken(),
      Accept: "application/json",
    },
    body: JSON.stringify({ promptList }),
  }).then((response) => handleResponse<{ success: boolean }>(response));
}

export async function updateProjectOrientation(projectId: string, orientation: "portrait" | "landscape"): Promise<void> {
  await fetch(`${API_BASE}/projects/${projectId}`, {
    method: "PUT",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCsrfToken(),
      Accept: "application/json",
    },
    body: JSON.stringify({ orientation }),
  }).then((response) => handleResponse<{ success: boolean }>(response));
}

export async function deleteProject(projectId: string): Promise<void> {
  await fetch(`${API_BASE}/projects/${projectId}`, {
    method: "DELETE",
    credentials: "include",
    headers: {
      Accept: "application/json",
      "X-CSRFToken": getCsrfToken(),
    },
  }).then((response) => handleResponse<{ success: boolean }>(response));
}

export async function generateProject(projectId: string, promptList?: string[]): Promise<{
  jobId: string;
  promptCount: number;
}> {
  const response = await fetch(`${API_BASE}/projects/${projectId}/generate`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCsrfToken(),
      Accept: "application/json",
    },
    body: JSON.stringify({ promptList }),
  });

  const data = await handleResponse<{
    success: boolean;
    jobId: string;
    promptCount: number;
  }>(response);

  return { jobId: data.jobId, promptCount: data.promptCount };
}

export async function fetchGenerationJob(projectId: string, jobId: string): Promise<ReelGenerationJob> {
  const response = await fetch(`${API_BASE}/projects/${projectId}/jobs/${jobId}`, {
    method: "GET",
    credentials: "include",
    headers: {
      Accept: "application/json",
    },
  });

  const data = await handleResponse<{ success: boolean; job: ReelGenerationJob }>(response);
  return data.job;
}

export async function reconcileProject(projectId: string): Promise<{
  report: {
    projectId: string;
    originalStatus: string;
    correctedStatus: string;
    claimedClips: number;
    verifiedClips: number;
    missingClips: string[];
    action: string;
  };
}> {
  const response = await fetch(`${API_BASE}/projects/${projectId}/reconcile`, {
    method: "POST",
    credentials: "include",
    headers: {
      "X-CSRFToken": getCsrfToken(),
      Accept: "application/json",
    },
  });

  const data = await handleResponse<{
    success: boolean;
    report: any;
  }>(response);

  return { report: data.report };
}

export async function stitchProject(projectId: string): Promise<{
  jobId: string;
  clipCount: number;
}> {
  const response = await fetch(`${API_BASE}/projects/${projectId}/stitch`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCsrfToken(),
      Accept: "application/json",
    },
  });

  const data = await handleResponse<{
    success: boolean;
    jobId: string;
    clipCount: number;
  }>(response);

  return { jobId: data.jobId, clipCount: data.clipCount };
}

