#!/usr/bin/env python3
"""
Automated News Aggregator with LLM Integration
Fetches news from multiple sources and generates AI-powered summaries at scheduled intervals
"""

import requests
import json
import time
import schedule
from datetime import datetime
from openai import OpenAI
import logging
from typing import List, Dict, Optional
import os
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('news_aggregator.log'),
        logging.StreamHandler()
    ]
)

@dataclass
class NewsArticle:
    title: str
    description: str
    url: str
    published_at: str
    source: str

class NewsAggregator:
    def __init__(self):
        # API Keys - Set these as environment variables
        self.news_api_key = os.getenv('NEWS_API_KEY')  # Get from https://newsapi.org/
        self.openai_api_key = os.getenv('OPENAI_API_KEY')  # Get from https://openai.com/
        
        if not self.news_api_key:
            logging.warning("NEWS_API_KEY not found. Using mock data mode.")
        
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        # Initialize OpenAI client
        self.client = OpenAI(api_key=self.openai_api_key)
        
        # News API configuration
        self.news_base_url = "https://newsapi.org/v2"
        self.categories = ["business", "technology", "consumer goods"]
        
    def fetch_news_articles(self, limit: int = 20) -> List[NewsArticle]:
        """Fetch latest news articles from NewsAPI"""
        articles = []
        
        if not self.news_api_key:
            # Mock data for testing when API key is not available
            return self._get_mock_articles()
        
        try:
            for category in self.categories:
                url = f"{self.news_base_url}/top-headlines"
                params = {
                    'apiKey': self.news_api_key,
                    'category': category,
                    'language': 'en',
                    'pageSize': limit // len(self.categories)
                }
                
                response = requests.get(url, params=params, timeout=10)
                response.raise_for_status()
                
                data = response.json()
                
                for article in data.get('articles', []):
                    if article.get('title') and article.get('description'):
                        articles.append(NewsArticle(
                            title=article['title'],
                            description=article['description'],
                            url=article['url'],
                            published_at=article['publishedAt'],
                            source=article['source']['name']
                        ))
                        
                time.sleep(0.1)  # Rate limiting
                
        except requests.RequestException as e:
            logging.error(f"Error fetching news: {e}")
            return self._get_mock_articles()
        
        return articles[:limit]
    
    def _get_mock_articles(self) -> List[NewsArticle]:
        """Return mock articles for testing"""
        return [
            NewsArticle(
                title="Tech Giants Report Strong Q3 Earnings",
                description="Major technology companies exceeded expectations in their quarterly reports.",
                url="https://example.com/tech-earnings",
                published_at="2024-01-15T10:00:00Z",
                source="TechNews"
            ),
            NewsArticle(
                title="Global Markets Show Positive Momentum",
                description="Stock markets worldwide continue upward trend amid economic recovery.",
                url="https://example.com/markets",
                published_at="2024-01-15T09:30:00Z",
                source="FinanceDaily"
            ),
            # Add more mock articles as needed
        ]
    
    def generate_news_summary(self, articles: List[NewsArticle]) -> str:
        """Use OpenAI to generate top 10 news summary"""
        if not articles:
            return "No news articles available at this time."
        
        # Prepare articles text for the LLM
        articles_text = "\n\n".join([
            f"Title: {article.title}\n"
            f"Description: {article.description}\n"
            f"Source: {article.source}\n"
            f"Published: {article.published_at}"
            for article in articles
        ])
        
        prompt = f"""
        Based on the following news articles, create a concise "Top 10 News" summary. 
        Select the 10 most important and diverse stories, and present them in a clear, 
        numbered format with brief descriptions.
        
        News Articles:
        {articles_text}
        
        Format your response as:
        TOP 10 NEWS - {datetime.now().strftime("%B %d, %Y")}
        
        1. [Brief headline] - [Concise summary in 1-2 sentences]
        2. [Brief headline] - [Concise summary in 1-2 sentences]
        ...and so on
        
        Focus on the most newsworthy and impactful stories.
        """
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",  # You can change to "gpt-4" if you have access
                messages=[
                    {"role": "system", "content": "You are a professional news editor who creates concise, informative news summaries."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1500,
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logging.error(f"Error generating summary with OpenAI: {e}")
            return self._generate_fallback_summary(articles)
    
    def _generate_fallback_summary(self, articles: List[NewsArticle]) -> str:
        """Generate a simple fallback summary without LLM"""
        summary = f"TOP 10 NEWS - {datetime.now().strftime('%B %d, %Y')}\n\n"
        
        for i, article in enumerate(articles[:10], 1):
            summary += f"{i}. {article.title}\n"
            summary += f"   {article.description}\n"
            summary += f"   Source: {article.source}\n\n"
        
        return summary
    
    def save_summary(self, summary: str) -> None:
        """Save summary to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"news_summary_{timestamp}.txt"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(summary)
            
            logging.info(f"Summary saved to {filename}")
            
        except IOError as e:
            logging.error(f"Error saving summary: {e}")
    
    def run_news_update(self) -> None:
        """Main function to fetch news and generate summary"""
        logging.info("Starting news update...")
        
        # Fetch articles
        articles = self.fetch_news_articles()
        logging.info(f"Fetched {len(articles)} articles")
        
        # Generate summary
        summary = self.generate_news_summary(articles)
        
        # Display summary
        print("\n" + "="*60)
        print(summary)
        print("="*60 + "\n")
        
        # Save to file
        self.save_summary(summary)
        
        logging.info("News update completed")

def main():
    """Main function to set up scheduling and run the aggregator"""
    
    # Check for required environment variables
    if not os.getenv('OPENAI_API_KEY'):
        print("Error: Please set your OPENAI_API_KEY environment variable")
        print("You can get an API key from: https://openai.com/")
        return
    
    # Create aggregator instance
    aggregator = NewsAggregator()
    
    # Schedule news updates
    # Run every 4 hours
    schedule.every(12).hours.do(aggregator.run_news_update)
    
    # Run immediately on startup
    print("News Aggregator Starting...")
    print("Scheduling news updates every 4 hours")
    print("Press Ctrl+C to stop")
    
    # Run once immediately
    aggregator.run_news_update()
    
    # Keep the script running
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
            
    except KeyboardInterrupt:
        print("\nNews Aggregator stopped.")
        logging.info("News Aggregator stopped by user")

if __name__ == "__main__":
    main()