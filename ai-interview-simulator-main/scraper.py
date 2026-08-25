import os
from dotenv import load_dotenv
from firecrawl import FirecrawlApp

# Explicitly load the .env file from the current directory
load_dotenv()

# Debug: Let's see if Python can read your key
api_key = os.getenv("FIRECRAWL_API_KEY")
print(f"Debug: API Key found in environment: {api_key is not None}")

if not api_key:
    raise ValueError(
        "Could not read FIRECRAWL_API_KEY from the .env file. "
        "Please verify that the .env file is saved in the same folder as this script."
    )

# Pass the API key explicitly to the Firecrawl application
app = FirecrawlApp(api_key=api_key)

def scrape_interview_data(url: str):
    """
    Takes a URL (like a Reddit thread or blog post), scrapes it, and returns clean Markdown text.
    """
    print(f"Scraping data from: {url}...")
    try:
        # Scrape the URL
        scraped_data = app.scrape_url(url)
        print("Scrape successful!")
        
        # Safely extract markdown whether it is a dictionary or a new Document object
        if isinstance(scraped_data, dict):
            return scraped_data.get('markdown', 'No markdown found.')
        else:
            return getattr(scraped_data, 'markdown', str(scraped_data))
        
    except Exception as e:
        print(f"Failed to scrape. Error: {e}")
        return None

if __name__ == "__main__":
    # Using the Levels.fyi link that is friendly to scraping
    test_url = "https://www.levels.fyi/blog/amazon-leadership-principles.html"
    print("Starting test run...")
    result = scrape_interview_data(test_url)
    
    if result:
        print("\n--- Snippet of Extracted Text ---\n")
        print(result[:800])