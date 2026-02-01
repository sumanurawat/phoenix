"""
Token Purchase API Routes
Handles token package purchases via Stripe checkout
"""
import logging
from flask import Blueprint, jsonify, request, session, render_template, redirect, url_for, current_app
from functools import wraps
from services.stripe_service import StripeService
from services.token_service import TokenService
from services.transaction_service import TransactionService
from middleware.csrf_protection import csrf_protect
from config.token_packages import TOKEN_PACKAGES
import os

logger = logging.getLogger(__name__)

# Create Blueprint
token_bp = Blueprint('token', __name__, url_prefix='/api/tokens')

# Initialize services
stripe_service = StripeService()
token_service = TokenService()
transaction_service = TransactionService()

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function


@token_bp.route('/packages', methods=['GET'])
def get_packages():
    """
    Get available token packages with pricing and bonus information.
    Public endpoint - no authentication required.
    """
    try:
        packages = []
        for package_id, config in TOKEN_PACKAGES.items():
            package_data = {
                'id': package_id,
                'name': config['name'],
                'tokens': config['tokens'],
                'price': config['price'],
                'bonus': config.get('bonus', 0),
                'description': config['description'],
                'badge': config.get('badge', None),
                'available': os.getenv(config['price_id_env']) is not None
            }
            packages.append(package_data)
        
        return jsonify({
            'success': True,
            'packages': packages
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching token packages: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to load token packages'
        }), 500


@token_bp.route('/create-checkout-session', methods=['POST'])
@login_required
@csrf_protect
def create_checkout_session():
    """
    Create a Stripe checkout session for token purchase.
    Requires authentication and valid package selection.
    """
    try:
        data = request.get_json()
        package_id = data.get('package')
        
        if not package_id:
            return jsonify({'error': 'Package ID required'}), 400
        
        # Validate package exists
        if package_id not in TOKEN_PACKAGES:
            return jsonify({'error': 'Invalid package selected'}), 400
        
        package_config = TOKEN_PACKAGES[package_id]
        
        # Get Stripe price ID from environment
        price_id_env = package_config['price_id_env']
        price_id = os.getenv(price_id_env)
        
        if not price_id:
            logger.error(f"Stripe price ID not configured for {package_id} ({price_id_env})")
            return jsonify({'error': 'Package not available - contact support'}), 500
        
        # Get user info from session
        user_id = session['user_id']
        user_email = session.get('user_email', '')
        
        logger.info(f"[Stripe Service] Creating checkout session for user {user_id}, package {package_id}")
        
        # Get or create Stripe customer
        customer_id = stripe_service.get_or_create_customer(
            firebase_uid=user_id,
            email=user_email
        )
        
        if not customer_id:
            logger.error(f"[Stripe Service] Failed to create/get customer for user {user_id}")
            return jsonify({'error': 'Failed to create customer'}), 500
        
        # Create checkout session with token metadata
        checkout_session = stripe_service.create_token_checkout_session(
            customer_id=customer_id,
            price_id=price_id,
            metadata={
                'firebase_uid': user_id,
                'package_id': package_id,
                'tokens': package_config['tokens'],
                'purchase_type': 'token_package'
            }
        )
        
        if not checkout_session:
            logger.error(f"[Stripe Service] Failed to create checkout session for user {user_id}: Checkout session creation returned None")
            return jsonify({'error': 'Failed to create checkout session'}), 500
        
        logger.info(f"[Stripe Service] Successfully created checkout session {checkout_session.get('session_id')} for user {user_id}")
        
        return jsonify({
            'success': True,
            'session_id': checkout_session['session_id'],
            'url': checkout_session['url']
        }), 200
        
    except Exception as e:
        user_id = session.get('user_id', 'unknown')
        logger.error(f"[Stripe Service] Failed to create checkout session for user {user_id}: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to create checkout session'
        }), 500


