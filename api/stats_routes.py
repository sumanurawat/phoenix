"""
Stats Routes

API routes for website statistics and analytics.
"""
import logging
from flask import Blueprint, jsonify, render_template, session
from services.website_stats_service import WebsiteStatsService
from api.auth_routes import login_required

logger = logging.getLogger(__name__)

stats_bp = Blueprint('stats', __name__)
website_stats_service = WebsiteStatsService()

@stats_bp.route('/api/website-stats')
def api_website_stats():
    """API endpoint for website statistics."""
    try:
        stats = website_stats_service.get_stats_for_display()
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error fetching website stats API: {e}")
        return jsonify({'error': 'Unable to fetch stats'}), 500

@stats_bp.route('/admin/stats')
@login_required
def admin_stats_page():
    """Admin page for viewing website statistics."""
    try:
        stats = website_stats_service.get_website_stats()
        return render_template('admin_stats.html', 
                             stats=stats,
                             title='Website Statistics')
    except Exception as e:
        logger.error(f"Error loading admin stats: {e}")
        return render_template('error.html', 
                             error='Unable to load statistics'), 500
