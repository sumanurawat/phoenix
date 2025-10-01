import { FormEvent, MouseEvent, useEffect, useMemo, useState } from "react";

interface PromptEditorModalProps {
  isOpen: boolean;
  initialPrompts: string[];
  onClose: () => void;
  onSave: (prompts: string[]) => Promise<void> | void;
}

const SAMPLE_PROMPTS = [
  "A cat playing piano in a jazz bar, cinematic lighting",
  "Slow orbital shot of a futuristic eco city at sunrise",
  "Drone flyover of terraced rice fields with morning mist"
];

export function PromptEditorModal({ isOpen, initialPrompts, onClose, onSave }: PromptEditorModalProps) {
  const [textareaValue, setTextareaValue] = useState("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  const initialValue = useMemo(() => {
    if (!initialPrompts?.length) {
      return "";
    }
    return initialPrompts.join("\n");
  }, [initialPrompts]);

  useEffect(() => {
    if (isOpen) {
      setTextareaValue(initialValue);
      setErrorMessage(null);
    }
  }, [isOpen, initialValue]);

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) {
    return null;
  }

  const handleUseSample = () => {
    setTextareaValue(SAMPLE_PROMPTS.join("\n"));
    setErrorMessage(null);
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const prompts = textareaValue
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter(Boolean);

    if (!prompts.length) {
      setErrorMessage("Add at least one prompt before saving.");
      return;
    }

    setIsSaving(true);
    try {
      await onSave(prompts);
      setErrorMessage(null);
    } catch (error) {
      setErrorMessage((error as Error)?.message ?? "Failed to save prompts");
      setIsSaving(false);
      return;
    }

    setIsSaving(false);
    onClose();
  };

  const handleOverlayClick = (event: MouseEvent<HTMLDivElement>) => {
    if (event.target === event.currentTarget) {
      onClose();
    }
  };

  return (
    <div className="prompt-editor-overlay" role="dialog" aria-modal="true" onMouseDown={handleOverlayClick}>
      <div className="prompt-editor-modal">
        <header className="prompt-editor-modal__header">
          <div>
            <h2>Edit prompts</h2>
            <p>Enter one prompt per line. Each prompt becomes a clip direction for the reel generator.</p>
          </div>
          <button type="button" className="icon-button" onClick={onClose} aria-label="Close prompt editor">
            <i className="fa fa-times" aria-hidden="true" />
          </button>
        </header>
        <form className="prompt-editor-modal__form" onSubmit={handleSubmit}>
          <div className="prompt-editor-modal__actions">
            <button type="button" className="btn btn-outline" onClick={handleUseSample}>
              <i className="fa fa-magic" aria-hidden="true" /> Use sample prompts
            </button>
            <span className="prompt-editor-modal__hint">You can paste your own list — we’ll keep whatever you enter.</span>
          </div>
          <label className="visually-hidden" htmlFor="prompt-editor-textarea">
            Prompts list
          </label>
          <textarea
            id="prompt-editor-textarea"
            value={textareaValue}
            onChange={(event) => setTextareaValue(event.target.value)}
            placeholder={["Hook", "Story", "Call to action"].join("\n")}
          />
          {errorMessage && <p className="prompt-editor-modal__error">{errorMessage}</p>}
          <footer className="prompt-editor-modal__footer">
            <button type="button" className="btn btn-outline" onClick={onClose} disabled={isSaving}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={isSaving}>
              {isSaving ? (
                <>
                  <i className="fa fa-spinner fa-spin" aria-hidden="true" /> Saving
                </>
              ) : (
                <>
                  <i className="fa fa-save" aria-hidden="true" /> Save prompts
                </>
              )}
            </button>
          </footer>
        </form>
      </div>
    </div>
  );
}
