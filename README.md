# PineScript V6 Documentation Crawler

A Python-based tool for crawling and processing TradingView's Pine Script V6 documentation, built using the Crawl4Ai framework. This tool extracts, cleans, and organizes the documentation, making it easier to reference and analyze. Crawl4Ai provides the core framework for web crawling, data extraction, and asynchronous processing, making it possible.

## Features

### Crawling
- Automatically extracts documentation from TradingView's Pine Script V6 website using Crawl4Ai
- Efficiently handles navigation through documentation pages
- Supports batch processing with rate limiting
- Maintains a structured extraction schema for consistent results
- Saves individual pages and a combined documentation file

### Content Processing
- Cleans and formats documentation content
- Preserves PineScript code blocks with proper syntax highlighting
- Extracts and formats function documentation
- Removes unnecessary navigation elements and formatting
- Processes content into a clean, readable markdown format

### Output Organization
- Creates individual markdown files for each documentation page
- Generates a combined documentation file for easy reference
- Maintains a processed/ directory with enhanced content
- Tracks failed URLs and crawling statistics
- Preserves original source URLs and timestamps

## Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/FaustoS88/PinescriptV6-docs-crawler
   cd PinescriptV6-docs-crawler
   ```

2. Install required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

1.  **Crawling Documentation**:

    Run the crawler:
    ```bash
    python pinescriptV6docs.py
    ```
    This script will collect documentation URLs, download content, and save it to the `pinescript_docs` directory.

2.  **Processing Documentation**:

    To clean and organize the crawled content, run:
    ```bash
    python process_docs.py
    ```
    This script extracts code examples and function documentation, generating processed versions in the `processed/` subdirectory.

## Output Structure

```
pinescript_docs/
├── all_docs_{timestamp}.md     # Combined documentation
├── {page_name}_{timestamp}.md  # Individual pages
├── failed_urls_{timestamp}.txt # Failed crawl attempts
└── processed/                  # Enhanced content
    └── processed_{page_name}_{timestamp}.md
```

## Customization

The crawler and processor can be customized through their respective class initializations:

-   `PineScriptDocsCrawler`: Configures crawling behavior, batch size, and extraction schema.
-   `PineScriptDocsProcessor`: Customizes content processing and output formatting.

## License

This project is open source and available under the MIT License.

## Error Handling

-   Failed URLs are logged with error messages.
-   Batch processing ensures resilience to temporary failures.
-   Rate limiting helps avoid server overload.