@token_bp.route('/balance', methods=['GET'])
@login_required
def get_balance():
    """
    Get user's current token balance.
    """
    try:
        user_id = session['user_id']
        balance = token_service.get_balance(user_id)
        
        return jsonify({
            'success': True,
            'balance': balance
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching token balance: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to fetch balance'
        }), 500


@token_bp.route('/transactions', methods=['GET'])
@login_required
def get_transactions():
    """
    Get user's complete token transaction history.
    Supports pagination and filtering via query params.

    Query params:
        limit: Max transactions to return (1-100, default 50)
        type: Filter by transaction type (optional)
              Options: purchase, generation_spend, generation_refund, tip_sent, tip_received, signup_bonus

    Returns:
        200: {
            success: true,
            transactions: [{
                type: string,
                amount: number,  // positive for credits, negative for debits
                timestamp: string,
                description: string,  // user-friendly description
                details: object  // additional context
            }],
            balance: number,  // current balance
            totalEarned: number  // lifetime earnings from tips
        }
    """
    try:
        user_id = session['user_id']

        # Get query parameters
        limit = request.args.get('limit', 50, type=int)
        transaction_type = request.args.get('type', None)

        # Clamp limit to reasonable range
        limit = max(1, min(limit, 100))

        # Get current balance and earnings
        balance = token_service.get_balance(user_id)
        total_earned = token_service.get_total_earned(user_id)

        # Get transactions from service
        raw_transactions = transaction_service.get_user_transactions(
            user_id=user_id,
            limit=limit
        )

        # Filter by type if specified
        if transaction_type:
            raw_transactions = [t for t in raw_transactions if t.get('type') == transaction_type]

        # Format transactions with user-friendly descriptions
        formatted_transactions = []
        for txn in raw_transactions:
            txn_type = txn.get('type')
            amount = txn.get('amount', 0)
            details = txn.get('details', {})

            # Generate user-friendly description
            if txn_type == 'purchase':
                description = "Token Purchase"
            elif txn_type == 'generation_spend':
                description = "Video Generation"
            elif txn_type == 'generation_refund':
                description = "Failed Generation Refund"
            elif txn_type == 'tip_sent':
                recipient = details.get('recipientUsername', 'Unknown')
                description = f"Tip Sent to @{recipient}"
            elif txn_type == 'tip_received':
                sender = details.get('senderUsername', 'Unknown')
                description = f"Tip Received from @{sender}"
            elif txn_type == 'signup_bonus':
                description = "Welcome Bonus"
            elif txn_type == 'admin_credit':
                description = "Admin Credit"
            elif txn_type == 'refund':
                description = "Refund"
            else:
                description = txn_type.replace('_', ' ').title()

            formatted_transactions.append({
                'type': txn_type,
                'amount': amount,
                'timestamp': txn.get('timestamp'),
                'description': description,
                'details': details,
                'balanceAfter': txn.get('balanceAfter')  # Include balance after transaction
            })

        return jsonify({
            'success': True,
            'transactions': formatted_transactions,
            'balance': balance,
            'totalEarned': total_earned,
            'limit': limit
        }), 200

    except Exception as e:
        logger.error(f"Error fetching transactions: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to fetch transactions'
        }), 500


