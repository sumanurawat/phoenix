"""Token Wallet Service

Manages the virtual token economy for the AI generation platform.
Implements atomic operations to ensure data integrity across concurrent requests.

Features:
- Token balance management (get, add, deduct)
- Atomic transactions using Firestore transactions
- Transfer tokens between users (tipping)
- Balance validation and insufficient funds handling
"""
from __future__ import annotations

import logging
from typing import Optional, Dict, Any
from datetime import datetime
from google.cloud import firestore
from firebase_admin import firestore as admin_firestore

logger = logging.getLogger(__name__)


class InsufficientTokensError(Exception):
    """Raised when user doesn't have enough tokens for an operation."""
    pass


class TokenService:
    """
    Service for managing user token balances with atomic operations.
    
    All balance modifications use Firestore transactions to prevent race conditions
    and ensure consistency across concurrent requests.
    """
    
    def __init__(self, db: firestore.Client = None):
        """
        Initialize token service.
        
        Args:
            db: Firestore client instance (uses default if not provided)
        """
        self.db = db or admin_firestore.client()
        logger.info("TokenService initialized")
    
    def get_balance(self, user_id: str) -> int:
        """
        Get current token balance for a user.
        
        Args:
            user_id: Firebase Auth UID
            
        Returns:
            Current token balance (0 if user doesn't exist)
        """
        try:
            user_ref = self.db.collection('users').document(user_id)
            user_doc = user_ref.get()
            
            if not user_doc.exists:
                logger.warning(f"User {user_id} not found when checking balance")
                return 0
            
            balance = user_doc.to_dict().get('tokenBalance', 0)
            logger.debug(f"User {user_id} balance: {balance} tokens")
            return balance
            
        except Exception as e:
            logger.error(f"Failed to get balance for {user_id}: {str(e)}", exc_info=True)
            return 0
    
    def get_total_earned(self, user_id: str) -> int:
        """
        Get total tokens earned by user (lifetime tips received).
        
        Args:
            user_id: Firebase Auth UID
            
        Returns:
            Total tokens earned (0 if user doesn't exist)
        """
        try:
            user_ref = self.db.collection('users').document(user_id)
            user_doc = user_ref.get()
            
            if not user_doc.exists:
                return 0
            
            return user_doc.to_dict().get('totalTokensEarned', 0)
            
        except Exception as e:
            logger.error(f"Failed to get total earned for {user_id}: {str(e)}", exc_info=True)
            return 0
    
    def deduct_tokens(self, user_id: str, amount: int, reason: str = None) -> bool:
        """
        Deduct tokens from user's balance atomically.
        
        Args:
            user_id: Firebase Auth UID
            amount: Number of tokens to deduct (must be positive)
            reason: Optional reason for logging
            
        Returns:
            True if successful
            
        Raises:
            InsufficientTokensError: If user doesn't have enough tokens
            ValueError: If amount is invalid
        """
        if amount <= 0:
            raise ValueError("Deduct amount must be positive")
        
        try:
            user_ref = self.db.collection('users').document(user_id)
            
            logger.info(f"Deducting {amount} tokens from {user_id} (reason: {reason})")
            
            # Use transactional decorator inline
            @admin_firestore.transactional
            def deduct_in_transaction(transaction):
                user_doc = user_ref.get(transaction=transaction)
                
                if not user_doc.exists:
                    raise ValueError(f"User does not exist")
                
                current_balance = user_doc.to_dict().get('tokenBalance', 0)
                
                if current_balance < amount:
                    raise InsufficientTokensError(
                        f"Insufficient tokens: have {current_balance}, need {amount}"
                    )
                
                # Atomically decrement balance
                transaction.update(user_ref, {
                    'tokenBalance': admin_firestore.Increment(-amount)
                })
                
                return True
            
            # Execute the transaction
            transaction = self.db.transaction()
            deduct_in_transaction(transaction)
            
            logger.info(f"Successfully deducted {amount} tokens from {user_id}")
            return True
            
        except InsufficientTokensError:
            logger.warning(f"Insufficient tokens for {user_id}: tried to deduct {amount}")
            raise
        except Exception as e:
            logger.error(f"Failed to deduct tokens for {user_id}: {str(e)}", exc_info=True)
            raise
    
    def _add_tokens_transaction(
        self,
        transaction: firestore.Transaction,
        user_ref: firestore.DocumentReference,
        amount: int,
        increment_earned: bool = False
    ) -> None:
        """
        Add tokens to user balance atomically within a transaction.

        Args:
            transaction: Firestore transaction
            user_ref: User document reference
            amount: Number of tokens to add
            increment_earned: Whether to also increment totalTokensEarned (for tips)
        """
        # CRITICAL: Check if user document exists before updating
        user_doc = user_ref.get(transaction=transaction)

        if not user_doc.exists:
            logger.error(f"❌ CRITICAL: User document does not exist for {user_ref.id}")
            logger.error(f"   Cannot add {amount} tokens to non-existent user")
            logger.error(f"   This purchase will FAIL - user needs to be created first")
            raise ValueError(f"User document {user_ref.id} does not exist")

        # Log current balance before update
        current_balance = user_doc.to_dict().get('tokenBalance', 0)
        logger.info(f"💰 Token Addition Transaction:")
        logger.info(f"   User: {user_ref.id}")
        logger.info(f"   Current Balance: {current_balance}")
        logger.info(f"   Adding: {amount} tokens")
        logger.info(f"   Expected New Balance: {current_balance + amount}")
        logger.info(f"   Increment Earned: {increment_earned}")

        # Atomically increment balance
        if increment_earned:
            transaction.update(user_ref, {
                'tokenBalance': admin_firestore.Increment(amount),
                'totalTokensEarned': admin_firestore.Increment(amount)
            })
            logger.info(f"✅ Transaction prepared: +{amount} tokens AND +{amount} earned")
        else:
            transaction.update(user_ref, {
                'tokenBalance': admin_firestore.Increment(amount)
            })
            logger.info(f"✅ Transaction prepared: +{amount} tokens only")
    
    def add_tokens(
        self,
        user_id: str,
        amount: int,
        reason: str = None,
        increment_earned: bool = False
    ) -> int:
        """
        Add tokens to user's balance atomically.

        Args:
            user_id: Firebase Auth UID
            amount: Number of tokens to add (must be positive)
            reason: Optional reason for logging
            increment_earned: If True, also increment totalTokensEarned (for tips)

        Returns:
            The user's balance after adding tokens

        Raises:
            ValueError: If amount is invalid
        """
        if amount <= 0:
            raise ValueError("Add amount must be positive")

        try:
            user_ref = self.db.collection('users').document(user_id)

            logger.info(f"🔵 ========== TOKEN PURCHASE START ==========")
            logger.info(f"👤 User ID: {user_id}")
            logger.info(f"🪙 Amount to Add: {amount} tokens")
            logger.info(f"📝 Reason: {reason}")
            logger.info(f"💎 Increment Earned: {increment_earned}")

            # Get balance BEFORE transaction
            balance_before = self.get_balance(user_id)
            logger.info(f"💰 Balance BEFORE: {balance_before} tokens")

            # Execute transaction with manual commit
            @admin_firestore.transactional
            def update_in_transaction(transaction):
                self._add_tokens_transaction(transaction, user_ref, amount, increment_earned)

            # Run the transaction
            logger.info(f"⚡ Starting Firestore transaction...")
            transaction = self.db.transaction()
            update_in_transaction(transaction)
            logger.info(f"✅ Firestore transaction COMMITTED successfully")

            # CRITICAL: Verify the balance actually increased
            logger.info(f"🔍 Verifying token balance after transaction...")
            balance_after = self.get_balance(user_id)
            expected_balance = balance_before + amount

            logger.info(f"💰 Balance AFTER: {balance_after} tokens")
            logger.info(f"📊 Expected Balance: {expected_balance} tokens")

            if balance_after == expected_balance:
                logger.info(f"✅ ✅ ✅ VERIFICATION PASSED: Balance increased correctly!")
                logger.info(f"🔵 ========== TOKEN PURCHASE SUCCESS ==========")
                return balance_after
            else:
                logger.error(f"❌❌❌ VERIFICATION FAILED: Balance mismatch!")
                logger.error(f"   Expected: {expected_balance}")
                logger.error(f"   Actual: {balance_after}")
                logger.error(f"   Difference: {balance_after - expected_balance}")
                logger.error(f"🔴 ========== TOKEN PURCHASE FAILED ==========")
                raise ValueError(f"Token balance verification failed: expected {expected_balance}, got {balance_after}")

        except Exception as e:
            logger.error(f"❌ Failed to add tokens for {user_id}: {str(e)}", exc_info=True)
            logger.error(f"🔴 ========== TOKEN PURCHASE EXCEPTION ==========")
            raise
    
    def transfer_tokens(
        self,
        sender_id: str,
        recipient_id: str,
        amount: int
    ) -> bool:
        """
        Transfer tokens from one user to another (tipping).
        
        This is an atomic operation that ensures either both the deduction
        and addition succeed, or neither happens.
        
        Args:
            sender_id: Firebase Auth UID of sender
            recipient_id: Firebase Auth UID of recipient
            amount: Number of tokens to transfer (must be positive)
            
        Returns:
            True if successful
            
        Raises:
            InsufficientTokensError: If sender doesn't have enough tokens
            ValueError: If sender and recipient are the same or amount invalid
        """
        if amount <= 0:
            raise ValueError("Transfer amount must be positive")
        
        if sender_id == recipient_id:
            raise ValueError("Cannot transfer tokens to yourself")
        
        try:
            sender_ref = self.db.collection('users').document(sender_id)
            recipient_ref = self.db.collection('users').document(recipient_id)
            
            logger.info(f"Transferring {amount} tokens from {sender_id} to {recipient_id}")
            
            # Use transactional decorator inline
            @admin_firestore.transactional
            def transfer_in_transaction(transaction):
                # Check sender's balance
                sender_doc = sender_ref.get(transaction=transaction)
                if not sender_doc.exists:
                    raise ValueError("Sender does not exist")
                
                sender_balance = sender_doc.to_dict().get('tokenBalance', 0)
                if sender_balance < amount:
                    raise InsufficientTokensError(
                        f"Insufficient tokens: sender has {sender_balance}, needs {amount}"
                    )
                
                # Check recipient exists
                recipient_doc = recipient_ref.get(transaction=transaction)
                if not recipient_doc.exists:
                    raise ValueError("Recipient does not exist")
                
                # Deduct from sender
                transaction.update(sender_ref, {
                    'tokenBalance': admin_firestore.Increment(-amount)
                })
                
                # Add to recipient (and increment their totalTokensEarned)
                transaction.update(recipient_ref, {
                    'tokenBalance': admin_firestore.Increment(amount),
                    'totalTokensEarned': admin_firestore.Increment(amount)
                })
            
            # Execute the transaction
            transaction = self.db.transaction()
            transfer_in_transaction(transaction)
            
            logger.info(f"Successfully transferred {amount} tokens from {sender_id} to {recipient_id}")
            return True
            
        except InsufficientTokensError:
            logger.warning(f"Insufficient tokens for transfer: {sender_id} → {recipient_id} ({amount})")
            raise
        except Exception as e:
            logger.error(f"Failed to transfer tokens: {str(e)}", exc_info=True)
            raise
    
    def check_sufficient_balance(self, user_id: str, required_amount: int) -> bool:
        """
        Check if user has sufficient tokens for an operation.
        
        Args:
            user_id: Firebase Auth UID
            required_amount: Number of tokens required
            
        Returns:
            True if user has enough tokens, False otherwise
        """
        current_balance = self.get_balance(user_id)
        return current_balance >= required_amount
