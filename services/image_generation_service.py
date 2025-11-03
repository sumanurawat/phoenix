"""Image Generation Service

Provides a typed wrapper around the Vertex AI Imagen 3 API for image generation.
Handles:
 - Request construction with hardcoded sensible defaults
 - Single portrait image generation (9:16 aspect ratio)
 - Lowest safety restrictions for unrestricted content
 - Cloudflare R2 storage integration ($0 egress for future video platform)
 - Production-grade logging and error handling

Configuration:
 - Hardcoded to 1 image per generation
 - Portrait orientation (9:16)
 - Lowest safety filter (block_few)
 - No person generation restrictions (allow_all)
 - No negative prompts
"""
from __future__ import annotations

import os
import time
import json
import base64
import logging
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid

import boto3
from botocore.exceptions import ClientError
from vertexai.preview.vision_models import ImageGenerationModel
import vertexai

from config.settings import (
    DEFAULT_IMAGE_ASPECT_RATIO,
    IMAGE_SAFETY_FILTER,
    IMAGE_PERSON_GENERATION,
    R2_ACCESS_KEY_ID,
    R2_SECRET_ACCESS_KEY,
    R2_ENDPOINT_URL,
    R2_BUCKET_NAME,
    R2_PUBLIC_URL
)

logger = logging.getLogger(__name__)

# Imagen 3 Model
IMAGEN_MODEL = "imagen-3.0-generate-001"


class ImageGenerationError(Exception):
    """Base exception for image generation failures."""
    pass


class SafetyFilterError(ImageGenerationError):
    """Raised when image generation is blocked by safety filters."""
    pass


class PolicyViolationError(ImageGenerationError):
    """Raised when prompt violates Google's content policies."""
    pass


@dataclass
class ImageGenerationResult:
    """Result from image generation with all relevant metadata."""
    image_url: str
    gcs_uri: str
    base64_data: str
    prompt: str
    aspect_ratio: str
    generation_time_seconds: float
    image_id: str
    timestamp: str
    model: str = IMAGEN_MODEL
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


