import clsx from "clsx";
import { useState } from "react";
import { ReelProject } from "../types";

interface SceneListProps {
  project: ReelProject;
}

const statusCopy: Record<"pending" | "rendering" | "done", string> = {
  pending: "Queued",
  rendering: "Rendering",
  done: "Ready",
};

const statusIcon: Record<"pending" | "rendering" | "done", string> = {
  pending: "clock",
  rendering: "spinner",
  done: "check",
};

function deriveStatus(projectStatus: ReelProject["status"]): "pending" | "rendering" | "done" {
  if (projectStatus === "generating") {
    return "rendering";
  }
  if (projectStatus === "ready") {
    return "done";
  }
  return "pending";
}

export function SceneList({ project }: SceneListProps) {
  const clips = project.clipFilenames ?? [];
  const prompts = project.promptList ?? [];
  const status = deriveStatus(project.status);

  const getClipUrl = (clipPath: string) => {
    return `/api/reel/projects/${project.projectId}/clips/${clipPath}`;
  };

  const getPromptForClip = (index: number): string => {
    if (prompts[index]) {
      return prompts[index];
    }
    return "No prompt available";
  };

  return (
    <section className="scene-list">
      <header className="scene-list__header">
        <div>
          <h2>Generated Clips</h2>
          <p>{clips.length > 0 ? `${clips.length} clip${clips.length === 1 ? "" : "s"} ready` : "No clips yet"}</p>
        </div>
      </header>
      {clips.length === 0 ? (
        <div className="scene-list__empty">
          <i className="fa fa-film" aria-hidden="true" />
          <p>No clips generated yet.</p>
        </div>
      ) : (
        <ul>
          {clips.map((clip, index) => (
            <li key={clip ?? index} className="scene-card">
              <div className="scene-card__icon">
                <i className={clsx("fa", `fa-${statusIcon[status]}`, `scene-card__icon--${status}`)} aria-hidden="true" />
              </div>
              <div className="scene-card__content">
                <div className="scene-card__title-row">
                  <h3>Clip {index + 1}</h3>
                  <span className="scene-card__duration">{project.durationSeconds}s</span>
                </div>
                
                <p className="scene-card__prompt">{getPromptForClip(index)}</p>
                
                {status === "done" && clip && (
                  <div className="scene-card__video">
                    <video
                      controls
                      preload="metadata"
                      className="scene-card__video-player"
                    >
                      <source src={`${getClipUrl(clip)}#t=0.1`} type="video/mp4" />
                      Your browser does not support the video tag.
                    </video>
                  </div>
                )}
                
                <span className={clsx("status-pill", `status-pill--${status}`)}>{statusCopy[status]}</span>
              </div>
              <div className="scene-card__actions">
                {status === "done" && (
                  <>
                    <a
                      href={clip ? getClipUrl(clip) : "#"}
                      download={`clip-${index + 1}.mp4`}
                      className="icon-button"
                      aria-label="Download clip"
                      title="Download clip"
                    >
                      <i className="fa fa-download" aria-hidden="true" />
                    </a>
                  </>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
