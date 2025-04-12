"""
API endpoints for search functionality.
"""
from flask import Blueprint, jsonify, request

from services.search_service import SearchService

# Initialize service
search_service = SearchService()

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
    
    # Return the search results
    return jsonify(search_results)