"""
Service for handling search functionality.
"""
import random
import time
import logging
from typing import Dict, List, Any
import re
import requests
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Import configurations
from config.settings import GOOGLE_API_KEY, GOOGLE_SEARCH_ENGINE_ID

# Set up logging
logger = logging.getLogger(__name__)

class SearchService:
    """Service for handling search operations."""
    
    def __init__(self):
        """Initialize the search service."""
        # We'll focus only on search and news categories
        self.supported_categories = ["web", "news"]
        
        # Pre-define some news sources for better quality results (used for simulation only)
        self.news_sources = [
            "The New York Times", "CNN", "BBC News", "Reuters", "Associated Press",
            "The Washington Post", "The Guardian", "Bloomberg", "CNBC", "The Verge",
            "TechCrunch", "Wired", "Scientific American", "National Geographic"
        ]
        
        # Check if we have Google Search API credentials
        self.has_api_credentials = bool(GOOGLE_API_KEY and GOOGLE_SEARCH_ENGINE_ID)
        
        if self.has_api_credentials:
            logger.info("Google Search API credentials found. Using real search.")
        else:
            logger.warning("Google Search API credentials not found. Using simulated search results.")
    
    def search(self, query: str, category: str = "web", page: int = 1, results_per_page: int = 10) -> Dict[str, Any]:
        """
        Perform a search with the given query.
        
        Args:
            query: The search query string
            category: Type of search (web or news)
            page: The page number for pagination
            results_per_page: Number of results per page
            
        Returns:
            Dictionary containing search results and metadata
        """
        if not query.strip():
            return {
                "query": query,
                "category": category,
                "total_results": 0,
                "search_time": 0,
                "page": page,
                "results_per_page": results_per_page,
                "results": [],
                "has_more": False
            }
        
        # Record start time for calculating search time
        start_time = time.time()
        
        if self.has_api_credentials:
            # Use the real Google Search API
            try:
                if category.lower() == "news":
                    results = self._google_news_search(query, page, results_per_page)
                else:
                    results = self._google_web_search(query, page, results_per_page)
                
                # Calculate search time
                search_time = time.time() - start_time
                
                return results
            except Exception as e:
                logger.error(f"Error using Google Search API: {str(e)}")
                logger.info("Falling back to simulated search results.")
                # Fall back to simulated search if API call fails
        
        # Generate simulated search results based on the query and category
        if category.lower() == "news":
            all_results = self._generate_news_results(query)
        else:
            all_results = self._generate_web_results(query)
        
        # Calculate pagination
        start_idx = (page - 1) * results_per_page
        end_idx = start_idx + results_per_page
        page_results = all_results[start_idx:end_idx]
        has_more = end_idx < len(all_results)
        
        # Calculate search time (simulated)
        search_time = time.time() - start_time
        
        return {
            "query": query,
            "category": category,
            "total_results": len(all_results),
            "search_time": round(search_time, 2),
            "page": page,
            "results_per_page": results_per_page,
            "results": page_results,
            "has_more": has_more
        }

    def _google_web_search(self, query: str, page: int = 1, results_per_page: int = 10) -> Dict[str, Any]:
        """
        Perform a web search using Google Custom Search API.
        
        Args:
            query: The search query
            page: The page number (1-based)
            results_per_page: Number of results per page (max 10)
            
        Returns:
            Dictionary with search results and metadata
        """
        # Build the service
        service = build("customsearch", "v1", developerKey=GOOGLE_API_KEY)
        
        # Calculate start index for pagination (Google API uses 1-based indexing)
        start_index = (page - 1) * results_per_page + 1
        
        # Execute the search
        try:
            res = service.cse().list(
                q=query,
                cx=GOOGLE_SEARCH_ENGINE_ID,
                start=start_index,
                num=min(results_per_page, 10)  # Google limits to 10 results per request
            ).execute()
            
            # Check if we got any search information
            search_info = res.get("searchInformation", {})
            total_results = int(search_info.get("totalResults", 0))
            
            # Process search results
            results = []
            if "items" in res:
                for item in res["items"]:
                    results.append({
                        "title": item.get("title", ""),
                        "url": item.get("link", ""),
                        "description": item.get("snippet", ""),
                        "category": "web"
                    })
            
            return {
                "query": query,
                "category": "web",
                "total_results": total_results,
                "search_time": float(search_info.get("searchTime", 0)),
                "page": page,
                "results_per_page": results_per_page,
                "results": results,
                "has_more": total_results > (start_index + len(results) - 1)
            }
            
        except HttpError as e:
            logger.error(f"Google Search API error: {str(e)}")
            raise
        
    def _google_news_search(self, query: str, page: int = 1, results_per_page: int = 10) -> Dict[str, Any]:
        """
        Perform a news search using Google Custom Search API.
        
        Args:
            query: The search query
            page: The page number (1-based)
            results_per_page: Number of results per page (max 10)
            
        Returns:
            Dictionary with search results and metadata
        """
        # Build the service
        service = build("customsearch", "v1", developerKey=GOOGLE_API_KEY)
        
        # Calculate start index for pagination
        start_index = (page - 1) * results_per_page + 1
        
        # Execute the search with a news filter
        try:
            res = service.cse().list(
                q=query,
                cx=GOOGLE_SEARCH_ENGINE_ID,
                start=start_index,
                num=min(results_per_page, 10),  # Google limits to 10 results per request
                sort="date",  # Sort by date for news
                dateRestrict="d7"  # Restrict to last 7 days
            ).execute()
            
            # Check if we got any search information
            search_info = res.get("searchInformation", {})
            total_results = int(search_info.get("totalResults", 0))
            
            # Process search results
            results = []
            if "items" in res:
                for item in res["items"]:
                    # Try to extract source and date from the displayed link
                    display_link = item.get("displayLink", "")
                    # Extract a date if available in the snippet or metatags
                    date = ""
                    if "pagemap" in item and "metatags" in item["pagemap"]:
                        date = item["pagemap"]["metatags"][0].get("article:published_time", "")
                    
                    results.append({
                        "title": item.get("title", ""),
                        "url": item.get("link", ""),
                        "description": item.get("snippet", ""),
                        "source": display_link,
                        "date": date,
                        "category": "news"
                    })
            
            return {
                "query": query,
                "category": "news",
                "total_results": total_results,
                "search_time": float(search_info.get("searchTime", 0)),
                "page": page,
                "results_per_page": results_per_page,
                "results": results,
                "has_more": total_results > (start_index + len(results) - 1)
            }
            
        except HttpError as e:
            logger.error(f"Google Search API error: {str(e)}")
            raise
    
    def _generate_web_results(self, query: str) -> List[Dict[str, str]]:
        """
        Generate simulated web search results based on the query.
        
        Args:
            query: The search query string
            
        Returns:
            List of search result objects
        """
        # Create a list of simulated result titles and descriptions
        result_count = random.randint(8, 25)  # More reasonable number of results
        results = []
        
        # Create more targeted domains based on query
        tech_domains = [
            "github.com", "stackoverflow.com", "dev.to", "medium.com", 
            "python.org", "javascript.info", "reactjs.org", "angular.io", 
            "vuejs.org", "nodejs.org", "flask.palletsprojects.com", "djangoproject.com"
        ]
        
        reference_domains = [
            "wikipedia.org", "britannica.com", "dictionary.com", "thesaurus.com",
            "howstuffworks.com", "investopedia.com", "healthline.com", "webmd.com"
        ]
        
        commerce_domains = [
            "amazon.com", "ebay.com", "etsy.com", "walmart.com", "target.com",
            "bestbuy.com", "homedepot.com", "booking.com", "expedia.com"
        ]
        
        education_domains = [
            "harvard.edu", "stanford.edu", "mit.edu", "coursera.org", "udemy.com",
            "edx.org", "khanacademy.org", "ted.com", "academia.edu"
        ]
        
        # Select domain category based on query content
        query_lower = query.lower()
        if any(word in query_lower for word in ["code", "programming", "developer", "software", "python", "javascript"]):
            domains = tech_domains
        elif any(word in query_lower for word in ["what is", "history", "meaning", "define", "science"]):
            domains = reference_domains
        elif any(word in query_lower for word in ["buy", "shop", "price", "cheap", "purchase", "product"]):
            domains = commerce_domains
        elif any(word in query_lower for word in ["learn", "course", "tutorial", "education", "university", "college"]):
            domains = education_domains
        else:
            # Mix of domains if query doesn't match specific categories
            domains = tech_domains + reference_domains + commerce_domains + education_domains
            random.shuffle(domains)
            domains = domains[:12]
        
        words = query_lower.split()
        
        for i in range(result_count):
            # Create varied titles that include the query terms
            capitalized_words = [word.capitalize() for word in words]
            
            # More relevant title extras based on the query
            if any(word in query_lower for word in ["tutorial", "learn", "how to"]):
                title_extras = [
                    "Guide", "Tutorial", "Examples", "Step-by-Step Guide", 
                    "Tips and Tricks", "Introduction to", "How to Use",
                    "Complete Reference", "Quick Start", "Beginner's Guide"
                ]
            elif any(word in query_lower for word in ["best", "top", "review"]):
                title_extras = [
                    "Best Options", "Top 10", "Reviews", "Comparison", 
                    "Alternatives", "Recommendations", "Buyer's Guide",
                    "Rated and Reviewed", "Expert Picks"
                ]
            else:
                title_extras = [
                    "Ultimate Guide", "Explained", "Overview", "Everything You Need to Know", 
                    "In-Depth Analysis", "Comprehensive Guide", "Essential Information"
                ]
            
            # Select a random domain
            domain = random.choice(domains)
            
            # Create a title with query terms
            random_extras = random.choice(title_extras)
            title_formats = [
                f"{' '.join(capitalized_words)}: {random_extras}",
                f"{random_extras} to {' '.join(capitalized_words)}",
                f"{' '.join(capitalized_words)} - {random_extras}",
                f"The Complete Guide to {' '.join(words)}",
                f"{' '.join(capitalized_words)}"
            ]
            title = random.choice(title_formats)
            
            # Create URL based on title
            url_slug = re.sub(r'[^a-z0-9]+', '-', title.lower())
            url = f"https://www.{domain}/{url_slug}"
            
            # Create more relevant descriptions
            if domain in tech_domains:
                description_templates = [
                    f"Learn everything about {query} with code examples and best practices.",
                    f"A comprehensive developer guide to {query} with tutorials and sample code.",
                    f"This developer resource explains how to use {query} in your projects.",
                    f"Find code examples, tutorials, and documentation for {query}.",
                    f"Improve your coding skills with our {query} guide for developers."
                ]
            elif domain in reference_domains:
                description_templates = [
                    f"{query.capitalize()} explained: definitions, examples, and key concepts.",
                    f"Everything you need to know about {query} in a comprehensive reference.",
                    f"Learn about the history, meaning, and significance of {query}.",
                    f"A complete encyclopedia entry on {query} with facts and information.",
                    f"Detailed explanation of {query} with references and further reading."
                ]
            elif domain in commerce_domains:
                description_templates = [
                    f"Shop for the best {query} products at competitive prices with free shipping.",
                    f"Compare prices and reviews for {query} from top brands and sellers.",
                    f"Find deals on {query} with options for every budget and need.",
                    f"Discover high-quality {query} products with customer reviews and ratings.",
                    f"Buy {query} online with secure checkout and fast delivery options."
                ]
            elif domain in education_domains:
                description_templates = [
                    f"Take online courses to learn about {query} from expert instructors.",
                    f"Study {query} with lectures, assignments, and certificates from top universities.",
                    f"Enhance your knowledge of {query} with educational resources and materials.",
                    f"Academic papers and research on {query} from leading scholars and institutions.",
                    f"Join online classes and tutorials to master {query} at your own pace."
                ]
            else:
                description_templates = [
                    f"Learn all about {query} with our comprehensive guide.",
                    f"Discover the best practices for working with {query}.",
                    f"This article explains how to use {query} effectively.",
                    f"Everything you need to know about {query} in one place.",
                    f"A deep dive into {query} with practical examples."
                ]
            
            description = random.choice(description_templates)
            
            results.append({
                "title": title,
                "url": url,
                "description": description,
                "category": "web"
            })
        
        return results
    
    def _generate_news_results(self, query: str) -> List[Dict[str, str]]:
        """
        Generate simulated news results based on the query.
        
        Args:
            query: The search query string
            
        Returns:
            List of news result objects
        """
        # Create a list of simulated news articles
        result_count = random.randint(5, 20)
        results = []
        
        words = query.lower().split()
        
        # Current date is April 12, 2025
        current_year = 2025
        current_month = 4
        
        for i in range(result_count):
            # Select news source
            source = random.choice(self.news_sources)
            
            # Create title with query terms
            capitalized_words = [word.capitalize() for word in words]
            
            # Different formats for news headlines
            headline_formats = [
                f"{' '.join(capitalized_words)}: What You Need to Know",
                f"Breaking: New Developments in {' '.join(capitalized_words)}",
                f"{' '.join(capitalized_words)} Update: Latest Information",
                f"The Future of {' '.join(capitalized_words)} According to Experts",
                f"{random.choice(capitalized_words)} Crisis Escalates as {' '.join(capitalized_words[1:] if len(capitalized_words) > 1 else capitalized_words)}",
                f"Report: {' '.join(capitalized_words)} Shows Promising Results",
                f"Analysis: How {' '.join(capitalized_words)} Is Changing the Industry"
            ]
            
            title = random.choice(headline_formats)
            
            # Create random recent date for the news (within past month)
            day = random.randint(1, 12)
            # Format: April 10, 2025
            months = ["January", "February", "March", "April", "May", "June", 
                     "July", "August", "September", "October", "November", "December"]
            date = f"{months[current_month-1]} {day}, {current_year}"
            
            # Create news URL
            url_slug = re.sub(r'[^a-z0-9]+', '-', title.lower())
            domain_part = source.lower().replace(' ', '')
            url = f"https://www.{domain_part}.com/news/{url_slug}"
            
            # Create news description
            description_templates = [
                f"{source} - {date} - {query.capitalize()} has become a major focus for industry leaders as new developments emerge.",
                f"{source} - {date} - Recent reports about {query} show significant changes in how experts view the situation.",
                f"{source} - {date} - The latest update on {query} reveals important information for stakeholders and the public.",
                f"{source} - {date} - Experts weigh in on the implications of recent {query} developments.",
                f"{source} - {date} - A new study on {query} published today provides valuable insights into ongoing trends."
            ]
            
            description = random.choice(description_templates)
            
            results.append({
                "title": title,
                "url": url,
                "description": description,
                "source": source,
                "date": date,
                "category": "news"
            })
        
        return results