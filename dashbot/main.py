import asyncio
from collections.abc import Generator
from fastapi import FastAPI, Request, Form, Depends
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, Response
import base64
import boto3
from botocore.exceptions import ClientError

from typing import Any
import os
from googleapiclient.discovery import build
from newspaper import Article
# Database
from dashbot.scripts.database import SessionLocal, NewsFeed
import dashbot.api.cse as cse
import dashbot.api.ai as ai
from sqlalchemy.orm import Session
from dashbot.config import logger

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


@app.get("/image/{image_key}")
async def get_s3_image(image_key: str):
    """
    Fetch image from S3 bucket and return as base64 data URL
    """
    try:
        # Initialize S3 client
        s3_client = boto3.client('s3')
        
        # Fetch the image from S3
        bucket_name = "website-dashbot"
        object_key = f"news-images/{image_key}"
        
        logger.info(f"Attempting to fetch image from S3: bucket={bucket_name}, key={object_key}")
        
        response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
        image_data = response['Body'].read()
        
        logger.info(f"Successfully fetched image: {len(image_data)} bytes")
        
        # Determine content type based on file extension
        content_type = "image/jpeg"  # default
        if image_key.lower().endswith('.png'):
            content_type = "image/png"
        elif image_key.lower().endswith('.gif'):
            content_type = "image/gif"
        elif image_key.lower().endswith('.webp'):
            content_type = "image/webp"
        
        logger.info(f"Returning image as {content_type}")
        return Response(content=image_data, media_type=content_type)
        
    except ClientError as e:
        logger.error(f"Error fetching image from S3: {e}")
        logger.error(f"Failed to fetch: bucket={bucket_name}, key={object_key}")
        # Return a placeholder image or error
        return Response(content="data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNTAiIGhlaWdodD0iNTAiIHZpZXdCb3g9IjAgMCA1MCA1MCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHJlY3Qgd2lkdGg9IjUwIiBoZWlnaHQ9IjUwIiBmaWxsPSIjRjNGNEY2Ii8+CjxwYXRoIGQ9Ik0yNSAyNUMzMC41MjI4IDI1IDM1IDIwLjUyMjggMzUgMTVDMzUgOS40NzcxNSAzMC41MjI4IDUgMjUgNUMxOS40NzcxIDUgMTUgOS40NzcxNSAxNSAxNUMxNSAyMC41MjI4IDE5LjQ3NzEgMjUgMjUgMjVaIiBmaWxsPSIjOUNBM0FGIi8+CjxwYXRoIGQ9Ik0yNSAzMEMyNy43NjE0IDMwIDMwIDI3Ljc2MTQgMzAgMjVDMzAgMjIuMjM4NiAyNy43NjE0IDIwIDI1IDIwQzIyLjIzODYgMjAgMjAgMjIuMjM4NiAyMCAyNUMyMCAyNy43NjE0IDIyLjIzODYgMzAgMjUgMzBaIiBmaWxsPSIjNjM2NkY3Ii8+Cjwvc3ZnPgo=", media_type="text/plain")
    except Exception as e:
        logger.error(f"Unexpected error fetching image: {e}")
        logger.error(f"Failed to fetch: bucket={bucket_name}, key={object_key}")
        return Response(content="data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNTAiIGhlaWdodD0iNTAiIHZpZXdCb3g9IjAgMCA1MCA1MCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHJlY3Qgd2lkdGg9IjUwIiBoZWlnaHQ9IjUwIiBmaWxsPSIjRjNGNEY2Ii8+CjxwYXRoIGQ9Ik0yNSAyNUMzMC41MjI4IDI1IDM1IDIwLjUyMjggMzUgMTVDMzUgOS40NzcxNSAzMC41MjI4IDUgMjUgNUMxOS40NzcxIDUgMTUgOS40NzcxNSAxNSAxNUMxNSAyMC41MjI4IDE5LjQ3NzEgMjUgMjUgMjVaIiBmaWxsPSIjOUNBM0FGIi8+CjxwYXRoIGQ9Ik0yNSAzMEMyNy43NjE0IDMwIDMwIDI3Ljc2MTQgMzAgMjVDMzAgMjIuMjM4NiAyNy43NjE0IDIwIDI1IDIwQzIyLjIzODYgMjAgMjAgMjIuMjM4NiAyMCAyNUMyMCAyNy43NjE0IDIyLjIzODYgMzAgMjUgMzBaIiBmaWxsPSIjNjM2NkY3Ii8+Cjwvc3ZnPgo=", media_type="text/plain")


