import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  createProject,
  fetchProject,
  fetchProjects,
  fetchActiveStitchJob,
  generateProject,
  reconcileProject,
  renameProject,
  stitchProject,
  updateProjectPrompts,
  updateProjectOrientation,
} from "./api";
import { ProjectList } from "./components/ProjectList";
import { ProjectSummary } from "./components/ProjectSummary";
import { PromptPanel } from "./components/PromptPanel";
import { SceneList } from "./components/SceneList";
import { StitchPanel } from "./components/StitchPanel";
import { ActionToolbar } from "./components/ActionToolbar";
import { ReelGenerationJob, ReelProject, ReelProjectSummary } from "./types";

const mergeClipPaths = (existing: string[], incoming: string[]): string[] => {
  const next = new Set(existing ?? []);
  incoming.forEach((item) => {
    if (item) {
      next.add(item);
    }
  });
  return Array.from(next);
};

export default function App() {
  const [projects, setProjects] = useState<ReelProjectSummary[]>([]);
  const [activeProjectId, setActiveProjectId] = useState<string | null>(null);
  const [activeProject, setActiveProject] = useState<ReelProject | null>(null);
  const [listLoading, setListLoading] = useState(true);
  const [projectLoading, setProjectLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const [generationJob, setGenerationJob] = useState<ReelGenerationJob | null>(null);
  const [isStartingGeneration, setIsStartingGeneration] = useState(false);
  const [hasAutoStitched, setHasAutoStitched] = useState(false);
  const autoStitchAttemptedRef = useRef(false);
  const [stitchingJob, setStitchingJob] = useState<{ projectId: string; jobId: string } | null>(null);
  const stitchingJobFetchRef = useRef<string | null>(null);

  const syncProjectSummary = useCallback(
    (projectId: string, updates: Partial<ReelProjectSummary>) => {
      setProjects((prev) =>
        prev.map((project) => (project.projectId === projectId ? { ...project, ...updates } : project))
      );
    },
    []
  );

  const loadProjects = useCallback(async () => {
    setListLoading(true);
    setErrorMessage(null);
    try {
      const fetchedProjects = await fetchProjects();
      setProjects(fetchedProjects);

      if (!fetchedProjects.length) {
        setActiveProjectId(null);
        setActiveProject(null);
        return;
      }

      setActiveProjectId((current) => {
        if (current && fetchedProjects.some((project) => project.projectId === current)) {
          return current;
        }
        return fetchedProjects[0].projectId;
      });
    } catch (error) {
      console.error("Failed to load projects", error);
      setErrorMessage((error as Error).message ?? "Unable to load projects");
    } finally {
      setListLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadProjects();
  }, [loadProjects]);

  useEffect(() => {
    if (!activeProjectId) {
      setActiveProject(null);
      return;
    }

    let cancelled = false;
    setProjectLoading(true);
    setErrorMessage(null);

    // Load project and auto-reconcile if needed
    const loadAndReconcile = async () => {
      try {
        // First fetch the project
        const project = await fetchProject(activeProjectId);
        
        // Auto-reconcile if project is stuck in "generating" or has claimed clips
        // This verifies clips exist in GCS and corrects status
        const needsReconciliation = 
          project.status === "generating" || 
          (project.clipFilenames?.length ?? 0) > 0;
        
        if (needsReconciliation) {
          console.log(`Auto-reconciling project ${activeProjectId} (status: ${project.status})`);
          
          try {
            const { report } = await reconcileProject(activeProjectId);
            
            if (report.action === "corrected") {
              console.log("Project state corrected:", {
                status: `${report.originalStatus} → ${report.correctedStatus}`,
                clips: `${report.claimedClips} → ${report.verifiedClips}`,
                missing: report.missingClips.length
              });
              
              // Refetch to get updated state after reconciliation
              const updated = await fetchProject(activeProjectId);
              if (!cancelled) {
                const normalized: ReelProject = {
                  ...updated,
                  promptList: updated.promptList ?? [],
                  clipFilenames: updated.clipFilenames ?? [],
                };
                setActiveProject(normalized);
                setGenerationJob((prev) =>
                  prev && prev.projectId === normalized.projectId && normalized.status === "generating" ? prev : null
                );
              }
            } else {
              // No corrections needed, use original project
              if (!cancelled) {
                const normalized: ReelProject = {
                  ...project,
                  promptList: project.promptList ?? [],
                  clipFilenames: project.clipFilenames ?? [],
                };
                setActiveProject(normalized);
                setGenerationJob((prev) =>
                  prev && prev.projectId === normalized.projectId && normalized.status === "generating" ? prev : null
                );
              }
            }
          } catch (reconcileError) {
            // If reconciliation fails, still show the project
            console.warn("Reconciliation failed, using project as-is:", reconcileError);
            if (!cancelled) {
              const normalized: ReelProject = {
                ...project,
                promptList: project.promptList ?? [],
                clipFilenames: project.clipFilenames ?? [],
              };
              setActiveProject(normalized);
              setGenerationJob((prev) =>
                prev && prev.projectId === normalized.projectId && normalized.status === "generating" ? prev : null
              );
            }
          }
        } else {
          // No reconciliation needed
          if (!cancelled) {
            const normalized: ReelProject = {
              ...project,
              promptList: project.promptList ?? [],
              clipFilenames: project.clipFilenames ?? [],
            };
            setActiveProject(normalized);
            setGenerationJob((prev) =>
              prev && prev.projectId === normalized.projectId && normalized.status === "generating" ? prev : null
            );
          }
        }
      } catch (error) {
        console.error("Failed to load project", error);
        if (!cancelled) {
          setErrorMessage((error as Error).message ?? "Unable to load project");
          setActiveProject(null);
        }
      } finally {
        if (!cancelled) {
          setProjectLoading(false);
        }
      }
    };

    void loadAndReconcile();

    return () => {
      cancelled = true;
    };
  }, [activeProjectId]);

  useEffect(() => {
    if (!activeProjectId) {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
      setGenerationJob(null);
      return;
    }

    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }

    const source = new EventSource(`/api/reel/projects/${activeProjectId}/events`);
    eventSourceRef.current = source;

    const parsePayload = (event: MessageEvent): Record<string, any> | null => {
      try {
        return JSON.parse(event.data ?? "{}");
      } catch (error) {
        console.error("Failed to parse reel event payload", error);
        return null;
      }
    };

    const handleJobAccepted = (event: MessageEvent) => {
      const data = parsePayload(event);
      if (!data) {
        return;
      }

      setGenerationJob({
        jobId: data.jobId,
        projectId: activeProjectId,
        status: "processing",
        promptCount: data.promptCount ?? 0,
        completedPrompts: 0,
        failedPrompts: 0,
        clipRelativePaths: [],
        error: null,
        createdAt: data.createdAt,
        updatedAt: data.updatedAt,
      });

      let nextClipCount: number | null = null;
      setActiveProject((prev) => {
        if (!prev || prev.projectId !== activeProjectId) {
          return prev;
        }
        nextClipCount = 0;
        return {
          ...prev,
          status: "generating",
          clipFilenames: [],
          stitchedFilename: undefined,
          errorInfo: undefined,
        };
      });

      if (nextClipCount !== null) {
        syncProjectSummary(activeProjectId, {
          status: "generating",
          clipCount: nextClipCount,
          hasStitchedReel: false,
        });
      }

      setErrorMessage(null);
    };

    const handlePromptCompleted = (event: MessageEvent) => {
      const data = parsePayload(event);
      if (!data) {
        return;
      }
      const clipRelativePaths: string[] = Array.isArray(data.clipRelativePaths) ? data.clipRelativePaths : [];

      setGenerationJob((prev) => {
        if (!prev || prev.projectId !== activeProjectId) {
          return prev;
        }
        const completedPrompts = typeof data.promptIndex === "number" ? Math.max(prev.completedPrompts, data.promptIndex + 1) : prev.completedPrompts + 1;
        return {
          ...prev,
          status: "processing",
          completedPrompts,
          clipRelativePaths: mergeClipPaths(prev.clipRelativePaths, clipRelativePaths),
        };
      });

      let nextClipCount: number | null = null;
      setActiveProject((prev) => {
        if (!prev || prev.projectId !== activeProjectId) {
          return prev;
        }
        const updatedClips = mergeClipPaths(prev.clipFilenames ?? [], clipRelativePaths);
        nextClipCount = updatedClips.length;
        return {
          ...prev,
          status: "generating",
          clipFilenames: updatedClips,
          errorInfo: undefined,
        };
      });

      if (nextClipCount !== null) {
        syncProjectSummary(activeProjectId, {
          status: "generating",
          clipCount: nextClipCount,
          hasStitchedReel: false,
        });
      }
    };

    const handlePromptFailed = (event: MessageEvent) => {
      const data = parsePayload(event);
      if (!data) {
        return;
      }
      const error = data.error ?? "Generation failed";
      setErrorMessage(error);
    };

    const handleJobCompleted = (event: MessageEvent) => {
      const data = parsePayload(event);
      if (!data) {
        return;
      }
      const clipRelativePaths: string[] = Array.isArray(data.clipRelativePaths) ? data.clipRelativePaths : [];

      setGenerationJob((prev) => {
        if (!prev || prev.projectId !== activeProjectId) {
          return prev;
        }
        return {
          ...prev,
          status: "completed",
          completedPrompts: data.completedPrompts ?? prev.completedPrompts,
          clipRelativePaths,
          error: null,
          completedAt: data.completedAt,
          updatedAt: data.updatedAt,
        };
      });

      let nextClipCount: number | null = null;
      setActiveProject((prev) => {
        if (!prev || prev.projectId !== activeProjectId) {
          return prev;
        }
        const updatedClips = clipRelativePaths.length ? clipRelativePaths : prev.clipFilenames ?? [];
        nextClipCount = updatedClips.length;
        return {
          ...prev,
          status: "ready",
          clipFilenames: updatedClips,
          errorInfo: undefined,
        };
      });

      if (nextClipCount !== null) {
        syncProjectSummary(activeProjectId, {
          status: "ready",
          clipCount: nextClipCount,
          hasStitchedReel: false,
        });
      }
    };

    const handleJobFailed = (event: MessageEvent) => {
      const data = parsePayload(event);
      if (!data) {
        return;
      }
      const errorMessageText = data.error ?? "Generation failed";

      setGenerationJob((prev) => {
        if (!prev || prev.projectId !== activeProjectId) {
          return prev;
        }
        return {
          ...prev,
          status: "failed",
          failedPrompts: data.failedPrompts ?? prev.failedPrompts,
          completedPrompts: data.completedPrompts ?? prev.completedPrompts,
          error: errorMessageText,
          updatedAt: data.updatedAt,
        };
      });

      setActiveProject((prev) => {
        if (!prev || prev.projectId !== activeProjectId) {
          return prev;
        }
        return {
          ...prev,
          status: "error",
          errorInfo: { message: errorMessageText },
        };
      });

      syncProjectSummary(activeProjectId, {
        status: "error",
      });

      setErrorMessage(errorMessageText);
    };

    source.addEventListener("job.accepted", handleJobAccepted);
    source.addEventListener("prompt.completed", handlePromptCompleted);
    source.addEventListener("prompt.failed", handlePromptFailed);
    source.addEventListener("job.completed", handleJobCompleted);
    source.addEventListener("job.failed", handleJobFailed);

    source.onerror = (error) => {
      console.error("Reel Maker SSE connection error", error);
    };

    return () => {
      source.removeEventListener("job.accepted", handleJobAccepted);
      source.removeEventListener("prompt.completed", handlePromptCompleted);
      source.removeEventListener("prompt.failed", handlePromptFailed);
      source.removeEventListener("job.completed", handleJobCompleted);
      source.removeEventListener("job.failed", handleJobFailed);
      source.close();
      if (eventSourceRef.current === source) {
        eventSourceRef.current = null;
      }
    };
  }, [activeProjectId, syncProjectSummary]);

  const handleCreateProject = useCallback(async () => {
    const defaultTitle = "Untitled reel";
    const title = window.prompt("New project name", defaultTitle);

    if (!title) {
      return;
    }

    setErrorMessage(null);
    try {
      const newProject = await createProject({ title: title.trim() });
      setProjects((prev) => [newProject, ...prev]);
      setActiveProjectId(newProject.projectId);
    } catch (error) {
      console.error("Failed to create project", error);
      setErrorMessage((error as Error).message ?? "Unable to create project");
    }
  }, []);

  const handleRenameProject = useCallback(async () => {
    if (!activeProject) {
      return;
    }

    const title = window.prompt("Rename project", activeProject.title);
    if (!title || title.trim() === activeProject.title) {
      return;
    }

    try {
      await renameProject(activeProject.projectId, title.trim());
      setProjects((prev) =>
        prev.map((project) =>
          project.projectId === activeProject.projectId ? { ...project, title: title.trim() } : project
        )
      );
      setActiveProject((prev) => (prev ? { ...prev, title: title.trim() } : prev));
    } catch (error) {
      console.error("Failed to rename project", error);
      setErrorMessage((error as Error).message ?? "Unable to rename project");
    }
  }, [activeProject]);

  const handleOrientationChange = useCallback(
    async (orientation: "portrait" | "landscape") => {
      if (!activeProject || activeProject.orientation === orientation) {
        return;
      }

      // Optimistically update UI immediately
      const previousOrientation = activeProject.orientation;
      setActiveProject((prev) => (prev ? { ...prev, orientation } : prev));
      setProjects((prev) =>
        prev.map((project) =>
          project.projectId === activeProject.projectId ? { ...project, orientation } : project
        )
      );

      // Then sync to backend in the background
      try {
        await updateProjectOrientation(activeProject.projectId, orientation);
      } catch (error) {
        // Revert on error
        console.error("Failed to update orientation", error);
        setActiveProject((prev) => (prev ? { ...prev, orientation: previousOrientation } : prev));
        setProjects((prev) =>
          prev.map((project) =>
            project.projectId === activeProject.projectId ? { ...project, orientation: previousOrientation } : project
          )
        );
        setErrorMessage((error as Error).message ?? "Unable to update orientation");
      }
    },
    [activeProject]
  );

  const handleSavePrompts = useCallback(
    async (prompts: string[]) => {
      if (!activeProjectId) {
        throw new Error("No active project selected");
      }

      setErrorMessage(null);
      await updateProjectPrompts(activeProjectId, prompts);
      setActiveProject((prev) => (prev ? { ...prev, promptList: prompts } : prev));
    },
    [activeProjectId]
  );

  const handleGenerateClips = useCallback(async () => {
    if (!activeProjectId || !activeProject) {
      return;
    }

    const hasPrompts = (activeProject.promptList ?? []).some((prompt) => prompt.trim().length > 0);
    if (!hasPrompts) {
      setErrorMessage("Add at least one prompt before generating clips.");
      return;
    }

    setIsStartingGeneration(true);
    setErrorMessage(null);
    try {
      const payloadPrompts = activeProject.promptList ?? [];
      const { jobId, promptCount } = await generateProject(activeProjectId, payloadPrompts);
      setGenerationJob({
        jobId,
        projectId: activeProjectId,
        status: "queued",
        promptCount,
        completedPrompts: 0,
        failedPrompts: 0,
        clipRelativePaths: [],
        error: null,
      });
      setActiveProject((prev) =>
        prev && prev.projectId === activeProjectId
          ? {
              ...prev,
              status: "generating",
              // Preserve existing clips - backend will keep them and only generate missing ones
              clipFilenames: prev.clipFilenames || [],
              stitchedFilename: undefined,
              errorInfo: undefined,
            }
          : prev
      );
      syncProjectSummary(activeProjectId, {
        status: "generating",
        // Keep existing clip count - backend preserves clips
        clipCount: activeProject.clipFilenames?.filter(Boolean).length ?? 0,
        hasStitchedReel: false,
      });
    } catch (error) {
      console.error("Failed to start reel generation", error);
      const errorMsg = (error as Error).message ?? "Unable to start generation";
      
      // Provide helpful context for bucket configuration errors
      if (errorMsg.includes("storage bucket") || errorMsg.includes("BUCKET")) {
        setErrorMessage(
          "⚙️ Storage not configured. Please set VIDEO_STORAGE_BUCKET in your .env file. " +
          "See REEL_MAKER_SETUP.md for detailed setup instructions."
        );
      } else {
        setErrorMessage(errorMsg);
      }
    } finally {
      setIsStartingGeneration(false);
    }
  }, [activeProject, activeProjectId, syncProjectSummary]);

  const handleStitchClips = useCallback(async () => {
    if (!activeProjectId || !activeProject) {
      return;
    }

    const clipCount = activeProject.clipFilenames?.length ?? 0;
    if (clipCount < 2) {
      setErrorMessage("Need at least 2 clips to stitch.");
      return;
    }

    setErrorMessage(null);
    try {
      const { jobId } = await stitchProject(activeProjectId);
      setStitchingJob({ projectId: activeProjectId, jobId });
      
      // Update project status to stitching
      setActiveProject((prev) =>
        prev && prev.projectId === activeProjectId
          ? {
              ...prev,
              status: "stitching",
            }
          : prev
      );
      syncProjectSummary(activeProjectId, {
        status: "stitching",
      });
      
      // Refresh project after delays to get the stitched file
      // Check multiple times as stitching can take time
      // Extended intervals to cover longer jobs (up to 2 minutes)
      const checkStatuses = [5000, 10000, 15000, 30000, 45000, 60000, 90000, 120000]; // 5s to 2 minutes
      checkStatuses.forEach((delay) => {
        setTimeout(async () => {
          if (activeProjectId) {
            try {
              const updated = await fetchProject(activeProjectId);
              setActiveProject(updated);
              syncProjectSummary(activeProjectId, {
                status: updated.status,
                hasStitchedReel: !!updated.stitchedFilename,
              });
              
              // If stitching is complete, stop polling
              if (updated.status !== 'stitching') {
                console.log('Stitching complete, status:', updated.status);
              }
            } catch (err) {
              console.error("Failed to refresh project:", err);
            }
          }
        }, delay);
      });
      
    } catch (error) {
      const errorMsg = (error as Error).message ?? "Unable to start stitching";
      
      // If job is already running, treat it as success and fetch the job ID
      if (errorMsg.includes("already running")) {
        console.warn("Stitch job already in progress for project", activeProjectId);
        setActiveProject((prev) =>
          prev && prev.projectId === activeProjectId
            ? { ...prev, status: "stitching" }
            : prev
        );
        syncProjectSummary(activeProjectId, { status: "stitching" });
        
        // Try to fetch the existing job ID
        try {
          const job = await fetchActiveStitchJob(activeProjectId);
          if (job?.jobId) {
            setStitchingJob({ projectId: activeProjectId, jobId: job.jobId });
          }
        } catch (fetchErr) {
          console.warn("Could not fetch existing stitch job", fetchErr);
        }
        return;
      }
      
      console.error("Failed to start stitching", error);
      setErrorMessage(errorMsg);
      setStitchingJob((prev) => (prev?.projectId === activeProjectId ? null : prev));
    }
  }, [activeProject, activeProjectId, syncProjectSummary]);

  useEffect(() => {
    if (!activeProject || !stitchingJob) {
      return;
    }

    if (stitchingJob.projectId !== activeProject.projectId) {
      return;
    }

    if (activeProject.status !== "stitching") {
      setStitchingJob(null);
    }
  }, [activeProject, stitchingJob]);

  useEffect(() => {
    if (!stitchingJob) {
      return;
    }

    if (stitchingJob.projectId !== activeProjectId) {
      setStitchingJob(null);
    }
  }, [activeProjectId, stitchingJob]);

  useEffect(() => {
    if (!activeProject) {
      return;
    }

    if (activeProject.status !== "stitching") {
      stitchingJobFetchRef.current = null;
      return;
    }

    if (stitchingJob?.projectId === activeProject.projectId) {
      return;
    }

    if (stitchingJobFetchRef.current === activeProject.projectId) {
      return;
    }

    stitchingJobFetchRef.current = activeProject.projectId;

    const loadExistingJob = async () => {
      try {
        const job = await fetchActiveStitchJob(activeProject.projectId);
        if (job?.jobId) {
          setStitchingJob({ projectId: activeProject.projectId, jobId: job.jobId });
        } else {
          stitchingJobFetchRef.current = null;
        }
      } catch (error) {
        console.warn("Failed to fetch active stitching job", error);
        stitchingJobFetchRef.current = null;
      }
    };

    void loadExistingJob();
  }, [activeProject, stitchingJob]);

  // Auto-stitch when all clips are ready
  useEffect(() => {
    if (!activeProject || !activeProjectId) {
      return;
    }

    const clipCount = activeProject.clipFilenames?.length ?? 0;
    const shouldAutoStitch = 
      clipCount >= 2 &&
      activeProject.status === "ready" &&
      !activeProject.hasStitchedReel &&
      !autoStitchAttemptedRef.current;

    if (shouldAutoStitch) {
      console.log("Auto-stitching clips...");
      autoStitchAttemptedRef.current = true;
      setHasAutoStitched(true);
      handleStitchClips();
    }

    // Reset flag when project changes or clips change
    if (activeProject.status === "generating") {
      autoStitchAttemptedRef.current = false;
    }
  }, [activeProject, activeProjectId, handleStitchClips]);

  // Listen for stitch job completion from progress monitor
  useEffect(() => {
    console.log('[App] Setting up stitchJobComplete event listener');
    
    const handleStitchComplete = async (event: Event) => {
      const customEvent = event as CustomEvent<{ status: string; projectId: string }>;
      console.log('[App] ========================================');
      console.log('[App] STITCH JOB COMPLETE EVENT RECEIVED');
      console.log('[App] Event detail:', customEvent.detail);
      console.log('[App] ========================================');
      
      const { status, projectId } = customEvent.detail;
      
      if (status === 'SUCCESS' && projectId === activeProjectId) {
        console.log('[App] Success status for active project, fetching updated project data...');
        try {
          const updated = await fetchProject(projectId);
          console.log('[App] Updated project data:', updated);
          setActiveProject(updated);
          syncProjectSummary(projectId, {
            status: updated.status,
            hasStitchedReel: !!updated.stitchedFilename,
          });
          console.log('[App] React state updated with stitched video');
        } catch (err) {
          console.error('[App] Failed to fetch updated project:', err);
        }
      }
    };
    
    window.addEventListener('stitchJobComplete', handleStitchComplete);
    console.log('[App] Event listener attached');
    
    return () => {
      console.log('[App] Cleaning up stitchJobComplete event listener');
      window.removeEventListener('stitchJobComplete', handleStitchComplete);
    };
  }, [activeProjectId, syncProjectSummary]);

  const listErrorNotice = useMemo(() => {
    if (!errorMessage) {
      return null;
    }

    return (
      <div className="global-error" role="status">
        <i className="fa fa-triangle-exclamation" aria-hidden="true" />
        <span>{errorMessage}</span>
      </div>
    );
  }, [errorMessage]);

  const canGenerateClips = useMemo(() => {
    if (!activeProject) {
      return false;
    }
    return (activeProject.promptList ?? []).some((prompt) => prompt.trim().length > 0);
  }, [activeProject]);

  const activeJobForProject = useMemo(() => {
    if (!generationJob || !activeProject) {
      return null;
    }
    return generationJob.projectId === activeProject.projectId ? generationJob : null;
  }, [generationJob, activeProject]);

  return (
    <div className="reel-app">
      {listErrorNotice}
      <ProjectList
        projects={projects}
        activeProjectId={activeProjectId}
        onSelect={setActiveProjectId}
        onCreate={handleCreateProject}
        isLoading={listLoading}
      />
      <main className="reel-app__content" role="main">
        {projectLoading && (
          <div className="content-loading">
            <i className="fa fa-spinner fa-spin" aria-hidden="true" /> Loading project…
          </div>
        )}

        {!projectLoading && !activeProject && (
          <div className="empty-state">
            <i className="fa fa-video-slash" aria-hidden="true" />
            <h2>No projects yet</h2>
            <p>Create your first reel to get started.</p>
            <button type="button" className="btn btn-primary" onClick={handleCreateProject}>
              New project
            </button>
          </div>
        )}

        {activeProject && !projectLoading && (
          <>
            <ProjectSummary 
              project={activeProject} 
              onRename={handleRenameProject} 
              onOrientationChange={handleOrientationChange}
            />
            <ActionToolbar
              projectName={activeProject.title}
              projectStatus={activeProject.status}
              canGenerate={canGenerateClips}
              isRequestingGeneration={isStartingGeneration}
              onGenerate={handleGenerateClips}
              activeJob={activeJobForProject}
            />
            <PromptPanel project={activeProject} onSavePrompts={handleSavePrompts} />
            <SceneList project={activeProject} />
            <StitchPanel
              project={activeProject}
              onStitch={handleStitchClips}
              activeStitchJobId={
                stitchingJob?.projectId === activeProject.projectId ? stitchingJob.jobId : undefined
              }
            />
          </>
        )}
      </main>
    </div>
  );
}
