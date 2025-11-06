"""Image Generation API routes (Imagen 3)"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify, session
from firebase_admin import firestore

from api.auth_routes import login_required
from middleware.csrf_protection import csrf_protect
from services.image_generation_service import (
    ImageGenerationService, 
    ImageGenerationResult,
    SafetyFilterError,
    PolicyViolationError,
    ImageGenerationError
)
from services.website_stats_service import WebsiteStatsService
from services.token_service import TokenService, InsufficientTokensError
from services.transaction_service import TransactionService, TransactionType

logger = logging.getLogger(__name__)

image_bp = Blueprint('image', __name__, url_prefix='/api/image')
website_stats_service = WebsiteStatsService()
db = firestore.client()
token_service = TokenService()
transaction_service = TransactionService()

IMAGE_GENERATION_COST = 1


@image_bp.route('/generate', methods=['POST'])
@login_required
@csrf_protect
def generate_image():
    """
    Generate a single portrait image from a text prompt.
    
    Request JSON:
    {
        "prompt": "A serene mountain landscape at sunset...",
        "save_to_firestore": true  // optional, default true
    }
    
    Response JSON:
    {
        "success": true,
        "image": {
            "image_url": "https://...",
            "gcs_uri": "gs://...",
            "base64_data": "base64...",
            "image_id": "uuid...",
            "prompt": "...",
            "aspect_ratio": "9:16",
            "generation_time_seconds": 3.45,
            "timestamp": "2025-10-25T12:00:00Z",
            "model": "imagen-3.0-generate-001"
        }
    }
    """
    try:
        # Get request data
        data = request.get_json()
        if not data:
            logger.warning("Empty request body received")
            return jsonify({
                "success": False,
                "error": "Request body is required"
            }), 400
        
        # Extract and validate prompt
        prompt = data.get('prompt', '').strip()
        if not prompt:
            logger.warning("Empty prompt received")
            return jsonify({
                "success": False,
                "error": "Prompt is required"
            }), 400
        
        # Get user info from session
        user_id = session.get('user_id')
        user_email = session.get('user_email', 'anonymous')

        if not user_id:
            return jsonify({
                "success": False,
                "error": "Authentication required"
            }), 401

        # Ensure user has enough tokens before attempting generation
        try:
            current_balance = token_service.get_balance(user_id)
        except Exception as e:
            logger.error(f"Failed to fetch token balance for {user_id}: {e}", exc_info=True)
            return jsonify({
                "success": False,
                "error": "Unable to verify token balance"
            }), 500

        if current_balance < IMAGE_GENERATION_COST:
            logger.warning(
                f"Insufficient tokens for image generation - user: {user_id}, balance: {current_balance}, required: {IMAGE_GENERATION_COST}"
            )
            return jsonify({
                "success": False,
                "error": "Insufficient tokens",
                "required": IMAGE_GENERATION_COST,
                "balance": current_balance
            }), 402

        logger.info(f"Image generation request from user {user_email} - prompt: '{prompt[:100]}...'")
        
        # Initialize service and generate image
        generation_successful = False
        try:
            service = ImageGenerationService()
            result = service.generate_image(
                prompt=prompt,
                user_id=user_id,
                save_to_gcs=True
            )
            
            # Mark as successful ONLY if we got a valid result
            generation_successful = True
            logger.info(f"Image generated successfully - ID: {result.image_id}, time: {result.generation_time_seconds:.2f}s")
            
        except SafetyFilterError as e:
            # Safety filter blocked the generation - DO NOT deduct credits
            logger.warning(f"Image generation blocked by safety filter for user {user_email}: {str(e)}")
            return jsonify({
                "success": False,
                "error": str(e),
                "error_type": "safety_filter",
                "should_deduct_credits": False,
                "message": "Your prompt was blocked by content safety filters. Please try a different prompt."
            }), 400
            
        except PolicyViolationError as e:
            # Policy violation - DO NOT deduct credits
            logger.warning(f"Image generation blocked by policy violation for user {user_email}: {str(e)}")
            return jsonify({
                "success": False,
                "error": str(e),
                "error_type": "policy_violation",
                "should_deduct_credits": False,
                "message": "Your prompt violates content policies. Please modify your prompt and try again."
            }), 400
            
        except ValueError as e:
            # Validation error (empty prompt, etc) - DO NOT deduct credits
            logger.warning(f"Validation error: {str(e)}")
            return jsonify({
                "success": False,
                "error": str(e),
                "error_type": "validation_error",
                "should_deduct_credits": False
            }), 400
            
        except ImageGenerationError as e:
            # Other image generation errors - DO NOT deduct credits
            logger.error(f"Image generation error: {str(e)}", exc_info=True)
            return jsonify({
                "success": False,
                "error": str(e),
                "error_type": "generation_error",
                "should_deduct_credits": False
            }), 500
            
        except Exception as e:
            # Unexpected errors - DO NOT deduct credits
            logger.error(f"Unexpected error during image generation: {str(e)}", exc_info=True)
            return jsonify({
                "success": False,
                "error": f"Image generation failed: {str(e)}",
                "error_type": "unexpected_error",
                "should_deduct_credits": False
            }), 500
        
        # At this point, generation was successful and credits SHOULD be deducted
        deduction_performed = False
        balance_after_deduction = None
        try:
            token_service.deduct_tokens(
                user_id=user_id,
                amount=IMAGE_GENERATION_COST,
                reason='image_generation'
            )
            deduction_performed = True
            balance_after_deduction = token_service.get_balance(user_id)
            logger.info(
                f"Deducted {IMAGE_GENERATION_COST} token(s) from {user_id} for image generation"
            )
        except InsufficientTokensError as e:
            logger.warning(f"Insufficient tokens during deduction for user {user_id}: {e}")
            return jsonify({
                "success": False,
                "error": "Insufficient tokens",
                "required": IMAGE_GENERATION_COST
            }), 402
        except Exception as e:
            logger.error(f"Failed to deduct tokens for {user_id}: {e}", exc_info=True)
            return jsonify({
                "success": False,
                "error": "Failed to deduct tokens"
            }), 500

        # Save to Firestore if requested (using 'creations' collection for social platform)
        save_to_firestore = data.get('save_to_firestore', True)
        firestore_doc_id = None

        if save_to_firestore and user_id:
            try:
                # Get username from user document for denormalization (feed performance)
                user_ref = db.collection('users').document(user_id)
                user_doc = user_ref.get()

                if not user_doc.exists:
                    logger.warning(f"User document not found for {user_id}")
                    username = 'unknown'
                else:
                    user_data = user_doc.to_dict()
                    username = user_data.get('username', 'unknown')

                # Create document in 'creations' collection (social platform schema)
                creation_data = {
                    'creationId': result.image_id,
                    'userId': user_id,
                    'username': username,  # Denormalized for explore feed performance

                    # Content metadata
                    'mediaType': 'image',  # Distinguish from videos
                    'mediaUrl': result.image_url,
                    'thumbnailUrl': result.image_url,
                    'prompt': prompt,
                    'caption': '',  # Empty initially - user can add later

                    # Image-specific fields
                    'aspectRatio': result.aspect_ratio,
                    'generationTimeSeconds': result.generation_time_seconds,
                    'model': result.model,

                    # Social platform fields
                    'status': 'draft',  # Users must publish manually from drafts
                    'likeCount': 0,

                    # Timestamps
                    'createdAt': firestore.SERVER_TIMESTAMP,
                    'updatedAt': firestore.SERVER_TIMESTAMP
                }

                creation_ref = db.collection('creations').document(result.image_id)
                creation_ref.set(creation_data)
                firestore_doc_id = result.image_id

                logger.info(f"Saved image as creation to social platform: {firestore_doc_id} (username: {username})")

            except Exception as e:
                logger.error(f"Failed to save creation to Firestore: {str(e)}", exc_info=True)
                if deduction_performed:
                    try:
                        token_service.add_tokens(
                            user_id=user_id,
                            amount=IMAGE_GENERATION_COST,
                            reason='image_generation_refund'
                        )
                        transaction_service.record_transaction(
                            user_id=user_id,
                            transaction_type=TransactionType.REFUND,
                            amount=IMAGE_GENERATION_COST,
                            details={
                                'mediaType': 'image',
                                'reason': 'firestore_save_failure'
                            }
                        )
                        deduction_performed = False
                        logger.info(f"Refunded {IMAGE_GENERATION_COST} token(s) to {user_id} after Firestore failure")
                    except Exception as refund_error:
                        logger.error(
                            f"Failed to refund tokens after Firestore error for {user_id}: {refund_error}",
                            exc_info=True
                        )
                return jsonify({
                    "success": False,
                    "error": "Failed to save creation"
                }), 500

        # Record token transaction after successful deduction (and optional Firestore save)
        if deduction_performed:
            try:
                transaction_service.record_transaction(
                    user_id=user_id,
                    transaction_type=TransactionType.GENERATION_SPEND,
                    amount=-IMAGE_GENERATION_COST,
                    details={
                        'mediaType': 'image',
                        'creationId': result.image_id,
                        'promptPreview': prompt[:120]
                    },
                    balance_after=balance_after_deduction
                )
            except Exception as e:
                logger.error(f"Failed to record generation transaction for {user_id}: {e}", exc_info=True)
        
        # Increment stats counter ONLY for successful generations
        try:
            website_stats_service.increment_images_generated(1)
            logger.info("Incremented images generated counter (generation was successful)")
        except Exception as e:
            # Don't fail the request if stats update fails
            logger.error(f"Failed to increment stats: {str(e)}", exc_info=True)
        
        # Return success response with explicit credit deduction flag
        response_data = {
            "success": True,
            "should_deduct_credits": True,  # IMPORTANT: Only returned on successful generation
            "image": result.to_dict()
        }
        
        if firestore_doc_id:
            response_data["firestore_doc_id"] = firestore_doc_id
        
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"Unexpected error in generate_image endpoint: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "error": "An unexpected error occurred"
        }), 500


@image_bp.route('/validate-prompt', methods=['POST'])
@login_required
def validate_prompt():
    """
    Validate a prompt before generation (optional pre-check).
    
    Request JSON:
    {
        "prompt": "..."
    }
    
    Response JSON:
    {
        "valid": true,
        "error": null
    }
    """
    try:
        data = request.get_json()
        prompt = data.get('prompt', '').strip()
        
        service = ImageGenerationService()
        is_valid, error_message = service.validate_prompt(prompt)
        
        return jsonify({
            "valid": is_valid,
            "error": error_message
        }), 200
        
    except Exception as e:
        logger.error(f"Error validating prompt: {str(e)}", exc_info=True)
        return jsonify({
            "valid": False,
            "error": "Validation failed"
        }), 500


@image_bp.route('/history', methods=['GET'])
@login_required
def get_history():
    """
    Get user's image generation history.
    
    Query params:
    - limit: Number of results (default 20, max 100)
    - offset: Pagination offset (default 0)
    
    Response JSON:
    {
        "success": true,
        "images": [...],
        "total": 45,
        "limit": 20,
        "offset": 0
    }
    """
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({
                "success": False,
                "error": "User not authenticated"
            }), 401
        
        # Get pagination params
        limit = min(int(request.args.get('limit', 20)), 100)
        offset = int(request.args.get('offset', 0))
        
        logger.info(f"Fetching image history for user {user_id} - limit: {limit}, offset: {offset}")
        
        # Query Firestore
        query = db.collection('image_generations') \
            .where('user_id', '==', user_id) \
            .order_by('created_at', direction=firestore.Query.DESCENDING) \
            .limit(limit) \
            .offset(offset)
        
        docs = query.stream()
        
        images = []
        for doc in docs:
            data = doc.to_dict()
            images.append({
                'id': doc.id,
                'image_id': data.get('image_id'),
                'prompt': data.get('prompt'),
                'image_url': data.get('image_url'),
                'gcs_uri': data.get('gcs_uri'),
                'aspect_ratio': data.get('aspect_ratio'),
                'model': data.get('model'),
                'generation_time_seconds': data.get('generation_time_seconds'),
                'timestamp': data.get('timestamp'),
                'status': data.get('status', 'generated')
            })
        
        # Get total count (expensive operation, consider caching)
        total_query = db.collection('image_generations').where('user_id', '==', user_id)
        total = len(list(total_query.stream()))
        
        logger.info(f"Retrieved {len(images)} images (total: {total})")
        
        return jsonify({
            "success": True,
            "images": images,
            "total": total,
            "limit": limit,
            "offset": offset
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching image history: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "error": "Failed to fetch history"
        }), 500


@image_bp.route('/<image_id>', methods=['GET'])
@login_required
def get_image(image_id):
    """
    Get a specific image by ID.
    
    Response JSON:
    {
        "success": true,
        "image": {...}
    }
    """
    try:
        user_id = session.get('user_id')
        
        # Fetch from Firestore
        doc_ref = db.collection('image_generations').document(image_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            logger.warning(f"Image not found: {image_id}")
            return jsonify({
                "success": False,
                "error": "Image not found"
            }), 404
        
        data = doc.to_dict()
        
        # Check ownership
        if data.get('user_id') != user_id:
            logger.warning(f"Unauthorized access attempt for image {image_id} by user {user_id}")
            return jsonify({
                "success": False,
                "error": "Unauthorized"
            }), 403
        
        return jsonify({
            "success": True,
            "image": {
                'id': doc.id,
                'image_id': data.get('image_id'),
                'prompt': data.get('prompt'),
                'image_url': data.get('image_url'),
                'gcs_uri': data.get('gcs_uri'),
                'aspect_ratio': data.get('aspect_ratio'),
                'model': data.get('model'),
                'generation_time_seconds': data.get('generation_time_seconds'),
                'timestamp': data.get('timestamp'),
                'status': data.get('status', 'generated')
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching image: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "error": "Failed to fetch image"
        }), 500


@image_bp.route('/<image_id>', methods=['DELETE'])
@login_required
@csrf_protect
def delete_image(image_id):
    """
    Delete an image (soft delete - marks as deleted in Firestore).
    
    Response JSON:
    {
        "success": true,
        "message": "Image deleted"
    }
    """
    try:
        user_id = session.get('user_id')
        
        # Fetch from Firestore
        doc_ref = db.collection('image_generations').document(image_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            logger.warning(f"Image not found for deletion: {image_id}")
            return jsonify({
                "success": False,
                "error": "Image not found"
            }), 404
        
        data = doc.to_dict()
        
        # Check ownership
        if data.get('user_id') != user_id:
            logger.warning(f"Unauthorized delete attempt for image {image_id} by user {user_id}")
            return jsonify({
                "success": False,
                "error": "Unauthorized"
            }), 403
        
        # Soft delete - update status
        doc_ref.update({
            'status': 'deleted',
            'deleted_at': firestore.SERVER_TIMESTAMP
        })
        
        logger.info(f"Image {image_id} marked as deleted by user {user_id}")
        
        return jsonify({
            "success": True,
            "message": "Image deleted successfully"
        }), 200
        
    except Exception as e:
        logger.error(f"Error deleting image: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "error": "Failed to delete image"
        }), 500


# Health check endpoint (no auth required)
@image_bp.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint to verify the image generation service is ready.
    """
    try:
        # Quick validation that we can initialize the service
        service = ImageGenerationService()
        
        return jsonify({
            "status": "healthy",
            "service": "image_generation",
            "model": "imagen-3.0-generate-001",
            "timestamp": datetime.utcnow().isoformat() + 'Z'
        }), 200
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}", exc_info=True)
        return jsonify({
            "status": "unhealthy",
            "error": str(e)
        }), 503