class ImageGenerationService:
    """
    Service for generating images using Google Vertex AI Imagen 3.
    
    Configured for:
    - Single image generation per request
    - Portrait orientation (9:16)
    - Minimal safety restrictions
    - Automatic R2 storage
    """
    
    def __init__(self, project_id: str = None, location: str = "us-central1"):
        """
        Initialize the image generation service.
        
        Args:
            project_id: GCP project ID (defaults to application default)
            location: GCP region for Vertex AI
        """
        self.project_id = project_id or os.getenv("GCP_PROJECT_ID")
        self.location = location
        self.bucket_name = R2_BUCKET_NAME
        self.r2_public_url = R2_PUBLIC_URL
        
        # Initialize Vertex AI
        try:
            vertexai.init(project=self.project_id, location=self.location)
            logger.info(f"Initialized Vertex AI for project {self.project_id} in {self.location}")
        except Exception as e:
            logger.error(f"Failed to initialize Vertex AI: {str(e)}", exc_info=True)
            raise
        
        # Initialize R2/S3 client (replacing GCS)
        try:
            # Cloudflare R2 is S3-compatible but requires special session configuration
            # Create a boto3 session first, then use it to create the client
            import boto3.session

            # Create session with credentials
            session = boto3.session.Session(
                aws_access_key_id=R2_ACCESS_KEY_ID,
                aws_secret_access_key=R2_SECRET_ACCESS_KEY
            )

            # Create S3 client from session with R2 endpoint
            # R2 requires specific configuration to bypass boto3's endpoint validation
            from botocore.config import Config
            
            self.s3_client = session.client(
                's3',
                endpoint_url=R2_ENDPOINT_URL,
                region_name='auto',  # R2 uses 'auto' region
                config=Config(
                    signature_version='s3v4',
                    s3={
                        'addressing_style': 'path',  # Use path-style addressing
                    }
                ),
                verify=True  # Keep SSL verification enabled
            )

            logger.info(f"Initialized Cloudflare R2 client for bucket: {self.bucket_name}")
            logger.info(f"R2 endpoint: {R2_ENDPOINT_URL}")
            logger.info(f"R2 public URL base: {self.r2_public_url}")
        except Exception as e:
            logger.error(f"Failed to initialize R2 client: {str(e)}", exc_info=True)
            raise
        
        # Load Imagen 3 model
        try:
            self.model = ImageGenerationModel.from_pretrained(IMAGEN_MODEL)
            logger.info(f"Loaded Imagen 3 model: {IMAGEN_MODEL}")
        except Exception as e:
            logger.error(f"Failed to load Imagen model: {str(e)}", exc_info=True)
            raise
    
    def generate_image(
        self,
        prompt: str,
        user_id: str = None,
        save_to_gcs: bool = True
    ) -> ImageGenerationResult:
        """
        Generate a single portrait image from a text prompt.
        
        Args:
            prompt: Text description of the image to generate
            user_id: User ID for organizing storage (optional)
            save_to_gcs: Whether to save to R2 (default True, param name kept for compatibility)
        
        Returns:
            ImageGenerationResult with image data and metadata
        
        Raises:
            ValueError: If prompt is empty
            SafetyFilterError: If generation blocked by safety filters (do NOT deduct credits)
            PolicyViolationError: If prompt violates content policies (do NOT deduct credits)
            ImageGenerationError: For other generation failures
        """
        if not prompt or not prompt.strip():
            logger.error("Empty prompt provided for image generation")
            raise ValueError("Prompt cannot be empty")
        
        logger.info(f"Starting image generation for prompt: '{prompt[:100]}...'")
        logger.info(f"User ID: {user_id}, Save to R2: {save_to_gcs}")
        start_time = time.time()
        
        try:
            # Generate image with hardcoded settings
            logger.debug(f"Generating with Imagen 3 - aspect_ratio: {DEFAULT_IMAGE_ASPECT_RATIO}, "
                        f"safety: {IMAGE_SAFETY_FILTER}, person_gen: {IMAGE_PERSON_GENERATION}")
            
            response = self.model.generate_images(
                prompt=prompt,
                number_of_images=1,  # Hardcoded: single image
                aspect_ratio=DEFAULT_IMAGE_ASPECT_RATIO,  # "9:16" (portrait)
                safety_filter_level=IMAGE_SAFETY_FILTER,  # "block_few"
                person_generation=IMAGE_PERSON_GENERATION,  # "allow_all"
            )
            
            # ImageGenerationResponse has .images attribute (list)
            if not response or not hasattr(response, 'images') or len(response.images) == 0:
                logger.error("No images returned from Imagen API")
                raise ImageGenerationError("Image generation returned no results")
            
            image = response.images[0]
            generation_time = time.time() - start_time
            logger.info(f"Image generation completed in {generation_time:.2f}s")
            
            # Validate successful generation
            if not hasattr(image, '_image_bytes') or not image._image_bytes:
                logger.error("Generated image has no image data")
                raise ImageGenerationError("Generated image is empty")
            
            # Get image bytes and encode to base64
            image_bytes = image._image_bytes
            base64_data = base64.b64encode(image_bytes).decode('utf-8')
            logger.debug(f"Image encoded to base64, size: {len(image_bytes)} bytes")
            
            # Generate unique ID
            image_id = str(uuid.uuid4())
            timestamp = datetime.utcnow().isoformat() + 'Z'
            
            # Save to R2 if requested
            if save_to_gcs:
                logger.info(f"Saving image {image_id} to Cloudflare R2...")
                image_url, gcs_uri = self._save_to_r2(
                    image_bytes=image_bytes,
                    image_id=image_id,
                    user_id=user_id,
                    prompt=prompt
                )
            else:
                logger.info("Skipping R2 storage (save_to_gcs=False)")
                image_url = f"data:image/png;base64,{base64_data}"
                gcs_uri = ""
            
            logger.info(f"Image generation fully completed - ID: {image_id}, URL: {image_url[:100]}...")
            
            return ImageGenerationResult(
                image_url=image_url,
                gcs_uri=gcs_uri,
                base64_data=base64_data,
                prompt=prompt,
                aspect_ratio=DEFAULT_IMAGE_ASPECT_RATIO,
                generation_time_seconds=generation_time,
                image_id=image_id,
                timestamp=timestamp,
                model=IMAGEN_MODEL
            )
            
        except Exception as e:
            generation_time = time.time() - start_time
            error_msg = str(e).lower()
            
            # Classify errors for credit deduction logic
            if 'safety' in error_msg or 'blocked' in error_msg:
                logger.warning(f"Image generation blocked by safety filter after {generation_time:.2f}s: {error_msg}")
                raise SafetyFilterError(f"Image generation blocked by safety filters: {str(e)}")
            
            if 'policy' in error_msg or 'violation' in error_msg or 'content' in error_msg:
                logger.warning(f"Image generation blocked by policy violation after {generation_time:.2f}s: {error_msg}")
                raise PolicyViolationError(f"Prompt violates content policy: {str(e)}")
            
            logger.error(f"Image generation failed after {generation_time:.2f}s: {str(e)}", exc_info=True)
            raise ImageGenerationError(f"Failed to generate image: {str(e)}")
    
    def _save_to_r2(
        self,
        image_bytes: bytes,
        image_id: str,
        user_id: str = None,
        prompt: str = None
    ) -> tuple[str, str]:
        """
        Save generated image to Cloudflare R2 storage.
        
        Args:
            image_bytes: Raw image data
            image_id: Unique identifier for the image
            user_id: User ID for organizing files (optional)
            prompt: Generation prompt for metadata (optional)
        
        Returns:
            Tuple of (public_url, r2_uri)
            
        Raises:
            ImageGenerationError: If upload fails
        """
        try:
            # Construct R2 object key (path within bucket)
            if user_id:
                blob_name = f"generated/{user_id}/{image_id}.png"
            else:
                blob_name = f"generated/{image_id}.png"
            
            logger.info(f"Uploading to R2: bucket={self.bucket_name}, key={blob_name}")
            logger.info(f"Image size: {len(image_bytes)} bytes ({len(image_bytes)/1024:.2f} KB)")
            
            # Prepare metadata
            metadata = {
                'image_id': image_id,
                'generated_at': datetime.utcnow().isoformat() + 'Z',
                'model': IMAGEN_MODEL,
                'aspect_ratio': DEFAULT_IMAGE_ASPECT_RATIO,
                'image_size_bytes': str(len(image_bytes))
            }
            if user_id:
                metadata['user_id'] = user_id
            if prompt:
                # Truncate prompt to avoid metadata size limits
                metadata['prompt'] = prompt[:500] if len(prompt) > 500 else prompt
            
            logger.debug(f"Upload metadata: {json.dumps(metadata, indent=2)}")
            
            # Upload to R2 using S3 API
            upload_start = time.time()
            try:
                self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=blob_name,
                    Body=image_bytes,
                    ContentType='image/png',
                    Metadata=metadata
                )
                upload_time = time.time() - upload_start
                logger.info(f"R2 upload completed in {upload_time:.2f}s")
            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', 'Unknown')
                error_msg = e.response.get('Error', {}).get('Message', str(e))
                logger.error(f"R2 ClientError during upload: {error_code} - {error_msg}", exc_info=True)
                raise ImageGenerationError(f"Failed to upload to R2: {error_code} - {error_msg}")
            except Exception as e:
                logger.error(f"Unexpected error during R2 upload: {str(e)}", exc_info=True)
                raise ImageGenerationError(f"Failed to upload to R2: {str(e)}")
            
            # Construct public URL
            public_url = f"{self.r2_public_url}/{blob_name}"
            r2_uri = f"r2://{self.bucket_name}/{blob_name}"
            
            logger.info(f"Image saved successfully - Public URL: {public_url}")
            logger.debug(f"R2 URI: {r2_uri}")
            
            return public_url, r2_uri
            
        except ImageGenerationError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error saving to R2: {str(e)}", exc_info=True)
            raise ImageGenerationError(f"Failed to save image to R2: {str(e)}")
