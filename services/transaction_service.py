"""Transaction Ledger Service

Maintains an immutable financial record of all token movements in the system.
Every token transaction (purchase, spend, tip, etc.) is recorded here permanently.

This provides:
- Complete audit trail
- Transaction history for users
- Analytics data for the platform
- Dispute resolution capability
"""
from __future__ import annotations

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from google.cloud import firestore
from firebase_admin import firestore as admin_firestore

logger = logging.getLogger(__name__)


class TransactionType:
    """Transaction type constants."""
    PURCHASE = "purchase"  # User bought tokens via Stripe
    GENERATION_SPEND = "generation_spend"  # User spent tokens to generate image
    TIP_SENT = "tip_sent"  # User sent tip to creator
    TIP_RECEIVED = "tip_received"  # User received tip from another user
    SIGNUP_BONUS = "signup_bonus"  # Free tokens on account creation
    ADMIN_CREDIT = "admin_credit"  # Manually credited by admin
    REFUND = "refund"  # Tokens refunded


class TransactionService:
    """
    Service for recording and querying token transactions.
    
    All transactions are immutable - once created, they are never modified or deleted.
    This ensures a perfect audit trail of the entire token economy.
    """
    
    def __init__(self, db: firestore.Client = None):
        """
        Initialize transaction service.
        
        Args:
            db: Firestore client instance (uses default if not provided)
        """
        self.db = db or admin_firestore.client()
        self.collection = 'transactions'
        logger.info("TransactionService initialized")
    
    def record_transaction(
        self,
        user_id: str,
        transaction_type: str,
        amount: int,
        details: Optional[Dict[str, Any]] = None,
        balance_after: Optional[int] = None
    ) -> str:
        """
        Record a new transaction in the immutable ledger.

        Args:
            user_id: Firebase Auth UID of user involved in transaction
            transaction_type: Type of transaction (use TransactionType constants)
            amount: Number of tokens moved (positive for credits, negative for debits)
            details: Additional context-specific information (optional)
            balance_after: User's token balance after this transaction (optional but recommended)

        Returns:
            Transaction document ID

        Raises:
            ValueError: If transaction data is invalid
        """
        if not user_id:
            raise ValueError("user_id is required")

        if transaction_type not in [
            TransactionType.PURCHASE,
            TransactionType.GENERATION_SPEND,
            TransactionType.TIP_SENT,
            TransactionType.TIP_RECEIVED,
            TransactionType.SIGNUP_BONUS,
            TransactionType.ADMIN_CREDIT,
            TransactionType.REFUND
        ]:
            logger.warning(f"Unknown transaction type: {transaction_type}")

        try:
            # Get current balance if not provided
            if balance_after is None:
                from services.token_service import TokenService
                token_service = TokenService()
                balance_after = token_service.get_balance(user_id)
                logger.debug(f"Fetched current balance for transaction: {balance_after}")

            transaction_data = {
                'userId': user_id,
                'type': transaction_type,
                'amount': amount,
                'balanceAfter': balance_after,
                'timestamp': admin_firestore.SERVER_TIMESTAMP,
                'details': details or {}
            }

            # Create document with auto-generated ID
            doc_ref = self.db.collection(self.collection).document()
            doc_ref.set(transaction_data)

            logger.info(
                f"Recorded transaction: {transaction_type} | "
                f"User: {user_id} | Amount: {amount} | Balance After: {balance_after} | ID: {doc_ref.id}"
            )

            return doc_ref.id

        except Exception as e:
            logger.error(
                f"Failed to record transaction for {user_id}: {str(e)}",
                exc_info=True
            )
            raise
    
    def record_purchase(
        self,
        user_id: str,
        amount: int,
        package_id: str,
        stripe_session_id: str,
        stripe_customer_id: str,
        amount_paid: float,
        balance_after: int = None
    ) -> str:
        """
        Record a token purchase via Stripe.

        Args:
            user_id: Firebase Auth UID
            amount: Number of tokens purchased
            package_id: Token package identifier (starter, popular, pro, creator)
            stripe_session_id: Stripe checkout session ID
            stripe_customer_id: Stripe customer ID
            amount_paid: Amount paid in USD
            balance_after: User's balance after purchase (optional, will be fetched if not provided)

        Returns:
            Transaction document ID
        """
        return self.record_transaction(
            user_id=user_id,
            transaction_type=TransactionType.PURCHASE,
            amount=amount,
            balance_after=balance_after,
            details={
                'packageId': package_id,
                'stripeSessionId': stripe_session_id,
                'stripeCustomerId': stripe_customer_id,
                'paymentAmountUSD': amount_paid
            }
        )
    
    def get_by_stripe_session(self, stripe_session_id: str) -> Optional[Dict[str, Any]]:
        """
        Check if a Stripe session has already been processed (idempotency check).
        
        Args:
            stripe_session_id: Stripe checkout session ID
            
        Returns:
            Transaction data if found, None otherwise
        """
        try:
            query = self.db.collection(self.collection)\
                .where('details.stripeSessionId', '==', stripe_session_id)\
                .limit(1)
            
            results = list(query.stream())
            
            if results:
                tx_data = results[0].to_dict()
                tx_data['id'] = results[0].id
                logger.info(f"Found existing transaction for session {stripe_session_id}")
                return tx_data
            
            return None
            
        except Exception as e:
            logger.error(f"Error checking Stripe session {stripe_session_id}: {e}", exc_info=True)
            return None
    
    def record_generation_spend(
        self,
        user_id: str,
        amount: int,
        post_id: str,
        prompt: str
    ) -> str:
        """
        Record tokens spent on image generation.
        
        Args:
            user_id: Firebase Auth UID
            amount: Number of tokens spent (will be negative)
            post_id: ID of the generated post
            prompt: The prompt used for generation
            
        Returns:
            Transaction document ID
        """
        return self.record_transaction(
            user_id=user_id,
            transaction_type=TransactionType.GENERATION_SPEND,
            amount=-abs(amount),  # Ensure negative
            details={
                'postId': post_id,
                'prompt': prompt[:200]  # Truncate to avoid size limits
            }
        )
    
    def record_tip(
        self,
        sender_id: str,
        recipient_id: str,
        amount: int,
        post_id: str
    ) -> tuple[str, str]:
        """
        Record a tip transaction (creates two records: sent and received).
        
        Args:
            sender_id: Firebase Auth UID of tipper
            recipient_id: Firebase Auth UID of creator
            amount: Number of tokens tipped
            post_id: ID of the post being tipped for
            
        Returns:
            Tuple of (sender_transaction_id, recipient_transaction_id)
        """
        # Record debit for sender
        sender_tx_id = self.record_transaction(
            user_id=sender_id,
            transaction_type=TransactionType.TIP_SENT,
            amount=-abs(amount),  # Negative for sender
            details={
                'recipientId': recipient_id,
                'postId': post_id
            }
        )
        
        # Record credit for recipient
        recipient_tx_id = self.record_transaction(
            user_id=recipient_id,
            transaction_type=TransactionType.TIP_RECEIVED,
            amount=abs(amount),  # Positive for recipient
            details={
                'senderId': sender_id,
                'postId': post_id
            }
        )
        
        return sender_tx_id, recipient_tx_id
    
    def record_signup_bonus(self, user_id: str, amount: int) -> str:
        """
        Record free tokens given on signup.
        
        Args:
            user_id: Firebase Auth UID
            amount: Number of free tokens
            
        Returns:
            Transaction document ID
        """
        return self.record_transaction(
            user_id=user_id,
            transaction_type=TransactionType.SIGNUP_BONUS,
            amount=amount,
            details={'reason': 'Welcome bonus'}
        )
    
    def get_user_transactions(
        self,
        user_id: str,
        limit: int = 50,
        transaction_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get transaction history for a user.
        
        Args:
            user_id: Firebase Auth UID
            limit: Maximum number of transactions to return
            transaction_type: Filter by specific type (optional)
            
        Returns:
            List of transaction dictionaries, newest first
        """
        try:
            query = self.db.collection(self.collection).where('userId', '==', user_id)
            
            if transaction_type:
                query = query.where('type', '==', transaction_type)
            
            query = query.order_by('timestamp', direction=firestore.Query.DESCENDING)
            query = query.limit(limit)
            
            transactions = []
            for doc in query.stream():
                tx_data = doc.to_dict()
                tx_data['id'] = doc.id
                
                # Convert timestamp to ISO string for JSON serialization
                if 'timestamp' in tx_data and tx_data['timestamp']:
                    tx_data['timestamp'] = tx_data['timestamp'].isoformat()
                
                transactions.append(tx_data)
            
            logger.debug(f"Retrieved {len(transactions)} transactions for user {user_id}")
            return transactions
            
        except Exception as e:
            logger.error(
                f"Failed to get transactions for {user_id}: {str(e)}",
                exc_info=True
            )
            return []
    
    def get_recent_transactions(
        self,
        hours: int = 24,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get recent transactions across all users (admin/analytics).
        
        Args:
            hours: Number of hours to look back
            limit: Maximum number of transactions to return
            
        Returns:
            List of transaction dictionaries, newest first
        """
        try:
            cutoff = datetime.utcnow() - timedelta(hours=hours)
            
            query = self.db.collection(self.collection)
            query = query.where('timestamp', '>=', cutoff)
            query = query.order_by('timestamp', direction=firestore.Query.DESCENDING)
            query = query.limit(limit)
            
            transactions = []
            for doc in query.stream():
                tx_data = doc.to_dict()
                tx_data['id'] = doc.id
                
                if 'timestamp' in tx_data and tx_data['timestamp']:
                    tx_data['timestamp'] = tx_data['timestamp'].isoformat()
                
                transactions.append(tx_data)
            
            logger.debug(f"Retrieved {len(transactions)} recent transactions")
            return transactions
            
        except Exception as e:
            logger.error(f"Failed to get recent transactions: {str(e)}", exc_info=True)
            return []
    
    def get_transaction_stats(self, user_id: str) -> Dict[str, Any]:
        """
        Get aggregated transaction statistics for a user.
        
        Args:
            user_id: Firebase Auth UID
            
        Returns:
            Dictionary with stats (total_spent, total_earned, etc.)
        """
        try:
            transactions = self.get_user_transactions(user_id, limit=1000)
            
            stats = {
                'total_spent': 0,
                'total_earned': 0,
                'total_purchased': 0,
                'total_tips_sent': 0,
                'total_tips_received': 0,
                'generation_count': 0,
                'transaction_count': len(transactions)
            }
            
            for tx in transactions:
                amount = tx.get('amount', 0)
                tx_type = tx.get('type')
                
                if tx_type == TransactionType.GENERATION_SPEND:
                    stats['total_spent'] += abs(amount)
                    stats['generation_count'] += 1
                elif tx_type == TransactionType.TIP_RECEIVED:
                    stats['total_tips_received'] += amount
                    stats['total_earned'] += amount
                elif tx_type == TransactionType.TIP_SENT:
                    stats['total_tips_sent'] += abs(amount)
                elif tx_type == TransactionType.PURCHASE:
                    stats['total_purchased'] += amount
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get transaction stats: {str(e)}", exc_info=True)
            return {}
