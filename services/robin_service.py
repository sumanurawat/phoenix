"""
Robin Service: Fetches latest news articles from newsdata.io API and optionally crawls
the full content from article URLs.
"""
import requests
import logging
import os
from datetime import datetime
from typing import Dict, Any, List, Optional
from services.utils import handle_api_error
from services.crawling_service import CrawlingService

# Load API key from environment
API_KEY = os.getenv("NEWSDATA_API_KEY")
BASE_URL = "https://newsdata.io/api/1/latest"  # Using latest endpoint instead of news

# Configure logging
logger = logging.getLogger(__name__)

class RobinService:
    """Service for fetching news articles using the newsdata.io API."""
    
    def __init__(self):
        """Initialize the news service with API key."""
        self.api_key = API_KEY
        if not self.api_key:
            logger.error("NewsData API key not found")
            raise ValueError("NewsData API key is required")
        
        # Initialize the crawling service
        self.crawling_service = CrawlingService()
        
        logger.info(f"Robin News Service initialized with API key: {self.api_key[:5]}...")
    
    def search_news(self, query: str, page: Optional[str] = None, language: str = "en", 
                    crawl_content: bool = True) -> Dict[str, Any]:
        """
        Search for news articles based on a query.
        
        Args:
            query: The search query
            page: Page token for pagination (if provided)
            language: Language code(s) for articles
            crawl_content: Whether to crawl the full content of each article
            
        Returns:
            Dictionary containing search results and metadata
        """
        try:
            # Prepare request parameters
            params = {
                "apikey": self.api_key,
                "language": language,
                "size": 10,  # Number of results per page
            }
            
            # Add query if provided
            if query and query.strip():
                params["q"] = query
            
            # Add page token if provided (newsdata.io uses a specific page token, not a number)
            if page and page != 1 and isinstance(page, str):
                params["page"] = page
            
            # Make request to NewsData API
            logger.info(f"Searching news for query: '{query}'")
            response = requests.get(BASE_URL, params=params, timeout=10)
            response.raise_for_status()
            
            # Parse response
            data = response.json()
            
            # Check for API error
            if data.get("status") == "error":
                error_message = data.get("results", {}).get("message", "Unknown API error")
                logger.error(f"NewsData API error: {error_message}")
                return {
                    "success": False,
                    "error": f"NewsData API error: {error_message}",
                    "articles": [],
                    "has_more": False
                }
            
            # Format results
            articles = []
            for item in data.get("results", []):
                article = {
                    "title": item.get("title", "No title"),
                    "link": item.get("link", "#"),
                    "pubDate": item.get("pubDate", "Unknown date"),
                    "source": item.get("source_id", "Unknown source"),
                    "description": item.get("description", ""),
                    "content": item.get("content", item.get("description", "No content available")),
                    "image_url": item.get("image_url", "")
                }
                
                # If crawl_content is enabled and we have a valid URL, fetch the full content
                if crawl_content and article["link"] and article["link"] != "#":
                    try:
                        logger.info(f"Crawling content for article: {article['title']}")
                        crawl_result = self.crawling_service.fetch_article_content(article["link"])
                        
                        if crawl_result["success"]:
                            # Update the article with the crawled content
                            article["content"] = crawl_result["content"]
                            # Update image if we got a better one from crawling
                            if crawl_result.get("image_url") and not article["image_url"]:
                                article["image_url"] = crawl_result["image_url"]
                            
                            logger.info(f"Successfully crawled content for article: {article['title']}")
                        else:
                            # Log the error but continue with the original content
                            logger.warning(f"Failed to crawl content for article: {article['title']} - {crawl_result.get('error')}")
                    except Exception as e:
                        logger.error(f"Error during content crawling for {article['title']}: {str(e)}")
                
                articles.append(article)
            
            # Return formatted results
            return {
                "success": True,
                "articles": articles,
                "has_more": bool(data.get("nextPage")),
                "next_page": data.get("nextPage"),
                "total_results": int(data.get("totalResults", 0)),
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        
        except requests.RequestException as e:
            logger.error(f"Error fetching news: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to fetch news: {str(e)}",
                "articles": [],
                "has_more": False
            }
    def get_article_content(self, article_url: str) -> Dict[str, Any]:
        """
        Fetch the full content for a specific article by crawling its URL.
        
        Args:
            article_url: The URL of the article to crawl
            
        Returns:
            Dictionary containing the crawled content and metadata
        """
        try:
            logger.info(f"Crawling content for article URL: {article_url}")
            
            # Crawl the article content
            crawl_result = self.crawling_service.fetch_article_content(article_url)
            
            if crawl_result["success"]:
                logger.info(f"Successfully crawled content for article URL: {article_url}")
                return {
                    "success": True,
                    "content": crawl_result["content"],
                    "image_url": crawl_result.get("image_url"),
                    "title": crawl_result.get("title")
                }
            else:
                logger.warning(f"Failed to crawl content for article URL: {article_url} - {crawl_result.get('error')}")
                return {
                    "success": False,
                    "error": crawl_result.get("error", "Failed to fetch article content")
                }
        
        except Exception as e:
            logger.error(f"Error fetching article content: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": f"An unexpected error occurred: {str(e)}"
            }
