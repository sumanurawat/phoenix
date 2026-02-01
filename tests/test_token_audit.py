"""
Tests for Token Audit Service.

These tests verify that the token audit logging system correctly
creates audit entries for all token operations.

Run with: pytest tests/test_token_audit.py -v
"""

import pytest
from unittest.mock import MagicMock, patch, call
from datetime import datetime

from services.token_audit_service import (
    TokenAuditService,
    AUDIT_TYPE_CREDIT,
    AUDIT_TYPE_DEBIT,
    AUDIT_TYPE_TRANSFER_IN,
    AUDIT_TYPE_TRANSFER_OUT,
    REASON_STRIPE_PURCHASE,
    REASON_IMAGE_GENERATION,
    REASON_TRANSFER,
)
from services.token_service import TokenService, InsufficientTokensError


class TestTokenAuditService:
    """Test suite for TokenAuditService."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock Firestore client."""
        return MagicMock()

    @pytest.fixture
    def audit_service(self, mock_db):
        """Create TokenAuditService with mock database."""
        return TokenAuditService(db=mock_db)

    def test_log_credit_creates_audit_entry(self, audit_service, mock_db):
        """Test that log_credit creates the correct audit entry."""
        # Setup mock
        mock_doc_ref = MagicMock()
        mock_doc_ref.id = "test_audit_id_123"
        mock_db.collection.return_value.add.return_value = (None, mock_doc_ref)

        # Execute
        doc_id = audit_service.log_credit(
            user_id="user_123",
            amount=100,
            balance_before=50,
            balance_after=150,
            reason=REASON_STRIPE_PURCHASE,
            reference_id="txn_abc123",
            metadata={"stripe_session": "cs_123"},
            ip_address="192.168.1.1"
        )

        # Verify
        assert doc_id == "test_audit_id_123"
        mock_db.collection.assert_called_with("token_audit_log")

        # Check the audit entry structure
        call_args = mock_db.collection.return_value.add.call_args[0][0]
        assert call_args["user_id"] == "user_123"
        assert call_args["type"] == AUDIT_TYPE_CREDIT
        assert call_args["amount"] == 100
        assert call_args["balance_before"] == 50
        assert call_args["balance_after"] == 150
        assert call_args["reason"] == REASON_STRIPE_PURCHASE
        assert call_args["reference_id"] == "txn_abc123"
        assert call_args["metadata"] == {"stripe_session": "cs_123"}
        assert call_args["ip_address"] == "192.168.1.1"
        assert isinstance(call_args["created_at"], datetime)

    def test_log_debit_creates_audit_entry(self, audit_service, mock_db):
        """Test that log_debit creates the correct audit entry."""
        # Setup mock
        mock_doc_ref = MagicMock()
        mock_doc_ref.id = "test_audit_id_456"
        mock_db.collection.return_value.add.return_value = (None, mock_doc_ref)

        # Execute
        doc_id = audit_service.log_debit(
            user_id="user_456",
            amount=25,
            balance_before=100,
            balance_after=75,
            reason=REASON_IMAGE_GENERATION,
            reference_id="creation_xyz789"
        )

        # Verify
        assert doc_id == "test_audit_id_456"

        call_args = mock_db.collection.return_value.add.call_args[0][0]
        assert call_args["user_id"] == "user_456"
        assert call_args["type"] == AUDIT_TYPE_DEBIT
        assert call_args["amount"] == 25
        assert call_args["balance_before"] == 100
        assert call_args["balance_after"] == 75
        assert call_args["reason"] == REASON_IMAGE_GENERATION
        assert call_args["reference_id"] == "creation_xyz789"

    def test_log_transfer_out_includes_recipient(self, audit_service, mock_db):
        """Test that log_transfer_out includes recipient in metadata."""
        # Setup mock
        mock_doc_ref = MagicMock()
        mock_doc_ref.id = "transfer_out_id"
        mock_db.collection.return_value.add.return_value = (None, mock_doc_ref)

        # Execute
        doc_id = audit_service.log_transfer_out(
            user_id="sender_123",
            amount=50,
            balance_before=200,
            balance_after=150,
            recipient_id="recipient_456",
            reference_id="transfer_abc"
        )

        # Verify
        call_args = mock_db.collection.return_value.add.call_args[0][0]
        assert call_args["type"] == AUDIT_TYPE_TRANSFER_OUT
        assert call_args["reason"] == REASON_TRANSFER
        assert call_args["metadata"]["recipient_id"] == "recipient_456"

    def test_log_transfer_in_includes_sender(self, audit_service, mock_db):
        """Test that log_transfer_in includes sender in metadata."""
        # Setup mock
        mock_doc_ref = MagicMock()
        mock_doc_ref.id = "transfer_in_id"
        mock_db.collection.return_value.add.return_value = (None, mock_doc_ref)

        # Execute
        doc_id = audit_service.log_transfer_in(
            user_id="recipient_456",
            amount=50,
            balance_before=100,
            balance_after=150,
            sender_id="sender_123",
            reference_id="transfer_abc"
        )

        # Verify
        call_args = mock_db.collection.return_value.add.call_args[0][0]
        assert call_args["type"] == AUDIT_TYPE_TRANSFER_IN
        assert call_args["reason"] == REASON_TRANSFER
        assert call_args["metadata"]["sender_id"] == "sender_123"

    def test_get_user_audit_log_queries_correctly(self, audit_service, mock_db):
        """Test that get_user_audit_log queries with correct parameters."""
        # Setup mock
        mock_query = MagicMock()
        mock_db.collection.return_value.where.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query

        mock_doc = MagicMock()
        mock_doc.id = "audit_1"
        mock_doc.to_dict.return_value = {
            "user_id": "user_123",
            "type": "credit",
            "amount": 100
        }
        mock_query.stream.return_value = [mock_doc]

        # Execute
        entries = audit_service.get_user_audit_log(
            user_id="user_123",
            limit=25,
            offset=0
        )

        # Verify
        mock_db.collection.assert_called_with("token_audit_log")
        mock_db.collection.return_value.where.assert_called_with(
            "user_id", "==", "user_123"
        )
        assert len(entries) == 1
        assert entries[0]["id"] == "audit_1"
        assert entries[0]["user_id"] == "user_123"

    def test_get_audit_log_by_reference(self, audit_service, mock_db):
        """Test that get_audit_log_by_reference finds all related entries."""
        # Setup mock - simulate transfer with 2 entries
        mock_query = MagicMock()
        mock_db.collection.return_value.where.return_value = mock_query
        mock_query.order_by.return_value = mock_query

        mock_doc_out = MagicMock()
        mock_doc_out.id = "transfer_out_1"
        mock_doc_out.to_dict.return_value = {
            "type": AUDIT_TYPE_TRANSFER_OUT,
            "reference_id": "transfer_abc"
        }

        mock_doc_in = MagicMock()
        mock_doc_in.id = "transfer_in_1"
        mock_doc_in.to_dict.return_value = {
            "type": AUDIT_TYPE_TRANSFER_IN,
            "reference_id": "transfer_abc"
        }

        mock_query.stream.return_value = [mock_doc_out, mock_doc_in]

        # Execute
        entries = audit_service.get_audit_log_by_reference("transfer_abc")

        # Verify
        mock_db.collection.return_value.where.assert_called_with(
            "reference_id", "==", "transfer_abc"
        )
        assert len(entries) == 2

    def test_empty_metadata_defaults(self, audit_service, mock_db):
        """Test that metadata defaults to empty dict when not provided."""
        mock_doc_ref = MagicMock()
        mock_doc_ref.id = "test_id"
        mock_db.collection.return_value.add.return_value = (None, mock_doc_ref)

        audit_service.log_credit(
            user_id="user_123",
            amount=100,
            balance_before=0,
            balance_after=100,
            reason="test"
        )

        call_args = mock_db.collection.return_value.add.call_args[0][0]
        assert call_args["metadata"] == {}
        assert call_args["reference_id"] is None
        assert call_args["ip_address"] is None


