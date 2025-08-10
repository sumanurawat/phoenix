"""Veo Video Generation Service

Provides a typed wrapper around the Vertex AI Veo long‑running video generation API.
Handles:
 - Request construction (instances + parameters)
 - Long‑running operation polling
 - Optional base64 video bytes decoding when storageUri not provided
 - Normalized response structure

NOTE: This uses the raw REST endpoint rather than the google-cloud-aiplatform helper because
predictLongRunning is newest; adjust if official SDK catches up.
"""
from __future__ import annotations

import os
import time
import json
import base64
import logging
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any

import requests
from google.auth import default as google_auth_default
from google.auth.transport.requests import Request as GoogleAuthRequest

logger = logging.getLogger(__name__)

VEO_MODELS = [
    "veo-2.0-generate-001",
    "veo-3.0-generate-001",
    "veo-3.0-fast-generate-001",
    "veo-3.0-generate-preview",
    "veo-3.0-fast-generate-preview",
]
ASPECT_RATIOS = ["16:9", "9:16"]
RESOLUTIONS = ["720p", "1080p"]  # Veo 3 only
PERSON_GENERATION = ["allow_adult", "dont_allow"]

@dataclass
class VeoGenerationParams:
    model: str = "veo-3.0-fast-generate-001"
    prompt: Optional[str] = None
    aspect_ratio: str = "16:9"
    duration_seconds: int = 8
    enhance_prompt: bool = True
    generate_audio: Optional[bool] = None  # Only for some models
    negative_prompt: Optional[str] = None
    person_generation: Optional[str] = None
    resolution: Optional[str] = None  # Veo 3 models only
    sample_count: int = 1
    seed: Optional[int] = None
    storage_uri: Optional[str] = None
    # Media (image/video) inputs (mutually exclusive per union type for each field)
    image_bytes_b64: Optional[str] = None
    image_gcs_uri: Optional[str] = None
    image_mime_type: Optional[str] = None
    last_frame_bytes_b64: Optional[str] = None
    last_frame_gcs_uri: Optional[str] = None
    last_frame_mime_type: Optional[str] = None
    video_bytes_b64: Optional[str] = None
    video_gcs_uri: Optional[str] = None
    video_mime_type: Optional[str] = None

    def validate(self) -> None:
        if self.model not in VEO_MODELS:
            raise ValueError(f"Unsupported model: {self.model}")
        if not (5 <= self.duration_seconds <= 8):
            raise ValueError("duration_seconds must be between 5 and 8")
        if self.aspect_ratio not in ASPECT_RATIOS:
            raise ValueError("aspect_ratio must be one of: " + ", ".join(ASPECT_RATIOS))
        if self.sample_count < 1 or self.sample_count > 4:
            raise ValueError("sample_count must be 1-4")
        if self.resolution and self.resolution not in RESOLUTIONS:
            raise ValueError("resolution must be 720p or 1080p")
        if self.person_generation and self.person_generation not in PERSON_GENERATION:
            raise ValueError("person_generation invalid")
        if self.generate_audio is not None and self.model.startswith("veo-2.0"):
            raise ValueError("generate_audio not supported by veo-2.0 models")
        if self.prompt is None and not (self.image_bytes_b64 or self.image_gcs_uri):
            raise ValueError("Either prompt or image must be provided")

    def build_instances(self) -> List[Dict[str, Any]]:
        inst: Dict[str, Any] = {}
        if self.prompt:
            inst["prompt"] = self.prompt
        # Image union
        if self.image_bytes_b64 or self.image_gcs_uri:
            img: Dict[str, Any] = {}
            if self.image_bytes_b64:
                img["bytesBase64Encoded"] = self.image_bytes_b64
            if self.image_gcs_uri:
                img["gcsUri"] = self.image_gcs_uri
            if self.image_mime_type:
                img["mimeType"] = self.image_mime_type
            inst["image"] = img
        # lastFrame (veo-2.0 only)
        if self.last_frame_bytes_b64 or self.last_frame_gcs_uri:
            lf: Dict[str, Any] = {}
            if self.last_frame_bytes_b64:
                lf["bytesBase64Encoded"] = self.last_frame_bytes_b64
            if self.last_frame_gcs_uri:
                lf["gcsUri"] = self.last_frame_gcs_uri
            if self.last_frame_mime_type:
                lf["mimeType"] = self.last_frame_mime_type
            inst["lastFrame"] = lf
        # video extension (veo-2.0 only)
        if self.video_bytes_b64 or self.video_gcs_uri:
            vid: Dict[str, Any] = {}
            if self.video_bytes_b64:
                vid["bytesBase64Encoded"] = self.video_bytes_b64
            if self.video_gcs_uri:
                vid["gcsUri"] = self.video_gcs_uri
            if self.video_mime_type:
                vid["mimeType"] = self.video_mime_type
            inst["video"] = vid
        return [inst]

    def build_parameters(self) -> Dict[str, Any]:
        params = {
            "aspectRatio": self.aspect_ratio,
            "durationSeconds": self.duration_seconds,
            "enhancePrompt": self.enhance_prompt,
            "sampleCount": self.sample_count,
        }
        if self.negative_prompt:
            params["negativePrompt"] = self.negative_prompt
        if self.person_generation:
            params["personGeneration"] = self.person_generation
        if self.resolution:
            params["resolution"] = self.resolution
        if self.seed is not None:
            params["seed"] = self.seed
        if self.storage_uri:
            params["storageUri"] = self.storage_uri
        if self.generate_audio is not None:
            params["generateAudio"] = self.generate_audio
        return params

