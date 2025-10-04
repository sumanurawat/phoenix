import clsx from "clsx";
import { formatDistanceToNowStrict } from "date-fns";
import { useState } from "react";
import { ReelProjectSummary } from "../types";

interface ProjectListProps {
  projects: ReelProjectSummary[];
  activeProjectId: string | null;
  onSelect: (projectId: string) => void;
  onCreate: () => void;
  onDelete: (projectId: string) => void;
  isLoading?: boolean;
}

const statusLabels: Record<ReelProjectSummary["status"], string> = {
  draft: "Draft",
  generating: "Generating",
  stitching: "Stitching",
  ready: "Ready",
  error: "Needs attention",
};

export function ProjectList({ projects, activeProjectId, onSelect, onCreate, onDelete, isLoading = false }: ProjectListProps) {
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);

  const handleDeleteClick = (e: React.MouseEvent, projectId: string) => {
    e.stopPropagation(); // Prevent project selection
    setConfirmDeleteId(projectId);
  };

  const handleConfirmDelete = async (e: React.MouseEvent, projectId: string) => {
    e.stopPropagation();
    setConfirmDeleteId(null);
    setDeletingId(projectId);
    
    try {
      await onDelete(projectId);
    } finally {
      setDeletingId(null);
    }
  };

  const handleCancelDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    setConfirmDeleteId(null);
  };

  return (
    <aside className="project-sidebar">
      <div className="project-sidebar__header">
        <h2>Projects</h2>
        <button className="btn btn-primary" type="button" onClick={onCreate} title="Create new project">
          <i className="fa fa-plus" aria-hidden="true" />
          <span className="visually-hidden">Create new project</span>
        </button>
      </div>

      <div className="project-sidebar__list-wrapper" aria-live="polite">
        {isLoading ? (
          <div className="project-sidebar__empty">
            <i className="fa fa-spinner fa-spin" aria-hidden="true" />
            <p>Loading projects…</p>
          </div>
        ) : projects.length === 0 ? (
          <div className="project-sidebar__empty">
            <i className="fa fa-folder-open" aria-hidden="true" />
            <p>No projects yet</p>
            <button className="btn btn-primary btn-sm" type="button" onClick={onCreate}>
              Create first project
            </button>
          </div>
        ) : (
          <ul className="project-sidebar__list">
            {projects.map((project) => (
              <li key={project.projectId}>
                <div className="project-sidebar__item-container">
                  <button
                    type="button"
                    className={clsx("project-sidebar__item", {
                      "project-sidebar__item--active": project.projectId === activeProjectId,
                      "project-sidebar__item--deleting": deletingId === project.projectId,
                    })}
                    onClick={() => onSelect(project.projectId)}
                    disabled={deletingId === project.projectId}
                  >
                    <div className="project-sidebar__item-title">
                      <span>{project.title}</span>
                      <span className={clsx("status-pill", `status-pill--${project.status}`)}>
                        {statusLabels[project.status]}
                      </span>
                    </div>
                    <p className="project-sidebar__item-description">
                      {project.clipCount} {project.clipCount === 1 ? "clip" : "clips"}
                      {project.hasStitchedReel && " • Combined reel"}
                    </p>
                  </button>
                  
                  {confirmDeleteId === project.projectId ? (
                    <div className="project-sidebar__delete-confirm">
                      <p>
                        <strong>Delete this project?</strong>
                        <br />
                        <small>This will permanently delete all prompts, videos, and data.</small>
                      </p>
                      <div className="project-sidebar__delete-actions">
                        <button
                          type="button"
                          className="btn btn-danger btn-sm"
                          onClick={(e) => handleConfirmDelete(e, project.projectId)}
                        >
                          <i className="fa fa-trash" aria-hidden="true" /> Delete
                        </button>
                        <button
                          type="button"
                          className="btn btn-secondary btn-sm"
                          onClick={handleCancelDelete}
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  ) : (
                    <button
                      type="button"
                      className="project-sidebar__delete-btn"
                      onClick={(e) => handleDeleteClick(e, project.projectId)}
                      disabled={deletingId === project.projectId}
                      title="Delete project"
                      aria-label={`Delete project: ${project.title}`}
                    >
                      {deletingId === project.projectId ? (
                        <i className="fa fa-spinner fa-spin" aria-hidden="true" />
                      ) : (
                        <i className="fa fa-trash" aria-hidden="true" />
                      )}
                    </button>
                  )}
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </aside>
  );
}
