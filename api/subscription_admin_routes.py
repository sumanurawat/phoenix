"""
Subscription Admin Routes

Admin API routes for managing subscriptions, monitoring health,
and manually triggering subscription management tasks.
"""

import logging
from flask import Blueprint, request, jsonify, session
from api.auth_routes import login_required
from services.subscription_expiration_service import SubscriptionExpirationService
from services.subscription_management_service import SubscriptionManagementService
from services.subscription_cron_service import SubscriptionCronService

logger = logging.getLogger(__name__)

# Create blueprint
subscription_admin_bp = Blueprint('subscription_admin', __name__, url_prefix='/admin/subscriptions')

# Initialize services
expiration_service = SubscriptionExpirationService()
management_service = SubscriptionManagementService()
cron_service = SubscriptionCronService()

def admin_required(f):
    """Decorator to require admin access."""
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if user is logged in
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        
        # For now, allow any logged-in user to access admin functions
        # In production, you'd check for admin role/permissions
        user_email = session.get('user_email', '')
        
        # Add your admin email check here
        admin_emails = ['admin@phoenix.ai', 'suman@phoenix.ai']  # Configure as needed
        if user_email not in admin_emails:
            return jsonify({'error': 'Admin access required'}), 403
        
        return f(*args, **kwargs)
    return decorated_function

@subscription_admin_bp.route('/health', methods=['GET'])
@login_required
@admin_required
def subscription_health():
    """Get overall subscription system health."""
    try:
        # Get expiration summary
        expiration_summary = expiration_service.get_expiration_summary()
        
        # Get available tiers
        available_tiers = management_service.get_subscription_tiers()
        
        # Get scheduler status
        scheduler_status = cron_service.get_scheduler_status()
        
        # Get recent execution history
        execution_history = cron_service.get_execution_history(limit=5)
        
        health_data = {
            'system_status': 'healthy',
            'subscription_summary': expiration_summary,
            'available_tiers': {name: tier['name'] for name, tier in available_tiers.items()},
            'scheduler': scheduler_status,
            'recent_executions': execution_history,
            'services': {
                'expiration_service': 'active',
                'management_service': 'active',
                'cron_service': 'active' if scheduler_status['is_running'] else 'inactive'
            }
        }
        
        # Determine overall health
        if expiration_summary.get('needs_attention', 0) > 0:
            health_data['system_status'] = 'warning'
        
        if 'error' in expiration_summary or not scheduler_status['is_running']:
            health_data['system_status'] = 'error'
        
        return jsonify(health_data)
        
    except Exception as e:
        logger.error(f"Error getting subscription health: {e}")
        return jsonify({
            'system_status': 'error',
            'error': str(e)
        }), 500

