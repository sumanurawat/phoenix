"""Creation Service - Unified Draft-First Content Management

Centralizes all creation state management and financial logic for both
image and video generation. Ensures consistent transaction handling,
token debiting/refunding, and creation document lifecycle.

This service is the single source of truth for:
- Creating pending drafts with atomic token debit
- Handling generation failures with automatic refunds
- Managing creation status transitions
"""
import logging
import uuid
from typing import Dict, Tuple, Optional
from datetime import datetime
from firebase_admin import firestore

from services.token_service import TokenService, InsufficientTokensError
from services.transaction_service import TransactionService, TransactionType

logger = logging.getLogger(__name__)

# Generation costs
IMAGE_GENERATION_COST = 1
VIDEO_GENERATION_COST = 10


class CreationService:
    """Unified service for managing content creation lifecycle."""

    def __init__(self):
        self.db = firestore.client()
        self.token_service = TokenService()
        self.transaction_service = TransactionService()

    def create_pending_creation(
        self,
        user_id: str,
        prompt: str,
        creation_type: str,
        username: Optional[str] = None,
        **extra_params
    ) -> Tuple[str, str]:
        """
        Create a pending creation with atomic token debit.

        This method runs in a Firestore transaction to ensure atomicity:
        - Check token balance
        - Debit tokens
        - Create creation document
        - Record transaction

        Args:
            user_id: Firebase UID of the user
            prompt: User's prompt text
            creation_type: 'image' or 'video'
            username: Optional username (fetched if not provided)
            **extra_params: Additional params (aspectRatio, duration, etc.)

        Returns:
            Tuple[str, str]: (creation_id, transaction_id) for refunds

        Raises:
            ValueError: Invalid creation type or parameters
            InsufficientTokensError: User doesn't have enough tokens
        """
        # Validate creation type
        if creation_type not in ['image', 'video']:
            raise ValueError(f"Invalid creation type: {creation_type}")

        # Determine cost
        cost = IMAGE_GENERATION_COST if creation_type == 'image' else VIDEO_GENERATION_COST

        # Validate prompt
        if not prompt or not prompt.strip():
            raise ValueError("Prompt is required")

        if len(prompt) > 500:
            raise ValueError("Prompt must be 500 characters or less")

        # Generate IDs
        creation_id = str(uuid.uuid4())
        transaction_id = str(uuid.uuid4())

        # Fetch username if not provided
        if not username:
            try:
                user_ref = self.db.collection('users').document(user_id)
                user_doc = user_ref.get()
                if user_doc.exists:
                    username = user_doc.to_dict().get('username', 'unknown')
                else:
                    username = 'unknown'
            except Exception as e:
                logger.warning(f"Failed to fetch username for {user_id}: {e}")
                username = 'unknown'

        # Define transactional operation
        @firestore.transactional
        def create_and_debit(transaction):
            user_ref = self.db.collection('users').document(user_id)
            creation_ref = self.db.collection('creations').document(creation_id)
            transaction_ref = self.db.collection('transactions').document(transaction_id)

            # 1. Check balance (within transaction for consistency)
            user_doc = user_ref.get(transaction=transaction)
            if not user_doc.exists:
                raise ValueError(f"User {user_id} not found")

            user_data = user_doc.to_dict()
            balance = user_data.get('tokenBalance', 0)

            if balance < cost:
                raise InsufficientTokensError(
                    f"Insufficient tokens: {balance} < {cost}"
                )

            # 2. Debit tokens atomically
            transaction.update(user_ref, {
                'tokenBalance': firestore.Increment(-cost),
                'totalTokensSpent': firestore.Increment(cost)
            })

            # 3. Create creation document (visible in drafts immediately)
            creation_data = {
                'creationId': creation_id,
                'userId': user_id,
                'username': username,
                'prompt': prompt,
                'mediaType': creation_type,
                'status': 'pending',
                'cost': cost,
                'createdAt': firestore.SERVER_TIMESTAMP,
                'updatedAt': firestore.SERVER_TIMESTAMP,
                # Add caption field for draft workflow
                'caption': '',
                # Social platform fields
                'likeCount': 0,
            }

            # Add type-specific params
            if creation_type == 'video':
                creation_data['aspectRatio'] = extra_params.get('aspectRatio', '9:16')
                creation_data['duration'] = extra_params.get('duration', 8)
                creation_data['progress'] = 0.0
            elif creation_type == 'image':
                creation_data['aspectRatio'] = extra_params.get('aspectRatio', '9:16')

            transaction.set(creation_ref, creation_data)

            # 4. Record transaction
            transaction.set(transaction_ref, {
                'userId': user_id,
                'type': f'{creation_type}_generation',
                'amount': -cost,
                'timestamp': firestore.SERVER_TIMESTAMP,
                'details': {
                    'creationId': creation_id,
                    'prompt': prompt[:100]  # Truncate for storage
                }
            })

            logger.info(
                f"✅ Created pending {creation_type} creation {creation_id} "
                f"and debited {cost} tokens from {user_id}"
            )

        # Execute transaction
        try:
            transaction = self.db.transaction()
            create_and_debit(transaction)
            return creation_id, transaction_id

        except InsufficientTokensError:
            logger.warning(
                f"Insufficient tokens for {user_id}: "
                f"needs {cost} for {creation_type} generation"
            )
            raise

        except Exception as e:
            logger.error(
                f"Failed to create pending creation for {user_id}: {e}",
                exc_info=True
            )
            raise

    def handle_generation_failure(
        self,
        creation_id: str,
        original_transaction_id: str,
        error_message: str,
        user_id: Optional[str] = None
    ) -> bool:
        """
        Handle generation failure: update status, refund tokens.

        This method is idempotent - can be called multiple times safely.

        Args:
            creation_id: UUID of the failed creation
            original_transaction_id: Transaction ID from create_pending_creation
            error_message: Error description
            user_id: Optional user ID (fetched from creation if not provided)

        Returns:
            bool: True if handled successfully, False otherwise
        """
        try:
            creation_ref = self.db.collection('creations').document(creation_id)

            # Fetch creation to get user_id and cost if needed
            creation_doc = creation_ref.get()
            if not creation_doc.exists:
                logger.error(f"Cannot handle failure - creation {creation_id} not found")
                return False

            creation_data = creation_doc.to_dict()

            # Check if already refunded (idempotency)
            if creation_data.get('refunded'):
                logger.info(f"⚠️ Creation {creation_id} already refunded - skipping")
                return True

            # Get user_id and cost from creation
            if not user_id:
                user_id = creation_data.get('userId')

            cost = creation_data.get('cost', 0)

            if not user_id:
                logger.error(f"Cannot refund - user_id missing for creation {creation_id}")
                return False

            # Perform refund in transaction
            @firestore.transactional
            def refund_transaction(transaction):
                user_ref = self.db.collection('users').document(user_id)
                refund_transaction_ref = self.db.collection('transactions').document()

                # 1. Update creation status
                transaction.update(creation_ref, {
                    'status': 'failed',
                    'error': error_message[:500],  # Truncate long errors
                    'refunded': True,
                    'refundedAt': firestore.SERVER_TIMESTAMP,
                    'updatedAt': firestore.SERVER_TIMESTAMP
                })

                # 2. Refund tokens atomically
                transaction.update(user_ref, {
                    'tokenBalance': firestore.Increment(cost),
                    'totalTokensSpent': firestore.Increment(-cost)
                })

                # 3. Log refund transaction
                transaction.set(refund_transaction_ref, {
                    'userId': user_id,
                    'type': f'{creation_data.get("mediaType", "unknown")}_generation_refund',
                    'amount': cost,
                    'timestamp': firestore.SERVER_TIMESTAMP,
                    'details': {
                        'creationId': creation_id,
                        'originalTransactionId': original_transaction_id,
                        'reason': 'generation_failed',
                        'error': error_message[:200]
                    }
                })

            # Execute refund transaction
            transaction = self.db.transaction()
            refund_transaction(transaction)

            logger.info(
                f"💰 Refunded {cost} tokens to user {user_id} "
                f"for failed creation {creation_id}"
            )
            return True

        except Exception as e:
            logger.error(
                f"Failed to handle generation failure for {creation_id}: {e}",
                exc_info=True
            )
            return False

    def update_creation_status(
        self,
        creation_id: str,
        status: str,
        **extra_fields
    ) -> bool:
        """
        Update creation status and additional fields.

        Args:
            creation_id: UUID of the creation
            status: New status (pending, processing, draft, published, failed)
            **extra_fields: Additional fields to update (mediaUrl, thumbnailUrl, etc.)

        Returns:
            bool: True if update successful, False otherwise
        """
        try:
            creation_ref = self.db.collection('creations').document(creation_id)

            update_data = {
                'status': status,
                'updatedAt': firestore.SERVER_TIMESTAMP
            }

            # Add extra fields
            update_data.update(extra_fields)

            # Update atomically
            creation_ref.update(update_data)

            logger.info(
                f"📝 Updated creation {creation_id} status: {status}"
            )
            return True

        except Exception as e:
            logger.error(
                f"Failed to update creation {creation_id} status: {e}",
                exc_info=True
            )
            return False

    def mark_stale_creations_as_failed(self, max_age_hours: float = 1.0) -> int:
        """
        Find and mark stale creations (stuck in pending/processing) as failed.
        
        Args:
            max_age_hours: Maximum age in hours before marking as stale (default: 1 hour)
            
        Returns:
            int: Number of creations marked as failed
        """
        from datetime import datetime, timezone, timedelta
        
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
            marked_count = 0
            
            # Check pending creations
            for status in ['pending', 'processing']:
                query = self.db.collection('creations').where('status', '==', status)
                
                for doc in query.stream():
                    data = doc.to_dict()
                    created_at = data.get('createdAt')
                    
                    if not created_at:
                        continue
                    
                    # Parse timestamp
                    if isinstance(created_at, datetime):
                        created_time = created_at
                    elif hasattr(created_at, 'seconds'):
                        created_time = datetime.fromtimestamp(created_at.seconds, tz=timezone.utc)
                    else:
                        continue
                    
                    # Check if stale
                    if created_time < cutoff_time:
                        age_hours = (datetime.now(timezone.utc) - created_time).total_seconds() / 3600
                        
                        # Mark as failed
                        success = self.mark_failed(
                            creation_id=doc.id,
                            user_id=data.get('userId'),
                            error_message=f"Generation timeout: Task stuck in {status} status for {age_hours:.1f} hours"
                        )
                        
                        if success:
                            marked_count += 1
                            logger.info(f"⏰ Marked stale creation {doc.id} as failed (age: {age_hours:.1f}h)")
            
            if marked_count > 0:
                logger.info(f"✅ Marked {marked_count} stale creations as failed")
            
            return marked_count
            
        except Exception as e:
            logger.error(f"Failed to mark stale creations: {e}", exc_info=True)
            return 0

    def get_creation(self, creation_id: str) -> Optional[Dict]:
        """
        Get creation document by ID.

        Args:
            creation_id: UUID of the creation

        Returns:
            Optional[Dict]: Creation data or None if not found
        """
        try:
            creation_ref = self.db.collection('creations').document(creation_id)
            creation_doc = creation_ref.get()

            if creation_doc.exists:
                return creation_doc.to_dict()
            return None

        except Exception as e:
            logger.error(f"Failed to get creation {creation_id}: {e}", exc_info=True)
            return None

