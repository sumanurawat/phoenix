import clsx from "clsx";
import { useState } from "react";
import { ReelProject } from "../types";
import { VideoPlayer } from "./VideoPlayer";

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

function deriveClipStatus(
  clipPath: string | null | undefined, 
  projectStatus: ReelProject["status"]
): "pending" | "rendering" | "done" {
  // If clip exists (has path), it's done regardless of project status
  if (clipPath) {
    return "done";
  }
  
  // If project is generating, clip is rendering
  if (projectStatus === "generating") {
    return "rendering";
  }
  
  // Otherwise pending
  return "pending";
}

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
  const overallStatus = deriveStatus(project.status);

  const getClipUrl = (clipPath: string) => {
    return `/api/reel/projects/${project.projectId}/clips/${clipPath}`;
  };

  const getPromptForClip = (index: number): string => {
    if (prompts[index]) {
      return prompts[index];
    }
    return "No prompt available";
  };
  
  // Count completed clips
  const completedClips = clips.filter(clip => clip).length;
  const totalPrompts = prompts.length;

  return (
    <section className="scene-list">
      <header className="scene-list__header">
        <div>
          <h2>Generated Clips</h2>
          <p>
            {totalPrompts > 0 
              ? `${completedClips}/${totalPrompts} clip${totalPrompts === 1 ? "" : "s"} ready` 
              : "No clips yet"}
          </p>
        </div>
      </header>
      {prompts.length === 0 ? (
        <div className="scene-list__empty">
          <i className="fa fa-film" aria-hidden="true" />
          <p>No clips generated yet.</p>
        </div>
      ) : (
        <ul>
          {prompts.map((prompt, index) => {
            const clip = clips[index];
            const clipStatus = deriveClipStatus(clip, project.status);
            
            return (
              <li key={clip ?? index} className="scene-card">
                <div className="scene-card__icon">
                  <i className={clsx("fa", `fa-${statusIcon[clipStatus]}`, `scene-card__icon--${clipStatus}`)} aria-hidden="true" />
                </div>
                <div className="scene-card__content">
                  <div className="scene-card__title-row">
                    <h3>Clip {index + 1}</h3>
                    <span className="scene-card__duration">{project.durationSeconds}s</span>
                  </div>
                  
                  <p className="scene-card__prompt">{prompt}</p>
                  
                  {clipStatus === "done" && clip && (
                    <div className="scene-card__video">
                      <VideoPlayer
                        apiUrl={getClipUrl(clip)}
                        className="scene-card__video-player"
                        controls
                        preload="metadata"
                      />
                    </div>
                  )}
                  
                  <span className={clsx("status-pill", `status-pill--${clipStatus}`)}>{statusCopy[clipStatus]}</span>
                </div>
                <div className="scene-card__actions">
                  {clipStatus === "done" && clip && (
                    <>
                      <a
                        href={getClipUrl(clip)}
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
            );
          })}
        </ul>
      )}
    </section>
  );
}
