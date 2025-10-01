export type ReelProjectStatus = "draft" | "generating" | "stitching" | "error" | "ready";

export interface ReelProjectSummary {
  projectId: string;
  title: string;
  orientation: "portrait" | "landscape";
  status: ReelProjectStatus;
  clipCount: number;
  hasStitchedReel: boolean;
  createdAt?: string;
  updatedAt?: string;
}

export interface ReelProject extends ReelProjectSummary {
  durationSeconds: number;
  compression: string;
  model: string;
  audioEnabled: boolean;
  promptList: string[];
  clipFilenames: string[];
  stitchedFilename?: string;
  errorInfo?: {
    code?: string;
    message?: string;
  };
}

export interface CreateProjectPayload {
  title: string;
}

export type ReelGenerationJobStatus = "queued" | "processing" | "completed" | "failed";

export interface ReelGenerationJob {
  jobId: string;
  projectId: string;
  status: ReelGenerationJobStatus;
  promptCount: number;
  completedPrompts: number;
  failedPrompts: number;
  clipRelativePaths: string[];
  error?: string | null;
  createdAt?: string;
  updatedAt?: string;
  startedAt?: string;
  completedAt?: string;
}