@token_bp.route('/transfer', methods=['POST'])
@login_required
@csrf_protect
def transfer_tokens():
    """
    Transfer tokens from the current user to another user.

    Request body:
        recipientUsername: str - Username of the recipient
        amount: int - Number of tokens to transfer (must be positive integer)

    Returns:
        200: {success: true, newBalance: int, message: str}
        400: {success: false, error: str} - Invalid request (bad amount, self-transfer, etc.)
        402: {success: false, error: str} - Insufficient tokens
        404: {success: false, error: str} - Recipient not found
        500: {success: false, error: str} - Server error
    """
    try:
        sender_id = session['user_id']
        data = request.get_json()

        # Validate request body
        if not data:
            return jsonify({'success': False, 'error': 'Request body required'}), 400

        recipient_username = data.get('recipientUsername', '').strip()
        amount = data.get('amount')

        # Validate recipient username
        if not recipient_username:
            return jsonify({'success': False, 'error': 'Recipient username is required'}), 400

        # Validate amount - must be a positive integer
        if amount is None:
            return jsonify({'success': False, 'error': 'Amount is required'}), 400

        try:
            amount = int(amount)
        except (ValueError, TypeError):
            return jsonify({'success': False, 'error': 'Amount must be a valid integer'}), 400

        if amount <= 0:
            return jsonify({'success': False, 'error': 'Amount must be greater than zero'}), 400

        if amount > 10000:
            return jsonify({'success': False, 'error': 'Maximum transfer amount is 10,000 tokens'}), 400

        # Look up recipient by username
        from firebase_admin import firestore as admin_firestore
        db = admin_firestore.client()

        # Query users collection by username
        recipient_query = db.collection('users').where('username', '==', recipient_username).limit(1)
        recipient_docs = list(recipient_query.stream())

        if not recipient_docs:
            return jsonify({'success': False, 'error': f'User @{recipient_username} not found'}), 404

        recipient_doc = recipient_docs[0]
        recipient_id = recipient_doc.id
        recipient_data = recipient_doc.to_dict()

        # Prevent self-transfer
        if sender_id == recipient_id:
            return jsonify({'success': False, 'error': 'Cannot send tokens to yourself'}), 400

        # Get sender's current balance to validate
        sender_balance = token_service.get_balance(sender_id)
        if sender_balance < amount:
            return jsonify({
                'success': False,
                'error': f'Insufficient tokens. You have {sender_balance} tokens, but tried to send {amount}.'
            }), 402

        # Get sender's username for transaction record
        sender_doc = db.collection('users').document(sender_id).get()
        sender_username = sender_doc.to_dict().get('username', 'Unknown') if sender_doc.exists else 'Unknown'

        logger.info(f"Token transfer initiated: {sender_username} ({sender_id}) -> {recipient_username} ({recipient_id}), amount: {amount}")

        # Perform the atomic transfer
        from services.token_service import InsufficientTokensError
        try:
            token_service.transfer_tokens(
                sender_id=sender_id,
                recipient_id=recipient_id,
                amount=amount
            )
        except InsufficientTokensError as e:
            logger.warning(f"Transfer failed - insufficient tokens: {e}")
            return jsonify({
                'success': False,
                'error': 'Insufficient tokens for this transfer'
            }), 402
        except ValueError as e:
            logger.warning(f"Transfer failed - validation error: {e}")
            return jsonify({'success': False, 'error': str(e)}), 400

        # Record both sides of the transaction
        # Get updated balances after transfer
        sender_balance_after = token_service.get_balance(sender_id)
        recipient_balance_after = token_service.get_balance(recipient_id)

        # Record sender's transaction (tip sent)
        transaction_service.record_transaction(
            user_id=sender_id,
            transaction_type='tip_sent',
            amount=-amount,  # Negative for sender
            balance_after=sender_balance_after,
            details={
                'recipientId': recipient_id,
                'recipientUsername': recipient_username
            }
        )

        # Record recipient's transaction (tip received)
        transaction_service.record_transaction(
            user_id=recipient_id,
            transaction_type='tip_received',
            amount=amount,  # Positive for recipient
            balance_after=recipient_balance_after,
            details={
                'senderId': sender_id,
                'senderUsername': sender_username
            }
        )

        logger.info(f"Token transfer completed: {sender_username} -> {recipient_username}, amount: {amount}")

        return jsonify({
            'success': True,
            'newBalance': sender_balance_after,
            'message': f'Successfully sent {amount} tokens to @{recipient_username}'
        }), 200

    except Exception as e:
        logger.error(f"Token transfer error: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to transfer tokens. Please try again.'
        }), 500