class TestTokenServiceAuditIntegration:
    """Test suite for TokenService with audit logging integration."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock Firestore client."""
        db = MagicMock()
        # Setup transaction mock
        db.transaction.return_value = MagicMock()
        return db

    @pytest.fixture
    def mock_audit_service(self):
        """Create a mock TokenAuditService."""
        return MagicMock(spec=TokenAuditService)

    @pytest.fixture
    def token_service(self, mock_db, mock_audit_service):
        """Create TokenService with mocked dependencies."""
        with patch('services.token_service.TokenAuditService') as MockAuditService:
            MockAuditService.return_value = mock_audit_service
            service = TokenService(db=mock_db)
            return service

    def test_add_tokens_creates_audit_entry(self, token_service, mock_db):
        """Test that add_tokens creates an audit entry."""
        # Setup mocks
        user_ref = MagicMock()
        mock_db.collection.return_value.document.return_value = user_ref

        # Mock user document
        user_doc = MagicMock()
        user_doc.exists = True
        user_doc.to_dict.return_value = {"tokenBalance": 50}
        user_ref.get.return_value = user_doc

        # Execute
        with patch.object(token_service, 'get_balance', side_effect=[50, 150]):
            with patch('firebase_admin.firestore.transactional', lambda f: f):
                result = token_service.add_tokens(
                    user_id="user_123",
                    amount=100,
                    reason=REASON_STRIPE_PURCHASE,
                    reference_id="txn_abc123",
                    metadata={"test": "data"},
                    ip_address="192.168.1.1"
                )

        # Verify audit was called
        token_service.audit_service.log_credit.assert_called_once_with(
            user_id="user_123",
            amount=100,
            balance_before=50,
            balance_after=150,
            reason=REASON_STRIPE_PURCHASE,
            reference_id="txn_abc123",
            metadata={"test": "data"},
            ip_address="192.168.1.1"
        )

    def test_deduct_tokens_creates_audit_entry(self, token_service, mock_db):
        """Test that deduct_tokens creates an audit entry."""
        # Setup mocks
        user_ref = MagicMock()
        mock_db.collection.return_value.document.return_value = user_ref

        # Mock user document with sufficient balance
        user_doc = MagicMock()
        user_doc.exists = True
        user_doc.to_dict.return_value = {"tokenBalance": 100}
        user_ref.get.return_value = user_doc

        # Execute
        with patch('firebase_admin.firestore.transactional', lambda f: f):
            result = token_service.deduct_tokens(
                user_id="user_456",
                amount=25,
                reason=REASON_IMAGE_GENERATION,
                reference_id="creation_xyz"
            )

        # Verify audit was called
        token_service.audit_service.log_debit.assert_called_once()
        call_kwargs = token_service.audit_service.log_debit.call_args[1]
        assert call_kwargs["user_id"] == "user_456"
        assert call_kwargs["amount"] == 25
        assert call_kwargs["balance_before"] == 100
        assert call_kwargs["balance_after"] == 75
        assert call_kwargs["reason"] == REASON_IMAGE_GENERATION

    def test_transfer_tokens_creates_two_audit_entries(self, token_service, mock_db):
        """Test that transfer_tokens creates entries for both sender and recipient."""
        # Setup mocks for sender and recipient
        sender_ref = MagicMock()
        recipient_ref = MagicMock()

        def get_document(user_id):
            mock_ref = MagicMock()
            if user_id == "sender_123":
                mock_doc = MagicMock()
                mock_doc.exists = True
                mock_doc.to_dict.return_value = {"tokenBalance": 200}
                mock_ref.get.return_value = mock_doc
            else:
                mock_doc = MagicMock()
                mock_doc.exists = True
                mock_doc.to_dict.return_value = {"tokenBalance": 50}
                mock_ref.get.return_value = mock_doc
            return mock_ref

        mock_db.collection.return_value.document.side_effect = get_document

        # Execute
        with patch('firebase_admin.firestore.transactional', lambda f: f):
            result = token_service.transfer_tokens(
                sender_id="sender_123",
                recipient_id="recipient_456",
                amount=75
            )

        # Verify both audit calls were made
        assert token_service.audit_service.log_transfer_out.call_count == 1
        assert token_service.audit_service.log_transfer_in.call_count == 1

        # Verify sender entry
        out_kwargs = token_service.audit_service.log_transfer_out.call_args[1]
        assert out_kwargs["user_id"] == "sender_123"
        assert out_kwargs["amount"] == 75
        assert out_kwargs["balance_before"] == 200
        assert out_kwargs["balance_after"] == 125
        assert out_kwargs["recipient_id"] == "recipient_456"

        # Verify recipient entry
        in_kwargs = token_service.audit_service.log_transfer_in.call_args[1]
        assert in_kwargs["user_id"] == "recipient_456"
        assert in_kwargs["amount"] == 75
        assert in_kwargs["balance_before"] == 50
        assert in_kwargs["balance_after"] == 125
        assert in_kwargs["sender_id"] == "sender_123"

        # Verify same reference_id for both entries
        assert out_kwargs["reference_id"] == in_kwargs["reference_id"]

    def test_deduct_tokens_no_audit_on_insufficient_balance(self, token_service, mock_db):
        """Test that no audit entry is created when balance is insufficient."""
        # Setup mocks
        user_ref = MagicMock()
        mock_db.collection.return_value.document.return_value = user_ref

        # Mock user document with insufficient balance
        user_doc = MagicMock()
        user_doc.exists = True
        user_doc.to_dict.return_value = {"tokenBalance": 10}
        user_ref.get.return_value = user_doc

        # Execute and expect exception
        with patch('firebase_admin.firestore.transactional', lambda f: f):
            with pytest.raises(InsufficientTokensError):
                token_service.deduct_tokens(
                    user_id="user_789",
                    amount=100,
                    reason="test"
                )

        # Verify no audit entry was created
        token_service.audit_service.log_debit.assert_not_called()


# Run with: pytest tests/test_token_audit.py -v
