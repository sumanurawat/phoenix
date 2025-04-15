"""
Robin News Routes: Routes for the Robin News reporter.
"""
from flask import Blueprint, render_template, request, jsonify
from services.robin_service import RobinService

robin_bp = Blueprint("robin", __name__)
robin_service = RobinService()

@robin_bp.route("/robin", methods=["GET"])
def robin_page():
    """Render the Robin News reporter page."""
    return render_template("robin.html", title="Robin News Reporter")

@robin_bp.route("/api/robin/search", methods=["POST"])
def search_news():
    """Endpoint to search for news articles."""
    data = request.get_json()
    
    query = data.get("query", "")
    page = data.get("page", 1)
    language = data.get("language", "en")
    
    # First request - get basic article info quickly without crawling
    result = robin_service.search_news(query, page, language, crawl_content=False)
    
    return jsonify(result)

@robin_bp.route("/api/robin/article_content", methods=["POST"])
def get_article_content():
    """Endpoint to fetch full content for a specific article."""
    data = request.get_json()
    
    article_url = data.get("article_url", "")
    
    if not article_url or article_url == "#":
        return jsonify({
            "success": False,
            "error": "Invalid article URL"
        })
    
    # Crawl the specific article
    result = robin_service.get_article_content(article_url)
    
    return jsonify(result)
