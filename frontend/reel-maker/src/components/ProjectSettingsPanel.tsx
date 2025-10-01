import { format } from "date-fns";
import { ReelProject } from "../types";

interface ProjectSettingsPanelProps {
  project: ReelProject;
}

export function ProjectSettingsPanel({ project }: ProjectSettingsPanelProps) {
  const updatedDate = project.updatedAt ? format(new Date(project.updatedAt), "MMM d, h:mm a") : null;

  return (
    <aside className="project-settings-sidebar">
      <header className="project-settings-sidebar__header">
        <h2>Settings</h2>
      </header>
      <div className="project-settings-sidebar__content">
        <div className="setting-item">
          <span className="setting-item__label">Orientation</span>
          <span className="setting-item__value">{project.orientation === "portrait" ? "Portrait" : "Landscape"}</span>
        </div>
        <div className="setting-item">
          <span className="setting-item__label">Duration</span>
          <span className="setting-item__value">{project.durationSeconds}s</span>
        </div>
        <div className="setting-item">
          <span className="setting-item__label">Model</span>
          <span className="setting-item__value">Veo 3.0 Fast</span>
        </div>
        <div className="setting-item">
          <span className="setting-item__label">Audio</span>
          <span className="setting-item__value">{project.audioEnabled ? "On" : "Off"}</span>
        </div>
        <div className="setting-item">
          <span className="setting-item__label">Compression</span>
          <span className="setting-item__value">Optimized</span>
        </div>
        {project.hasStitchedReel && (
          <div className="setting-item">
            <span className="setting-item__label">Combined Reel</span>
            <span className="setting-item__value setting-item__value--success">
              <i className="fa fa-check-circle" aria-hidden="true" /> Ready
            </span>
          </div>
        )}
        {updatedDate && (
          <div className="setting-item setting-item--meta">
            <span className="setting-item__label">Last updated</span>
            <span className="setting-item__value">{updatedDate}</span>
          </div>
        )}
      </div>
    </aside>
  );
}
