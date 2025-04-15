"""
Robin News Routes: Routes for the Robin News reporter.
"""
from flask import Blueprint, render_template, request, jsonify
from services.robin_service import RobinService
from services.llm_service import LLMService

robin_bp = Blueprint("robin", __name__)
robin_service = RobinService()
llm_service = LLMService()

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

@robin_bp.route("/api/robin/generate_summary", methods=["POST"])
def generate_summary():
    """Endpoint to generate an AI summary of multiple news articles."""
    data = request.get_json()
    
    articles = data.get("articles", [])
    search_query = data.get("query", "News Search")
    
    if not articles or len(articles) == 0:
        return jsonify({
            "success": False,
            "error": "No articles provided for summary generation"
        })
    
    # Compile all article content with titles
    compiled_content = ""
    for i, article in enumerate(articles, 1):
        title = article.get("title", f"Article {i}")
        content = article.get("content", "")
        
        if content and len(content) > 20:  # Only include articles with meaningful content
            compiled_content += f"\n--- ARTICLE {i}: {title} ---\n{content}\n\n"
    
    if not compiled_content or len(compiled_content) < 100:
        return jsonify({
            "success": False,
            "error": "Insufficient content across articles to generate a summary"
        })
    
    # Create prompt for the LLM
    prompt = f"""
    Search Query: {search_query}
    
    Articles:
    {compiled_content}
    
    Task: Create a chatty tech gossip column summary based on these news articles. Use an engaging, 
    slightly informal tone as if you're a tech journalist writing for a popular blog. 
    Synthesize the key information across all articles, identify patterns and insights, 
    and present a cohesive overview of the topic. Include relevant details but keep it concise and entertaining.
    """
    
    # Generate summary using LLM service
    llm_response = llm_service.generate_text(prompt)
    
    # Check if the generation was successful
    if not llm_response.get("success", False):
        return jsonify({
            "success": False,
            "error": "Failed to generate summary: " + llm_response.get("error", "Unknown error")
        })
    
    return jsonify({
        "success": True,
        "summary": llm_response.get("text", ""),
        "model_used": llm_response.get("model_used", "Unknown model")
    })
