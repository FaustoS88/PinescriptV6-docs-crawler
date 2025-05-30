import asyncio
from typing import Set, List
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy, LLMExtractionStrategy
from bs4 import BeautifulSoup
import os
from datetime import datetime

class PineScriptDocsCrawler:
    def __init__(self):
        self.base_url = "https://www.tradingview.com/pine-script-docs"
        # Create output directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.output_dir = os.path.join(script_dir, "pinescript_docs")
        self.visited_urls: Set[str] = set()
        
        # Define the extraction schema for structure
        self.structure_schema = {
            "name": "PineScript Documentation",
            "baseSelector": "main",  # Main content area
            "fields": [
                {
                    "name": "title",
                    "selector": "h1",
                    "type": "text"
                },
                {
                    "name": "content",
                    "selector": "main > div",  # Main content excluding navigation
                    "type": "html"
                },
                {
                    "name": "navigation",
                    "selector": "nav",  # Left navigation menu
                    "type": "html"
                },
                {
                    "name": "toc",
                    "selector": "[aria-label='Table of contents']",  # Right-side TOC
                    "type": "html"
                }
            ]
        }
        
        # LLM strategy for processing content
        self.content_schema = {
            "title": str,
            "section": str,
            "content": str,
            "code_examples": List[str],
            "related_topics": List[str]
        }

    def normalize_url(self, url: str) -> str:
        """Convert relative URLs to absolute and clean them"""
        if not url:
            return ""
            
        # Remove anchor tags and query parameters
        url = url.split('#')[0].split('?')[0]
        
        # Skip external links and special protocols
        if url.startswith(('http', 'https')) and not url.startswith(self.base_url):
            return ""
        if url.startswith(('mailto:', 'tel:', 'javascript:')):
            return ""
            
        # Handle relative URLs
        if not url.startswith('http'):
            if url.startswith('/'):
                url = f"https://www.tradingview.com{url}"
            else:
                url = f"{self.base_url}/{url}"
                
        return url

    async def get_all_doc_urls(self) -> List[str]:
        """Extract all documentation URLs from the navigation menu"""
        urls = set()
        print("Starting to collect URLs...")
        
        # Start with main sections from left navigation
        browser_config = BrowserConfig(
            headless=True,
            extra_args=["--disable-gpu", "--disable-dev-shm-usage", "--no-sandbox"]
        )
        
        async with AsyncWebCrawler(config=browser_config) as crawler:
            result = await crawler.arun(url=f"{self.base_url}/welcome/")
            if result.success:
                print("Successfully accessed the main page")
                soup = BeautifulSoup(result.html, 'html.parser')
                
                # Find all navigation elements
                nav_elements = soup.find_all(['nav', 'div'], class_=['toc', 'sidebar'])
                for nav in nav_elements:
                    for link in nav.find_all('a'):
                        href = link.get('href')
                        if href:
                            full_url = self.normalize_url(href)
                            if full_url:
                                urls.add(full_url)
                                print(f"Found URL: {full_url}")
            else:
                print(f"Failed to access main page: {result.error_message}")
        
        urls_list = sorted(list(urls))
        print(f"Total URLs found: {len(urls_list)}")
        return urls_list

    async def crawl_docs(self, urls: List[str]):
        """Crawl documentation pages with both structure and content extraction"""
        os.makedirs(self.output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        print(f"Created output directory: {self.output_dir}")
        
        # Configure strategies
        structure_strategy = JsonCssExtractionStrategy(
            schema=self.structure_schema,
            verbose=True
        )
        
        browser_config = BrowserConfig(
            headless=True,
            extra_args=["--disable-gpu", "--disable-dev-shm-usage", "--no-sandbox"]
        )
        
        # Create files for saving results
        combined_path = f"{self.output_dir}/all_docs_{timestamp}.md"
        failed_path = f"{self.output_dir}/failed_urls_{timestamp}.txt"
        
        print("Starting crawling process...")
        
        async with AsyncWebCrawler(config=browser_config) as crawler:
            success = 0
            failed = 0
            
            with open(combined_path, "w", encoding="utf-8") as combined_file, \
                 open(failed_path, "w", encoding="utf-8") as failed_file:
                
                # Process in small batches
                batch_size = 3
                for i in range(0, len(urls), batch_size):
                    batch = urls[i:i + batch_size]
                    print(f"\nProcessing batch {i//batch_size + 1}/{(len(urls) + batch_size - 1)//batch_size}")
                    
                    for url in batch:
                        try:
                            print(f"Crawling: {url}")
                            result = await crawler.arun(
                                url=url,
                                extraction_strategy=structure_strategy
                            )
                            
                            if result.success:
                                # Save as individual file
                                page_name = url.rstrip('/').split('/')[-1] or 'index'
                                file_path = f"{self.output_dir}/{page_name}_{timestamp}.md"
                                
                                with open(file_path, "w", encoding="utf-8") as f:
                                    f.write(f"# {page_name}\n\n")
                                    f.write(f"Source: {url}\n\n")
                                    # Handle both string and MarkdownGenerationResult object
                                    if isinstance(result.markdown, str):
                                        content = result.markdown
                                    else:
                                        content = result.markdown.raw_markdown if result.markdown else ""
                                    f.write(content)
                                
                                # Add to combined file
                                combined_file.write(f"\n\n# {page_name}\n\n")
                                combined_file.write(f"Source: {url}\n\n")
                                # Handle both string and MarkdownGenerationResult object
                                if isinstance(result.markdown, str):
                                    content = result.markdown
                                else:
                                    content = result.markdown.raw_markdown if result.markdown else ""
                                combined_file.write(content)
                                combined_file.write("\n\n---\n\n")
                                
                                success += 1
                                print(f"Successfully saved: {page_name}")
                            else:
                                print(f"Failed to crawl {url}: {result.error_message}")
                                failed_file.write(f"{url}: {result.error_message}\n")
                                failed += 1
                                
                        except Exception as e:
                            print(f"Error processing {url}: {str(e)}")
                            failed_file.write(f"{url}: {str(e)}\n")
                            failed += 1
                    
                    # Rate limiting between batches
                    await asyncio.sleep(2)
        
        print(f"\nCrawling completed:")
        print(f"- Successfully crawled: {success} pages")
        print(f"- Failed: {failed} pages")
        print(f"\nOutputs saved to:")
        print(f"- Combined content: {combined_path}")
        print(f"- Failed URLs: {failed_path}")
        print(f"- Individual pages: {self.output_dir}/*.md")

    async def run(self):
        """Main execution method"""
        print("Starting PineScript documentation crawler...")
        urls = await self.get_all_doc_urls()
        if not urls:
            print("No documentation pages found!")
            return
            
        print(f"\nFound {len(urls)} documentation pages")
        await self.crawl_docs(urls)

async def main():
    crawler = PineScriptDocsCrawler()
    await crawler.run()

if __name__ == "__main__":
    asyncio.run(main())