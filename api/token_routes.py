"""
Token Purchase API Routes
Handles token package purchases via Stripe checkout
"""
import logging
from flask import Blueprint, jsonify, request, session, render_template, redirect, url_for
from functools import wraps
from services.stripe_service import StripeService
from services.token_service import TokenService
from services.transaction_service import TransactionService
from middleware.csrf_protection import csrf_protect
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

# Token package configurations
TOKEN_PACKAGES = {
    'starter': {
        'name': 'Starter Pack',
        'tokens': 50,
        'price': 4.99,
        'bonus': 0,
        'price_id_env': 'STRIPE_TOKEN_STARTER_PRICE_ID',
        'description': 'Perfect for trying out our platform'
    },
    'popular': {
        'name': 'Popular Pack',
        'tokens': 110,
        'price': 9.99,
        'bonus': 10,
        'price_id_env': 'STRIPE_TOKEN_POPULAR_PRICE_ID',
        'description': 'Most popular choice - 10% bonus!',
        'badge': 'MOST POPULAR'
    },
    'pro': {
        'name': 'Pro Pack',
        'tokens': 250,
        'price': 19.99,
        'bonus': 50,
        'price_id_env': 'STRIPE_TOKEN_PRO_PRICE_ID',
        'description': 'For power users - 25% bonus!'
    },
    'creator': {
        'name': 'Creator Pack',
        'tokens': 700,
        'price': 49.99,
        'bonus': 200,
        'price_id_env': 'STRIPE_TOKEN_CREATOR_PRICE_ID',
        'description': 'Maximum value - 40% bonus!',
        'badge': 'BEST VALUE'
    }
}


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
