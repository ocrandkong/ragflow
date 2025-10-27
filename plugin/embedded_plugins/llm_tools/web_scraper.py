"""
Web Scraper Plugin for RAGFlow

This plugin provides web scraping capabilities to extract content from web pages.
Supports extracting text, markdown, and structured data from URLs.
Perfect for retrieving privacy policies, terms of service, documentation, etc.
"""

import json
import logging
from typing import Optional
from urllib.parse import urlparse

try:
    import requests
    from bs4 import BeautifulSoup
    from markdownify import markdownify as md
    SCRAPER_AVAILABLE = True
except ImportError:
    requests = None  # type: ignore
    BeautifulSoup = None  # type: ignore
    md = None  # type: ignore
    SCRAPER_AVAILABLE = False
    logging.warning("Web scraper dependencies not installed. Run: pip install requests beautifulsoup4 markdownify lxml")

from plugin.llm_tool_plugin import LLMToolMetadata, LLMToolPlugin


class WebScraperPlugin(LLMToolPlugin):
    """
    A LLM tool plugin to scrape and extract content from web pages.
    
    Features:
    - Extract content as Markdown (best for LLM), plain text, or HTML
    - Target specific sections using CSS selectors
    - Automatic cleaning (remove scripts, styles, etc.)
    - Support for privacy policies, terms, documentation
    """
    _version_ = "1.0.0"
    
    DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    DEFAULT_TIMEOUT = 30

    @classmethod
    def get_metadata(cls) -> LLMToolMetadata:
        return {
            "name": "web_scraper",
            "displayName": "$t:web_scraper.name",
            "description": (
                "Scrape and extract content from web pages. Perfect for retrieving privacy policies, "
                "terms of service, documentation, articles, and other web content. Supports extracting "
                "content as markdown (best for LLM), plain text, or HTML. Can target specific sections "
                "using CSS selectors."
            ),
            "displayDescription": "$t:web_scraper.description",
            "parameters": {
                "url": {
                    "type": "string",
                    "description": "The URL of the web page to scrape (must include http:// or https://)",
                    "displayDescription": "$t:web_scraper.params.url",
                    "required": True
                },
                "format": {
                    "type": "string",
                    "enum": ["markdown", "text", "html"],
                    "description": "Output format: 'markdown' (default, best for LLM), 'text' (plain text), or 'html' (raw HTML)",
                    "displayDescription": "$t:web_scraper.params.format",
                    "default": "markdown"
                },
                "selector": {
                    "type": "string",
                    "description": "Optional CSS selector to extract only specific content (e.g., 'article', '.main-content', '#privacy-policy'). If not provided, extracts entire page.",
                    "displayDescription": "$t:web_scraper.params.selector",
                    "required": False
                },
                "remove_scripts": {
                    "type": "boolean",
                    "description": "Remove <script> tags from output (default: true)",
                    "displayDescription": "$t:web_scraper.params.remove_scripts",
                    "default": True
                },
                "remove_styles": {
                    "type": "boolean",
                    "description": "Remove <style> tags from output (default: true)",
                    "displayDescription": "$t:web_scraper.params.remove_styles",
                    "default": True
                },
                "timeout": {
                    "type": "integer",
                    "description": "Request timeout in seconds (default: 30)",
                    "displayDescription": "$t:web_scraper.params.timeout",
                    "default": 30,
                    "minimum": 5,
                    "maximum": 120
                }
            }
        }

    def invoke(
        self,
        url: str,
        format: str = "markdown",
        selector: Optional[str] = None,
        remove_scripts: bool = True,
        remove_styles: bool = True,
        timeout: int = DEFAULT_TIMEOUT
    ) -> str:
        """
        Scrape content from a web page.
        
        Args:
            url: The URL to scrape
            format: Output format - 'markdown', 'text', or 'html'
            selector: CSS selector to extract specific content (optional)
            remove_scripts: Remove script tags
            remove_styles: Remove style tags
            timeout: Request timeout in seconds
            
        Returns:
            A JSON string containing the scraped content and metadata
        """
        if not SCRAPER_AVAILABLE:
            result = {
                "success": False,
                "error": "Dependencies not installed",
                "message": "Web scraper dependencies not installed. Please install: beautifulsoup4, lxml, markdownify"
            }
            return json.dumps(result, ensure_ascii=False, indent=2)
        
        try:
            logging.info(f"Web scraper plugin invoked for URL: {url}")
            
            # Validate URL
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                result = {
                    "success": False,
                    "url": url,
                    "error": "Invalid URL",
                    "message": f"URL must include scheme (http/https): {url}"
                }
                return json.dumps(result, ensure_ascii=False, indent=2)
            
            # Set headers
            headers = {
                "User-Agent": self.DEFAULT_USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
            }
            
            # Fetch the page
            logging.info(f"Fetching URL: {url}")
            response = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
            response.raise_for_status()
            
            # Detect encoding
            response.encoding = response.apparent_encoding
            
            # Parse HTML
            soup = BeautifulSoup(response.text, 'lxml')
            
            # Remove unwanted elements
            if remove_scripts:
                for script in soup.find_all('script'):
                    script.decompose()
            
            if remove_styles:
                for style in soup.find_all('style'):
                    style.decompose()
            
            # Remove other noise
            for tag in soup.find_all(['noscript', 'iframe']):
                tag.decompose()
            
            # Extract specific content if selector provided
            if selector:
                selected = soup.select(selector)
                if not selected:
                    result = {
                        "success": False,
                        "url": url,
                        "error": "Selector not found",
                        "message": f"No elements found matching selector: {selector}"
                    }
                    return json.dumps(result, ensure_ascii=False, indent=2)
                # Use first matching element
                content_soup = selected[0]
            else:
                content_soup = soup
            
            # Extract metadata
            title = soup.find('title')
            title_text = title.get_text(strip=True) if title else ""
            
            meta_description = soup.find('meta', attrs={'name': 'description'})
            description = meta_description.get('content', '') if meta_description else ""
            
            # Format output
            if format.lower() == "markdown":
                # Convert to markdown
                content = md(str(content_soup), heading_style="ATX", bullets="-")
            elif format.lower() == "text":
                # Plain text
                content = content_soup.get_text(separator='\n', strip=True)
            elif format.lower() == "html":
                # Clean HTML
                content = str(content_soup)
            else:
                result = {
                    "success": False,
                    "url": url,
                    "error": "Invalid format",
                    "message": f"Format must be 'markdown', 'text', or 'html', got: {format}"
                }
                return json.dumps(result, ensure_ascii=False, indent=2)
            
            # Build result
            result = {
                "success": True,
                "url": url,
                "final_url": response.url,  # After redirects
                "title": title_text,
                "description": description,
                "content": content,
                "content_length": len(content),
                "format": format,
                "status_code": response.status_code,
                "content_type": response.headers.get('Content-Type', ''),
                "selector_used": selector if selector else None,
                "message": f"Successfully scraped {url}"
            }
            
            logging.info(f"Successfully scraped {url} ({len(content)} chars)")
            return json.dumps(result, ensure_ascii=False, indent=2)
            
        except requests.exceptions.Timeout:
            result = {
                "success": False,
                "url": url,
                "error": "Request timeout",
                "message": f"Request timed out after {timeout} seconds"
            }
            return json.dumps(result, ensure_ascii=False, indent=2)
            
        except requests.exceptions.RequestException as e:
            result = {
                "success": False,
                "url": url,
                "error": "Request failed",
                "message": f"Failed to fetch URL: {str(e)}"
            }
            return json.dumps(result, ensure_ascii=False, indent=2)
            
        except Exception as e:
            logging.error(f"Web scraping error for {url}: {e}", exc_info=True)
            result = {
                "success": False,
                "url": url,
                "error": type(e).__name__,
                "message": f"Scraping failed: {str(e)}"
            }
            return json.dumps(result, ensure_ascii=False, indent=2)

    @classmethod
    def clear_cache(cls):
        """Clear any cached data (if needed in future)"""
        logging.info("Web scraper cache cleared (no cache implemented)")