@subscription_admin_bp.route('/expiration/check', methods=['POST'])
@login_required
@admin_required
def run_expiration_check():
    """Manually run subscription expiration check."""
    try:
        logger.info("Admin manually triggered expiration check")
        results = expiration_service.check_all_expired_subscriptions()
        
        return jsonify({
            'success': True,
            'message': 'Expiration check completed',
            'results': results
        })
        
    except Exception as e:
        logger.error(f"Error running expiration check: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@subscription_admin_bp.route('/downgrades/process', methods=['POST'])
@login_required
@admin_required
def process_scheduled_downgrades():
    """Manually process scheduled downgrades."""
    try:
        logger.info("Admin manually triggered downgrade processing")
        results = management_service.process_scheduled_downgrades()
        
        return jsonify({
            'success': True,
            'message': 'Scheduled downgrades processed',
            'results': results
        })
        
    except Exception as e:
        logger.error(f"Error processing downgrades: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@subscription_admin_bp.route('/cron/task/<task_name>', methods=['POST'])
@login_required
@admin_required
def run_cron_task(task_name):
    """Manually run a specific cron task."""
    try:
        logger.info(f"Admin manually triggered cron task: {task_name}")
        results = cron_service.run_task_manually(task_name)
        
        if results['success']:
            return jsonify({
                'success': True,
                'message': f'Task {task_name} completed',
                'results': results
            })
        else:
            return jsonify({
                'success': False,
                'error': results.get('error', 'Task failed'),
                'available_tasks': results.get('available_tasks', [])
            }), 400
        
    except Exception as e:
        logger.error(f"Error running cron task {task_name}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@subscription_admin_bp.route('/cron/status', methods=['GET'])
@login_required
@admin_required
def get_cron_status():
    """Get cron scheduler status."""
    try:
        status = cron_service.get_scheduler_status()
        return jsonify(status)
        
    except Exception as e:
        logger.error(f"Error getting cron status: {e}")
        return jsonify({'error': str(e)}), 500

@subscription_admin_bp.route('/cron/start', methods=['POST'])
@login_required
@admin_required
def start_cron_scheduler():
    """Start the cron scheduler."""
    try:
        cron_service.start_scheduler()
        return jsonify({
            'success': True,
            'message': 'Cron scheduler started'
        })
        
    except Exception as e:
        logger.error(f"Error starting cron scheduler: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@subscription_admin_bp.route('/cron/stop', methods=['POST'])
@login_required
@admin_required
def stop_cron_scheduler():
    """Stop the cron scheduler."""
    try:
        cron_service.stop_scheduler()
        return jsonify({
            'success': True,
            'message': 'Cron scheduler stopped'
        })
        
    except Exception as e:
        logger.error(f"Error stopping cron scheduler: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@subscription_admin_bp.route('/cron/history', methods=['GET'])
@login_required
@admin_required
def get_cron_history():
    """Get cron execution history."""
    try:
        limit = request.args.get('limit', 20, type=int)
        history = cron_service.get_execution_history(limit=limit)
        
        return jsonify({
            'history': history,
            'total_returned': len(history)
        })
        
    except Exception as e:
        logger.error(f"Error getting cron history: {e}")
        return jsonify({'error': str(e)}), 500

@subscription_admin_bp.route('/tiers', methods=['GET'])
@login_required
@admin_required
def get_subscription_tiers():
    """Get all available subscription tiers."""
    try:
        tiers = management_service.get_subscription_tiers()
        return jsonify({'tiers': tiers})
        
    except Exception as e:
        logger.error(f"Error getting subscription tiers: {e}")
        return jsonify({'error': str(e)}), 500

@subscription_admin_bp.route('/user/<firebase_uid>/tier', methods=['GET'])
@login_required
@admin_required
def get_user_tier(firebase_uid):
    """Get current tier for a specific user."""
    try:
        current_tier = management_service.get_current_subscription_tier(firebase_uid)
        subscription_status = expiration_service.stripe_service.get_subscription_status(firebase_uid)
        
        return jsonify({
            'firebase_uid': firebase_uid,
            'current_tier': current_tier,
            'subscription_status': subscription_status
        })
        
    except Exception as e:
        logger.error(f"Error getting user tier: {e}")
        return jsonify({'error': str(e)}), 500

@subscription_admin_bp.route('/user/<firebase_uid>/upgrade', methods=['POST'])
@login_required
@admin_required
def upgrade_user_subscription(firebase_uid):
    """Upgrade a user's subscription (admin override)."""
    try:
        data = request.get_json()
        to_tier = data.get('to_tier')
        billing_interval = data.get('billing_interval', 'monthly')
        
        if not to_tier:
            return jsonify({'error': 'to_tier is required'}), 400
        
        logger.info(f"Admin upgrading user {firebase_uid} to {to_tier}")
        result = management_service.upgrade_subscription(firebase_uid, to_tier, billing_interval)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error upgrading user subscription: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@subscription_admin_bp.route('/user/<firebase_uid>/downgrade', methods=['POST'])
@login_required
@admin_required
def schedule_user_downgrade(firebase_uid):
    """Schedule a user's subscription downgrade."""
    try:
        data = request.get_json()
        to_tier = data.get('to_tier')
        
        if not to_tier:
            return jsonify({'error': 'to_tier is required'}), 400
        
        logger.info(f"Admin scheduling downgrade for user {firebase_uid} to {to_tier}")
        result = management_service.schedule_downgrade(firebase_uid, to_tier)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error scheduling user downgrade: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@subscription_admin_bp.route('/stats', methods=['GET'])
@login_required
@admin_required
def get_subscription_stats():
    """Get subscription statistics."""
    try:
        from firebase_admin import firestore
        
        if not expiration_service.db:
            return jsonify({'error': 'Database not available'}), 500
        
        # Get subscription counts by tier
        tier_counts = {}
        
        # Count active subscriptions by plan_id
        active_subs = expiration_service.db.collection('user_subscriptions')\
            .where('status', 'in', ['active', 'trialing'])\
            .get()
        
        for sub_doc in active_subs:
            sub_data = sub_doc.to_dict()
            plan_id = sub_data.get('plan_id', 'zero')
            
            # Map plan_id to tier name
            tier_name = 'free'
            for tier, config in management_service.SUBSCRIPTION_TIERS.items():
                if config['plan_id'] == plan_id:
                    tier_name = tier
                    break
            
            tier_counts[tier_name] = tier_counts.get(tier_name, 0) + 1
        
        # Get total users
        all_users = expiration_service.db.collection('users').get()
        total_users = len(all_users)
        
        # Calculate conversion rate
        premium_users = sum(count for tier, count in tier_counts.items() if tier != 'free')
        conversion_rate = (premium_users / total_users * 100) if total_users > 0 else 0
        
        stats = {
            'total_users': total_users,
            'tier_distribution': tier_counts,
            'premium_users': premium_users,
            'free_users': tier_counts.get('free', 0),
            'conversion_rate': round(conversion_rate, 2),
            'generated_at': datetime.now().isoformat()
        }
        
        return jsonify(stats)
        
    except Exception as e:
        logger.error(f"Error getting subscription stats: {e}")
        return jsonify({'error': str(e)}), 500