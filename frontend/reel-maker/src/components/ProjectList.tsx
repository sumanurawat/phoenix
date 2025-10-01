import clsx from "clsx";
import { formatDistanceToNowStrict } from "date-fns";
import { ReelProjectSummary } from "../types";

interface ProjectListProps {
  projects: ReelProjectSummary[];
  activeProjectId: string | null;
  onSelect: (projectId: string) => void;
  onCreate: () => void;
  isLoading?: boolean;
}

const statusLabels: Record<ReelProjectSummary["status"], string> = {
  draft: "Draft",
  generating: "Generating",
  stitching: "Stitching",
  ready: "Ready",
  error: "Needs attention",
};

export function ProjectList({ projects, activeProjectId, onSelect, onCreate, isLoading = false }: ProjectListProps) {
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
                <button
                  type="button"
                  className={clsx("project-sidebar__item", {
                    "project-sidebar__item--active": project.projectId === activeProjectId,
                  })}
                  onClick={() => onSelect(project.projectId)}
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
              </li>
            ))}
          </ul>
        )}
      </div>
    </aside>
  );
}
