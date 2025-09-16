from collections.abc import Generator
from fastapi import FastAPI, Request, Form, Depends
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse

from typing import Any
import os
from googleapiclient.discovery import build
from newspaper import Article
import logging

# Database
from .scripts.database import SessionLocal, NewsFeed
from sqlalchemy.orm import Session


app = FastAPI()
app.mount("/static", StaticFiles(directory="dashbot/static"), name="static")
templates = Jinja2Templates(directory="dashbot/templates")


@app.get("/")
async def home(request: Request):
    context = {"request": request}
    return templates.TemplateResponse("base.html", context)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/news", response_class=HTMLResponse)
async def news(request: Request):
    # Render shell; content will be loaded via HTMX
    context = {"request": request}
    return templates.TemplateResponse("news-v2.html", context)


@app.get("/hx/news-feed", response_class=HTMLResponse)
async def hx_news_feed(request: Request, db: Session = Depends(get_db)):
    # Query recent items (not deleted), newest first
    rows = (
        db.query(NewsFeed)
        .filter(NewsFeed.deleted_at.is_(None))
        .order_by(NewsFeed.created_at.desc())
        .limit(50)
        .all()
    )
    # Pass rows as items; template will handle rendering
    context = {"request": request, "items": rows}
    return templates.TemplateResponse("partials/news_items.html", context)


@app.post("/toggle-like/{item_id}", response_class=HTMLResponse)
async def toggle_like(
    request: Request,
    item_id: int,
    is_liked: bool = Form(False),
    db: Session = Depends(get_db),
):
    # Flip the state; here you'd persist to DB and return the new state
    print("inside toggle like post func")
    item = db.query(NewsFeed).filter(NewsFeed.id == item_id).first()
    if not item:
        return JSONResponse(status_code=404, content={"error": "Item not found"})
    item.is_liked = not is_liked
    db.commit()
    db.refresh(item)

    return templates.TemplateResponse(
        "partials/like_button.html",
        {"request": request, "item": {"id": item_id, "is_liked": item.is_liked}},
    )


@app.post("/scrape-news")
async def scrape_german_news():
    """
    Endpoint to scrape German news using Google Custom Search API and newspaper3k.
    This endpoint will be triggered daily via AWS EventBridge.
    """
    try:
        # Get API credentials from environment variables
        google_api_key = os.getenv("GOOGLE_API_KEY")
        google_cse_id = os.getenv("GOOGLE_CSE_ID")
        
        if not google_api_key or not google_cse_id:
            return JSONResponse(
                status_code=500,
                content={"error": "Google API credentials not configured"}
            )
        
        # Initialize Google Custom Search API
        service = build("customsearch", "v1", developerKey=google_api_key)
        
        # Search for German news
        search_queries = [
            "deutsche nachrichten heute",
            # "german news heute",
            # "deutschland aktuell",
            # "tagesschau",
            # "spiegel online"
        ]
        
        scraped_articles = []
        
        for query in search_queries:
            try:
                # Perform search
                result = service.cse().list(
                    q=query,
                    cx=google_cse_id,
                    num=5,  # Limit to 5 results per query
                    lr="lang_de",  # Restrict to German language
                    sort="date"  # Sort by date
                ).execute()
                
                # Process each search result
                for item in result.get("items", []):
                    url = item.get("link")
                    title = item.get("title")
                    snippet = item.get("snippet")
                    
                    if url:
                        try:
                            # Use newspaper3k to extract article content
                            article = Article(url)
                            article.download()
                            article.parse()
                            
                            # Extract main content
                            main_content = article.text
                            authors = article.authors
                            publish_date = article.publish_date
                            
                            article_data = {
                                "url": url,
                                "title": title,
                                "snippet": snippet,
                                "main_content": main_content[:1000] if main_content else "",  # Limit content length
                                "authors": authors,
                                "publish_date": publish_date.isoformat() if publish_date else None,
                                "source": article.source_url if hasattr(article, 'source_url') else url
                            }
                            
                            scraped_articles.append(article_data)
                            
                            # Print results as requested
                            print(f"Scraped article: {title}")
                            print(f"URL: {url}")
                            print(f"Content preview: {main_content[:200]}...")
                            print("-" * 50)
                            
                        except Exception as e:
                            logging.error(f"Error processing article {url}: {str(e)}")
                            continue
                            
            except Exception as e:
                logging.error(f"Error searching for query '{query}': {str(e)}")
                continue
        
        return JSONResponse(content={
            "message": f"Successfully scraped {len(scraped_articles)} German news articles",
            "articles": scraped_articles
        })
        
    except Exception as e:
        logging.error(f"Error in scrape_german_news: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to scrape news: {str(e)}"}
        )


"""
So now the frontend is working. Like we have a feed and everything.
The feed is just a list of those articles.
Next, first of all the current articles are hard coded.
Lets instead fetch them from the database. done!

lets make the pictures be ai generated as well.

After that we would have to solve the actual problem of getting the 
news articles. This we wanna serverless, directly in cloud via
a lambda job. Have a script run twice a day to scrape for news and 
put in the database.

Alright so how do i actually fetch then. Like that should
probably also be a htmx?
"""

