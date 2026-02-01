"""Token Audit Service

Provides a complete, queryable audit trail of every token movement in the system.
Think of it like a bank statement - every credit and debit recorded with timestamp,
reason, and context.

Features:
- Log all token operations (credits, debits, transfers)
- Store balance before/after for each operation
- Query audit logs by user_id or reference_id
- Append-only design for security
"""
from __future__ import annotations

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from google.cloud import firestore
from firebase_admin import firestore as admin_firestore

logger = logging.getLogger(__name__)

# Audit log types
AUDIT_TYPE_CREDIT = "credit"
AUDIT_TYPE_DEBIT = "debit"
AUDIT_TYPE_TRANSFER_IN = "transfer_in"
AUDIT_TYPE_TRANSFER_OUT = "transfer_out"

# Reason codes for audit entries
REASON_STRIPE_PURCHASE = "stripe_purchase"
REASON_IMAGE_GENERATION = "image_generation"
REASON_VIDEO_GENERATION = "video_generation"
REASON_TRANSFER = "transfer"
REASON_REFUND = "refund"
REASON_ADMIN_ADJUSTMENT = "admin_adjustment"


class TokenAuditService:
    """
    Service for managing token audit logs.

    All audit entries are append-only and immutable once created.
    This ensures a reliable audit trail for all token movements.
    """

    COLLECTION_NAME = "token_audit_log"

    def __init__(self, db: firestore.Client = None):
        """
        Initialize token audit service.

        Args:
            db: Firestore client instance (uses default if not provided)
        """
        self.db = db or admin_firestore.client()
        logger.debug("TokenAuditService initialized")

    def _create_audit_entry(
        self,
        user_id: str,
        audit_type: str,
        amount: int,
        balance_before: int,
        balance_after: int,
        reason: str,
        reference_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None
    ) -> str:
        """
        Create an audit entry in Firestore.

        Args:
            user_id: Firebase Auth UID
            audit_type: Type of operation (credit, debit, transfer_in, transfer_out)
            amount: Number of tokens involved (always positive)
            balance_before: User's balance before the operation
            balance_after: User's balance after the operation
            reason: Reason for the operation
            reference_id: Related ID (creation_id, transaction_id, etc.)
            metadata: Additional context
            ip_address: Optional IP address for fraud detection

        Returns:
            The auto-generated document ID
        """
        audit_entry = {
            "user_id": user_id,
            "type": audit_type,
            "amount": amount,
            "balance_before": balance_before,
            "balance_after": balance_after,
            "reason": reason,
            "reference_id": reference_id,
            "metadata": metadata or {},
            "created_at": datetime.utcnow(),
            "ip_address": ip_address
        }

        try:
            doc_ref = self.db.collection(self.COLLECTION_NAME).add(audit_entry)
            doc_id = doc_ref[1].id
            logger.info(
                f"Audit entry created: {audit_type} | user={user_id} | "
                f"amount={amount} | {balance_before} → {balance_after} | "
                f"reason={reason} | doc_id={doc_id}"
            )
            return doc_id
        except Exception as e:
            logger.error(f"Failed to create audit entry: {str(e)}", exc_info=True)
            raise

    def log_credit(
        self,
        user_id: str,
        amount: int,
        balance_before: int,
        balance_after: int,
        reason: str,
        reference_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None
    ) -> str:
        """
        Log a token credit (tokens added to user's balance).

        Args:
            user_id: Firebase Auth UID
            amount: Number of tokens credited
            balance_before: Balance before credit
            balance_after: Balance after credit
            reason: Reason for credit (e.g., stripe_purchase, refund)
            reference_id: Related transaction/creation ID
            metadata: Additional context
            ip_address: Optional IP for fraud detection

        Returns:
            Audit entry document ID
        """
        return self._create_audit_entry(
            user_id=user_id,
            audit_type=AUDIT_TYPE_CREDIT,
            amount=amount,
            balance_before=balance_before,
            balance_after=balance_after,
            reason=reason,
            reference_id=reference_id,
            metadata=metadata,
            ip_address=ip_address
        )

    def log_debit(
        self,
        user_id: str,
        amount: int,
        balance_before: int,
        balance_after: int,
        reason: str,
        reference_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None
    ) -> str:
        """
        Log a token debit (tokens removed from user's balance).

        Args:
            user_id: Firebase Auth UID
            amount: Number of tokens debited
            balance_before: Balance before debit
            balance_after: Balance after debit
            reason: Reason for debit (e.g., image_generation, video_generation)
            reference_id: Related creation ID
            metadata: Additional context
            ip_address: Optional IP for fraud detection

        Returns:
            Audit entry document ID
        """
        return self._create_audit_entry(
            user_id=user_id,
            audit_type=AUDIT_TYPE_DEBIT,
            amount=amount,
            balance_before=balance_before,
            balance_after=balance_after,
            reason=reason,
            reference_id=reference_id,
            metadata=metadata,
            ip_address=ip_address
        )

    def log_transfer_out(
        self,
        user_id: str,
        amount: int,
        balance_before: int,
        balance_after: int,
        recipient_id: str,
        reference_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None
    ) -> str:
        """
        Log a token transfer out (tokens sent to another user).

        Args:
            user_id: Firebase Auth UID of sender
            amount: Number of tokens transferred
            balance_before: Sender's balance before transfer
            balance_after: Sender's balance after transfer
            recipient_id: Firebase Auth UID of recipient
            reference_id: Transfer reference ID
            metadata: Additional context
            ip_address: Optional IP for fraud detection

        Returns:
            Audit entry document ID
        """
        transfer_metadata = metadata or {}
        transfer_metadata["recipient_id"] = recipient_id

        return self._create_audit_entry(
            user_id=user_id,
            audit_type=AUDIT_TYPE_TRANSFER_OUT,
            amount=amount,
            balance_before=balance_before,
            balance_after=balance_after,
            reason=REASON_TRANSFER,
            reference_id=reference_id,
            metadata=transfer_metadata,
            ip_address=ip_address
        )

    def log_transfer_in(
        self,
        user_id: str,
        amount: int,
        balance_before: int,
        balance_after: int,
        sender_id: str,
        reference_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None
    ) -> str:
        """
        Log a token transfer in (tokens received from another user).

        Args:
            user_id: Firebase Auth UID of recipient
            amount: Number of tokens received
            balance_before: Recipient's balance before transfer
            balance_after: Recipient's balance after transfer
            sender_id: Firebase Auth UID of sender
            reference_id: Transfer reference ID
            metadata: Additional context
            ip_address: Optional IP for fraud detection

        Returns:
            Audit entry document ID
        """
        transfer_metadata = metadata or {}
        transfer_metadata["sender_id"] = sender_id

        return self._create_audit_entry(
            user_id=user_id,
            audit_type=AUDIT_TYPE_TRANSFER_IN,
            amount=amount,
            balance_before=balance_before,
            balance_after=balance_after,
            reason=REASON_TRANSFER,
            reference_id=reference_id,
            metadata=transfer_metadata,
            ip_address=ip_address
        )

    def get_user_audit_log(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get audit log entries for a specific user.

        Args:
            user_id: Firebase Auth UID
            limit: Maximum number of entries to return
            offset: Number of entries to skip (for pagination)

        Returns:
            List of audit entries, newest first
        """
        try:
            query = (
                self.db.collection(self.COLLECTION_NAME)
                .where("user_id", "==", user_id)
                .order_by("created_at", direction=firestore.Query.DESCENDING)
                .limit(limit + offset)
            )

            docs = query.stream()
            entries = []

            for i, doc in enumerate(docs):
                if i < offset:
                    continue
                if len(entries) >= limit:
                    break

                entry = doc.to_dict()
                entry["id"] = doc.id
                entries.append(entry)

            logger.debug(f"Retrieved {len(entries)} audit entries for user {user_id}")
            return entries

        except Exception as e:
            logger.error(f"Failed to get audit log for user {user_id}: {str(e)}", exc_info=True)
            return []

    def get_audit_log_by_reference(
        self,
        reference_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get all audit log entries for a specific reference ID.

        Useful for finding all token movements related to a single
        transaction, creation, or transfer.

        Args:
            reference_id: The reference ID to search for

        Returns:
            List of audit entries matching the reference
        """
        try:
            query = (
                self.db.collection(self.COLLECTION_NAME)
                .where("reference_id", "==", reference_id)
                .order_by("created_at", direction=firestore.Query.DESCENDING)
            )

            docs = query.stream()
            entries = []

            for doc in docs:
                entry = doc.to_dict()
                entry["id"] = doc.id
                entries.append(entry)

            logger.debug(f"Retrieved {len(entries)} audit entries for reference {reference_id}")
            return entries

        except Exception as e:
            logger.error(f"Failed to get audit log for reference {reference_id}: {str(e)}", exc_info=True)
            return []
