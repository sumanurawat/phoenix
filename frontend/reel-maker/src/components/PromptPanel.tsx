import { useMemo, useState, useCallback } from "react";
import { ReelProject } from "../types";

interface PromptPanelProps {
  project: ReelProject;
  onSavePrompts: (prompts: string[]) => Promise<void>;
}

const SAMPLE_PROMPTS = [
  "A cat playing piano in a jazz bar, cinematic lighting",
  "Slow orbital shot of a futuristic eco city at sunrise",
  "Drone flyover of terraced rice fields with morning mist"
];

export function PromptPanel({ project, onSavePrompts }: PromptPanelProps) {
  const [textareaValue, setTextareaValue] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Initialize textarea value from project prompts
  const initialValue = useMemo(() => {
    if (!project.promptList?.length) {
      return "";
    }
    return JSON.stringify(project.promptList, null, 2);
  }, [project.promptList]);

  // Keep textarea synced with project prompts (but allow editing)
  useMemo(() => {
    if (!isSaving) {
      setTextareaValue(initialValue);
    }
  }, [initialValue, isSaving]);

  const handleUseSample = useCallback(() => {
    setTextareaValue(JSON.stringify(SAMPLE_PROMPTS, null, 2));
    setErrorMessage(null);
  }, []);

  const handleSave = useCallback(async () => {
    let prompts: string[];
    
    // Try to parse as JSON array first
    try {
      const parsed = JSON.parse(textareaValue);
      if (Array.isArray(parsed)) {
        prompts = parsed.map(item => String(item).trim()).filter(Boolean);
      } else {
        setErrorMessage("Invalid format. Please enter a JSON array like: [\"prompt 1\", \"prompt 2\"]");
        return;
      }
    } catch (error) {
      setErrorMessage("Invalid JSON format. Please enter a valid JSON array like: [\"prompt 1\", \"prompt 2\"]");
      return;
    }

    if (!prompts.length) {
      setErrorMessage("Add at least one prompt before saving.");
      return;
    }

    setIsSaving(true);
    setErrorMessage(null);
    try {
      await onSavePrompts(prompts);
    } catch (error) {
      setErrorMessage((error as Error)?.message ?? "Failed to save prompts");
    } finally {
      setIsSaving(false);
    }
  }, [textareaValue, onSavePrompts]);

  return (
    <section className="prompt-panel">
      <header className="prompt-panel__header">
        <div>
          <h2>Prompt definitions</h2>
          <p>Paste a JSON array of prompts. Each entry produces an individual clip.</p>
        </div>
        <div className="prompt-panel__actions">
          <button type="button" className="btn btn-outline" onClick={handleUseSample}>
            <i className="fa fa-magic" aria-hidden="true" /> Sample prompts
          </button>
          <button 
            type="button" 
            className="btn btn-primary" 
            onClick={handleSave}
            disabled={isSaving}
          >
            <i className={isSaving ? "fa fa-spinner fa-spin" : "fa fa-save"} aria-hidden="true" /> 
            {isSaving ? "Saving..." : "Save prompts"}
          </button>
        </div>
      </header>
      <div className="prompt-panel__grid">
        <article>
          <h3>Prompt list (JSON array format)</h3>
          <textarea
            value={textareaValue}
            onChange={(e) => setTextareaValue(e.target.value)}
            aria-label="Prompt list"
            placeholder='[\n  "A cat playing piano in a jazz bar",\n  "Slow orbital shot of a futuristic city",\n  "Drone flyover of terraced rice fields"\n]'
          />
          {errorMessage && (
            <p className="prompt-panel__error">{errorMessage}</p>
          )}
          {!project.promptList?.length && !textareaValue && (
            <p className="prompt-panel__helper">No prompts yet. Paste a JSON array or click "Sample prompts" to get started.</p>
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
