import clsx from "clsx";
import { useState } from "react";
import { ReelProject } from "../types";
import { VideoPlayer } from "./VideoPlayer";

interface StitchPanelProps {
  project: ReelProject;
  onStitch: () => void;
  onDeleteStitched: () => void;
  activeStitchJobId?: string;
}

export function StitchPanel({ project, onStitch, onDeleteStitched, activeStitchJobId }: StitchPanelProps) {
  const [isStitching, setIsStitching] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  
  const clipCount = project.clipFilenames?.length || 0;
  const hasStitched = !!project.stitchedFilename;
  const canStitch = clipCount >= 2 && project.status !== "stitching" && project.status !== "generating";
  const isStitchingNow = project.status === "stitching";

  const handleStitch = async () => {
    setIsStitching(true);
    try {
      await onStitch();
    } finally {
      // Keep button disabled until status updates from backend
      setTimeout(() => setIsStitching(false), 1000);
    }
  };

  const handleDelete = async () => {
    if (!window.confirm("Delete the stitched video? You can re-stitch anytime.")) {
      return;
    }
    
    setIsDeleting(true);
    try {
      await onDeleteStitched();
    } finally {
      setIsDeleting(false);
    }
  };

  const getStitchedVideoUrl = () => {
    if (!project.stitchedFilename) return "";
    return `/api/reel/projects/${project.projectId}/clips/${project.stitchedFilename}`;
  };

  return (
    <section className="stitch-panel">
      <header className="stitch-panel__header">
        <div>
          <h2>Combined Reel</h2>
          <p>Stitch all clips into a single video.</p>
        </div>
      </header>

      {clipCount < 2 ? (
        <div className="stitch-panel__empty">
          <i className="fa fa-film" aria-hidden="true" />
          <p>Generate at least 2 clips to create a combined reel.</p>
        </div>
      ) : !hasStitched && !isStitchingNow ? (
        <div className="stitch-panel__cta">
          <i className="fa fa-layer-group fa-2x" aria-hidden="true" />
          <p>Ready to combine {clipCount} clips into one video.</p>
          <button
            className="btn btn-primary btn-lg"
            onClick={handleStitch}
            disabled={!canStitch || isStitching}
          >
            <i className={clsx("fa", isStitching ? "fa-spinner fa-spin" : "fa-wand-magic-sparkles")} aria-hidden="true" />
            {isStitching ? "Starting..." : `Stitch ${clipCount} Clips`}
          </button>
        </div>
      ) : isStitchingNow ? (
        <>
          {/* Progress monitor will inject itself here automatically */}
          <div
            id="job-progress-monitor-container"
            data-project-id={project.projectId}
            data-job-id={activeStitchJobId || undefined}
          ></div>
          
          {/* Fallback message (hidden when monitor appears) */}
          <div className="stitch-panel__processing">
            <i className="fa fa-spinner fa-spin fa-2x" aria-hidden="true" />
            <p>
              <strong>Stitching in progress...</strong>
            </p>
            <p className="text-muted">
              {activeStitchJobId
                ? `Initializing progress monitor for job ${activeStitchJobId}`
                : "Initializing progress monitor..."}
            </p>
          </div>
        </>
      ) : hasStitched ? (
        <div className="stitch-panel__result">
          <div className="stitch-panel__video-container">
            <VideoPlayer
              apiUrl={getStitchedVideoUrl()}
              className="stitch-panel__video-player"
              controls
              preload="metadata"
            />
          </div>
          <div className="stitch-panel__actions">
            <a
              href={getStitchedVideoUrl()}
              download={`${project.title}_full_reel.mp4`}
              className="btn btn-outline-primary"
            >
              <i className="fa fa-download" aria-hidden="true" /> Download Full Reel
            </a>
            <button
              className="btn btn-outline"
              onClick={handleStitch}
              disabled={!canStitch || isStitching}
            >
              <i className="fa fa-rotate" aria-hidden="true" /> Re-stitch
            </button>
            <button
              className="btn btn-outline-danger"
              onClick={handleDelete}
              disabled={isDeleting}
              title="Delete stitched video"
            >
              <i className={clsx("fa", isDeleting ? "fa-spinner fa-spin" : "fa-trash")} aria-hidden="true" />
              {isDeleting ? "Deleting..." : "Delete"}
            </button>
          </div>
          <p className="stitch-panel__filename text-muted">
            {project.stitchedFilename?.split('/').pop()}
          </p>
        </div>
      ) : null}
    </section>
  );
}