BAVARIAN_PIC = "bavarian_landscape_20250918_210807.png"
HACKER_PIC = "hacker_20250918_212113.png"
TENNIS_PIC = "tennis_20250918_212632.png"
STARTUP_PIC = "startup_20250918_213550.png"
BOOKS_PIC = "books_20250918_215804.png"
BODYBUILDING_PIC = "harry-potter-ai-video.png"
CLIMATE_PIC = "climate_20250918_223129.png"


# Search for German news
# in the future this should be set on the website by the client
SEARCH_QUERIES = {
    # "deutsche nachrichten heute": BAVARIAN_PIC,
    # "climate change news": CLIMATE_PIC,
    # "globe aufwärmung nachrichten": CLIMATE_PIC,
    
    # "climate change news": CLIMATE_PIC,
    # "globe aufwärmung nachrichten": CLIMATE_PIC,
    # "klimatförändring nyheter": CLIMATE_PIC,
    # "energy news": CLIMATE_PIC,
    # "energy news in sweden": CLIMATE_PIC,
    # "energy news in germany": CLIMATE_PIC,
    # "hacker news": HACKER_PIC,
    "software development news": HACKER_PIC,
    # "ai news": HACKER_PIC,
    # "german news": BAVARIAN_PIC,
    # "deutschland aktuell": BAVARIAN_PIC,
    # "tennis news": TENNIS_PIC,
    # "upcoming tennis tournaments news": TENNIS_PIC,
    # "best tennis players news": TENNIS_PIC,
    # "htmx news": HACKER_PIC,
    # "python news": HACKER_PIC,
    # "tailwindcss and daisyui news": HACKER_PIC,
    # "ai python tools and libraries news": HACKER_PIC,
    # "startups in europe news": STARTUP_PIC,
    # "startups in germany news": STARTUP_PIC,
    # "startups in sweden news": STARTUP_PIC,
    # "startups in munich news": STARTUP_PIC,
    # "top bestselling books today": BOOKS_PIC,
    # "bestselling books today": BOOKS_PIC,
    # "best new sci-fi and fantasy books": BOOKS_PIC,
    # "Bestseller Bücher in Deutschland": BOOKS_PIC,
    # "Health science news": BODYBUILDING_PIC,
    # "Diet science news": BOOKS_PIC,
    # "Muscle building science news": BODYBUILDING_PIC,
}


@app.post("/scrape-news")
async def scrape_news() -> JSONResponse:
    """
    Endpoint to scrape German news using Google Custom Search API and newspaper3k.
    This endpoint will be triggered daily via AWS EventBridge.
    Save personalized news to db.

    1. Search with CSE -> articles
    2. AI filter -> return groups ids of articles per topic
    3. AI research facts and counter arguments -> more articles + ids per topic
    4. Get full context (articles per topic), let ai write summary -> save to db
    """
    pages_nested = await asyncio.gather(*(cse.search_google(q) for q in SEARCH_QUERIES.keys()))
    pages = [p for sub in pages_nested for p in (sub or [])]
    topics = ai.generate_topics(pages)
    topics = ai.personalize_topics(topics)
    for topic in topics:
        p = ai.get_pages_per_topic(pages, topic)
        context = ""
        source = ""
        query = BAVARIAN_PIC
        if len(topic.pages) > 0:
            query = pages[topic.pages[0]].query
        for page in p:
            source += page.source + "\n"
            try:
                article = cse.extract_article(page)
            except Exception as e:
                logger.error(f"Error extracting article: {e}\n Page: {page}")
                continue
            context += page.title + "\n" + article.content
        if not context:
            logger.error(f"No context found for topic: {topic.topic}")
            continue
        summary = ai.generate_summary(context)
        ai.add_news_to_database(summary, source, topic.topic, SEARCH_QUERIES[query])
    return JSONResponse(status_code=200, content={"message": "News scraped successfully"})

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

So we now got the news from the google cse. Thats already pretty good.
And also we extract the info from the websites. So we do have the whole
content already.
"""
if __name__ == "__main__":
    asyncio.run(scrape_news())