@dataclass
class VeoOperationResult:
    success: bool
    job_id: Optional[str] = None
    model: Optional[str] = None
    gcs_uris: List[str] = field(default_factory=list)
    video_bytes: List[bytes] = field(default_factory=list)
    local_paths: List[str] = field(default_factory=list)
    raw_operation: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class VeoVideoGenerationService:
    def __init__(self, project: Optional[str] = None, location: str = "us-central1"):
        self.project = project or os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("PROJECT_ID")
        self.location = location
        if not self.project:
            raise RuntimeError("Google Cloud project ID not set (GOOGLE_CLOUD_PROJECT or PROJECT_ID env var)")

    # --------------- Auth helpers ---------------
    def _get_access_token(self) -> str:
        creds, _ = google_auth_default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
        if not creds.valid:
            creds.refresh(GoogleAuthRequest())
        return creds.token

    # --------------- Core calls ---------------
    def start_generation(self, params: VeoGenerationParams, poll: bool = True, poll_interval: float = 5.0, timeout: float = 600.0) -> VeoOperationResult:
        params.validate()
        token = self._get_access_token()
        model = params.model
        url = f"https://{self.location}-aiplatform.googleapis.com/v1/projects/{self.project}/locations/{self.location}/publishers/google/models/{model}:predictLongRunning"
        body = {
            "instances": params.build_instances(),
            "parameters": params.build_parameters(),
        }
        logger.info("Submitting Veo generation request model=%s duration=%s sampleCount=%s", model, params.duration_seconds, params.sample_count)
        r = requests.post(url, headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }, data=json.dumps(body), timeout=60)
        if r.status_code >= 300:
            return VeoOperationResult(success=False, error=f"submit failed {r.status_code}: {r.text}")
        op = r.json()
        name = op.get("name")
        if not poll:
            return VeoOperationResult(success=True, job_id=name, model=model, raw_operation=op)
        return self._poll_operation(model=model, operation_name=name, interval=poll_interval, timeout=timeout)

    def poll(self, model: str, operation_name: str, interval: float = 5.0, timeout: float = 600.0) -> VeoOperationResult:
        return self._poll_operation(model=model, operation_name=operation_name, interval=interval, timeout=timeout)

    def _poll_operation(self, model: str, operation_name: str, interval: float, timeout: float) -> VeoOperationResult:
        token = self._get_access_token()
        url = f"https://{self.location}-aiplatform.googleapis.com/v1/projects/{self.project}/locations/{self.location}/publishers/google/models/{model}:fetchPredictOperation"
        body = {"operationName": operation_name}
        start = time.time()
        while True:
            r = requests.post(url, headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }, data=json.dumps(body), timeout=60)
            if r.status_code >= 300:
                return VeoOperationResult(success=False, error=f"poll failed {r.status_code}: {r.text}")
            op = r.json()
            if op.get("done"):
                response = op.get("response", {})
                videos = response.get("videos", [])
                gcs_uris: List[str] = []
                video_bytes: List[bytes] = []
                for idx, v in enumerate(videos):
                    if "gcsUri" in v:
                        gcs_uris.append(v["gcsUri"])
                    elif "bytesBase64Encoded" in v:
                        try:
                            video_bytes.append(base64.b64decode(v["bytesBase64Encoded"]))
                        except Exception:
                            logger.warning("Failed decoding base64 video segment")
                # Persist locally if we only have bytes
                local_paths: List[str] = []
                if video_bytes and not gcs_uris:
                    out_root = os.getenv("VIDEO_OUTPUT_DIR", "generated_videos")
                    op_short = operation_name.split('/')[-1][:16]
                    save_dir = os.path.join(out_root, op_short)
                    try:
                        os.makedirs(save_dir, exist_ok=True)
                        for i, data in enumerate(video_bytes):
                            file_path = os.path.join(save_dir, f"sample_{i}.mp4")
                            with open(file_path, 'wb') as f:
                                f.write(data)
                            local_paths.append(file_path)
                    except Exception as e:
                        logger.error("Failed saving video bytes locally: %s", e)
                return VeoOperationResult(
                    success=True,
                    job_id=operation_name,
                    model=model,
                    gcs_uris=gcs_uris,
                    video_bytes=video_bytes,
                    local_paths=local_paths,
                    raw_operation=op,
                )
            if time.time() - start > timeout:
                return VeoOperationResult(success=False, error="poll timeout")
            time.sleep(interval)

# Singleton
veo_video_service = VeoVideoGenerationService()
