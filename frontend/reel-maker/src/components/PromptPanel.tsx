import { useMemo } from "react";
import { ReelProject } from "../types";

interface PromptPanelProps {
  project: ReelProject;
  onEditPrompts: () => void;
}

export function PromptPanel({ project, onEditPrompts }: PromptPanelProps) {
  const formattedPrompts = useMemo(() => {
    if (!project.promptList?.length) {
      return "";
    }
    try {
      return JSON.stringify(project.promptList, null, 2);
    } catch (error) {
      return project.promptList.join("\n");
    }
  }, [project.promptList]);

  return (
    <section className="prompt-panel">
      <header className="prompt-panel__header">
        <div>
          <h2>Prompt definitions</h2>
          <p>Each entry produces an individual clip. Edit to regenerate with updated guidance.</p>
        </div>
        <div className="prompt-panel__actions">
          <button type="button" className="btn btn-outline" onClick={onEditPrompts}>
            <i className="fa fa-pen" aria-hidden="true" /> Edit prompts
          </button>
          <button type="button" className="btn btn-primary" disabled>
            <i className="fa fa-wand-magic" aria-hidden="true" /> Regenerate (coming soon)
          </button>
        </div>
      </header>
      <div className="prompt-panel__grid">
        <article>
          <h3>Prompt list</h3>
          <textarea
            readOnly
            value={formattedPrompts}
            aria-label="Prompt list"
            placeholder="[]"
          />
          {!project.promptList?.length && (
            <p className="prompt-panel__helper">No prompts yet. Add prompts when you kick off generation.</p>
          )}
        </article>
        <article>
          <h3>Status notes</h3>
          {project.status === "error" ? (
            <p className="prompt-panel__error">
              {project.errorInfo?.message ?? "Generation failed. Update prompts and try again."}
            </p>
          ) : (
            <p>
              {project.status === "draft"
                ? "Prompts saved but no clips generated yet."
                : project.status === "generating"
                ? "Clips are currently rendering. Refresh to see updates."
                : "Clips generated successfully. Stitch to produce a full reel."}
            </p>
          )}
        </article>
      </div>
    </section>
  );
}
