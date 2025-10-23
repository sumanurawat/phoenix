import { useEffect, useState } from "react";

interface VideoPlayerProps {
  apiUrl: string;
  className?: string;
  controls?: boolean;
  preload?: "none" | "metadata" | "auto";
}

export function VideoPlayer({ apiUrl, className, controls = true, preload = "metadata" }: VideoPlayerProps) {
  const [signedUrl, setSignedUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;

    async function fetchSignedUrl() {
      try {
        setLoading(true);
        setError(null);

        const response = await fetch(apiUrl, {
          method: "GET",
          credentials: "include",
          headers: {
            Accept: "application/json",
          },
        });

        if (!response.ok) {
          throw new Error(`Failed to fetch video URL: ${response.status}`);
        }

        const data = await response.json();

        if (!data.success || !data.url) {
          throw new Error(data.error?.message || "Failed to get video URL");
        }

        if (mounted) {
          setSignedUrl(data.url);
          setLoading(false);
        }
      } catch (err) {
        console.error("Error fetching signed URL:", err);
        if (mounted) {
          setError(err instanceof Error ? err.message : "Failed to load video");
          setLoading(false);
        }
      }
    }

    fetchSignedUrl();

    return () => {
      mounted = false;
    };
  }, [apiUrl]);

  if (loading) {
    return (
      <div className={`video-player-loading ${className || ""}`}>
        <i className="fa fa-spinner fa-spin" aria-hidden="true" />
        <p>Loading video...</p>
      </div>
    );
  }

  if (error || !signedUrl) {
    return (
      <div className={`video-player-error ${className || ""}`}>
        <i className="fa fa-exclamation-triangle" aria-hidden="true" />
        <p>{error || "Failed to load video"}</p>
      </div>
    );
  }

  return (
    <video
      src={`${signedUrl}#t=0.1`}
      className={className}
      controls={controls}
      preload={preload}
    >
      Your browser does not support the video tag.
    </video>
  );
}
