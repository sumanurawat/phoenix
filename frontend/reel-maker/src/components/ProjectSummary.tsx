import clsx from "clsx";
import { format } from "date-fns";
import { ReelProject } from "../types";

interface ProjectSummaryProps {
  project: ReelProject;
  onRename: () => void;
  onOrientationChange: (orientation: "portrait" | "landscape") => void;
}

const statusLabel: Record<ReelProject["status"], string> = {
  draft: "Draft",
  generating: "Generating",
  stitching: "Stitching",
  ready: "Ready",
  error: "Needs attention",
};

const orientationCopy: Record<ReelProject["orientation"], string> = {
  portrait: "Vertical (9:16)",
  landscape: "Horizontal (16:9)",
};

export function ProjectSummary({ project, onRename, onOrientationChange }: ProjectSummaryProps) {
  const updatedDate = project.updatedAt ? format(new Date(project.updatedAt), "MMM d, yyyy 'at' h:mm a") : "";
  
  // Lock orientation if clips have been generated
  const hasGeneratedClips = project.clipCount > 0;

  return (
    <section className="project-summary-compact">
      <div className="project-summary-compact__header">
        <div className="project-summary-compact__title-row">
          <h1>{project.title}</h1>
          <span className={clsx("status-pill", `status-pill--${project.status}`)}>{statusLabel[project.status]}</span>
          <button type="button" className="btn btn-sm btn-outline" onClick={onRename}>
            <i className="fa fa-edit" aria-hidden="true" /> Rename
          </button>
        </div>
        <div className="project-summary-compact__meta">
          <div className="orientation-toggle">
            <button
              type="button"
              className={clsx("orientation-toggle__btn", project.orientation === "portrait" && "active")}
              onClick={() => onOrientationChange("portrait")}
              aria-label="Portrait mode"
              title={hasGeneratedClips ? "Orientation locked (videos already generated)" : "Portrait (9:16)"}
              disabled={hasGeneratedClips}
            >
              <i className="fa fa-mobile-screen-button" aria-hidden="true" />
            </button>
            <button
              type="button"
              className={clsx("orientation-toggle__btn", project.orientation === "landscape" && "active")}
              onClick={() => onOrientationChange("landscape")}
              aria-label="Landscape mode"
              title={hasGeneratedClips ? "Orientation locked (videos already generated)" : "Landscape (16:9)"}
              disabled={hasGeneratedClips}
            >
              <i className="fa fa-tv" aria-hidden="true" />
            </button>
          </div>
          <span className="project-summary-compact__separator">•</span>
          <span className="project-summary-compact__meta-item">
            {project.clipCount} clip{project.clipCount === 1 ? "" : "s"}
          </span>
          <span className="project-summary-compact__separator">•</span>
          <span className="project-summary-compact__meta-item">
            {project.durationSeconds}s
          </span>
          <span className="project-summary-compact__separator">•</span>
          <span className="project-summary-compact__meta-item">
            {project.audioEnabled ? "Audio on" : "Muted"}
          </span>
          {project.hasStitchedReel && (
            <>
              <span className="project-summary-compact__separator">•</span>
              <span className="project-summary-compact__meta-item">
                <i className="fa fa-check-circle" aria-hidden="true" /> Combined reel ready
              </span>
            </>
          )}
        </div>
      </div>
    </section>
  );
}
