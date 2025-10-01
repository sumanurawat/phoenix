import clsx from "clsx";
import { ReelGenerationJob, ReelProjectStatus } from "../types";

interface ActionToolbarProps {
  projectName: string;
  projectStatus: ReelProjectStatus;
  canGenerate: boolean;
  isRequestingGeneration: boolean;
  onGenerate: () => void;
  activeJob: ReelGenerationJob | null;
}

export function ActionToolbar({
  projectName,
  projectStatus,
  canGenerate,
  isRequestingGeneration,
  onGenerate,
  activeJob,
}: ActionToolbarProps) {
  const isGenerating = projectStatus === "generating";
  const isGenerateDisabled = !canGenerate || isGenerating || isRequestingGeneration;
  const showSpinner = isGenerating || isRequestingGeneration;
  const generateLabel = showSpinner ? "Generating clips" : "Generate clips";

  const statusLabel = (() => {
    if (showSpinner) {
      const completed = activeJob?.completedPrompts ?? 0;
      const total = activeJob?.promptCount ?? 0;
      if (total > 0) {
        return `Rendering ${completed}/${total} clips…`;
      }
      return "Rendering clips…";
    }
    if (projectStatus === "ready") {
      return "Clips are ready. Stitch to combine scenes.";
    }
    if (projectStatus === "error") {
      return "Generation failed. Update prompts and try again.";
    }
    return "Saved prompts are ready to render.";
  })();

  return (
    <section className="action-toolbar">
      <div className="action-toolbar__primary">
        <button type="button" className="btn btn-outline-primary" disabled>
          <i className="fa fa-check" aria-hidden="true" /> Validate prompts
        </button>
        <button type="button" className="btn btn-primary" disabled={isGenerateDisabled} onClick={onGenerate}>
          <i className={clsx("fa", showSpinner ? "fa-spinner fa-spin" : "fa-play")} aria-hidden="true" /> {generateLabel}
        </button>
        <button type="button" className="btn btn-outline" disabled>
          <i className="fa fa-bolt" aria-hidden="true" /> Quick iterate
        </button>
      </div>
      <aside className="action-toolbar__secondary">
        <span className="action-toolbar__hint">
          <strong>{projectName}</strong>: {statusLabel}
        </span>
        <div className="action-toolbar__icons">
          <button type="button" className="icon-button" aria-label="Share project" disabled>
            <i className="fa fa-share-nodes" aria-hidden="true" />
          </button>
          <button type="button" className="icon-button" aria-label="More options" disabled>
            <i className="fa fa-ellipsis-h" aria-hidden="true" />
          </button>
        </div>
      </aside>
    </section>
  );
}
