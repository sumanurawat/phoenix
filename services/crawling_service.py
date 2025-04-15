"""
Crawling Service: Fetches full content of articles from their URLs.
"""
import requests
import logging
from bs4 import BeautifulSoup
from typing import Dict, Any, Optional
import time
import random

# Configure logging
logger = logging.getLogger(__name__)

class CrawlingService:
    """Service for crawling and extracting content from web pages."""
    
    def __init__(self):
        """Initialize the crawling service."""
        # Set up headers to mimic a browser
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
        }
    
    def fetch_article_content(self, url: str) -> Dict[str, Any]:
        """
        Fetch and extract the main content from an article URL.
        
        Args:
            url: The URL of the article to crawl
            
        Returns:
            Dictionary containing the extracted content and metadata
        """
        try:
            # Add a small random delay to avoid overwhelming the target site
            time.sleep(random.uniform(0.5, 2.0))
            
            # Make the request
            logger.info(f"Crawling article: {url}")
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()
            
            # Parse the HTML content
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract title (if available)
            title = None
            title_tag = soup.find('title')
            if title_tag:
                title = title_tag.get_text().strip()
            
            # Extract main content
            # This is the challenging part as different sites structure their content differently
            # We'll implement a heuristic approach to find the main content
            
            # Strategy 1: Look for common article container elements
            content = None
            potential_content_elements = [
                soup.find('article'),
                soup.find('div', class_='article-body'),
                soup.find('div', class_='content'),
                soup.find('div', class_='post-content'),
                soup.find('div', class_='entry-content'),
                soup.find('div', class_='story-body'),
                soup.find('div', class_='main-content'),
                soup.find('div', {'id': 'content'}),
                soup.find('div', {'id': 'article-body'})
            ]
            
            # Use the first element that is found
            for element in potential_content_elements:
                if element:
                    # Remove unwanted elements like ads, social sharing buttons, etc.
                    for unwanted in element.find_all(['script', 'style', 'iframe', 'aside', 'nav']):
                        unwanted.decompose()
                    
                    # Get the text and clean it up
                    content = element.get_text(separator='\n').strip()
                    break
            
            # Strategy 2: If no content found, look for the largest text block
            if not content:
                paragraphs = soup.find_all('p')
                if paragraphs:
                    content = '\n\n'.join([p.get_text().strip() for p in paragraphs 
                                          if len(p.get_text().strip()) > 50])
            
            # If still no content, return a fallback message
            if not content or len(content) < 100:  # Set a minimum content length
                return {
                    "success": False,
                    "error": "Could not extract meaningful content from the article",
                    "content": "The article content could not be extracted. Please visit the original URL."
                }
            
            # Extract the first image (if available)
            image_url = None
            main_image = soup.find('meta', property='og:image')
            if main_image and 'content' in main_image.attrs:
                image_url = main_image['content']
            
            if not image_url:
                # Try to find a large image in the content
                for img in soup.find_all('img'):
                    if img.get('src') and (img.get('width') or 'width' in img.get('style', '')):
                        image_url = img.get('src')
                        # If it's a relative URL, make it absolute
                        if image_url.startswith('/'):
                            # Extract domain from the article URL
                            from urllib.parse import urlparse
                            parsed_url = urlparse(url)
                            domain = f"{parsed_url.scheme}://{parsed_url.netloc}"
                            image_url = domain + image_url
                        break
            
            return {
                "success": True,
                "title": title,
                "content": content,
                "image_url": image_url,
                "source_url": url
            }
            
        except requests.RequestException as e:
            logger.error(f"Error crawling article: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to fetch article: {str(e)}",
                "content": None
            }
        except Exception as e:
            logger.error(f"Unexpected error in article crawling: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": f"An unexpected error occurred: {str(e)}",
                "content": None
            }
