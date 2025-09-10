"""
API endpoints for search functionality.
"""
from flask import Blueprint, jsonify, request

from services.search_service import SearchService
from services.website_stats_service import WebsiteStatsService

# Initialize service
search_service = SearchService()
website_stats_service = WebsiteStatsService()

# Create Blueprint
search_bp = Blueprint('search', __name__, url_prefix='/api/search')

@search_bp.route('/', methods=['GET'])
def search():
    """Process a search query and return results."""
    # Get query parameters
    query = request.args.get('q', '')
    category = request.args.get('category', 'web')
    page = int(request.args.get('page', 1))
    results_per_page = int(request.args.get('per_page', 10))
    
    # Validate category
    if category not in ['web', 'news']:
        category = 'web'
    
    # Process the search query
    search_results = search_service.search(query, category, page, results_per_page)
    # Increment Doogle searches when a non-empty query is made
    if isinstance(query, str) and query.strip():
        website_stats_service.increment_doogle_searches(1)
    
    # Return the search results
    return jsonify(search_results)

@search_bp.route('/summary', methods=['POST'])
def generate_summary():
    """Generate AI summary from search results."""
    try:
        # Get request data
        data = request.get_json()
        
        if not data:
            return jsonify({
                "success": False,
                "error": "No JSON data provided"
            }), 400
        
        # Extract required fields
        search_results = data.get('search_results', [])
        query = data.get('query', '')
        category = data.get('category', 'web')
        
        # Validate inputs
        if not search_results:
            return jsonify({
                "success": False,
                "error": "No search results provided"
            }), 400
        
        if not query:
            return jsonify({
                "success": False,
                "error": "No search query provided"
            }), 400
        
        # Generate AI summary
        summary_result = search_service.generate_search_summary(search_results, query, category)
        
        return jsonify(summary_result)
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": "Internal server error",
            "details": str(e)
        }), 500