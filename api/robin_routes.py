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
    
    result = robin_service.search_news(query, page, language)
    
    return jsonify(result)
