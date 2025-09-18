from dataclasses import dataclass
import os

from newspaper import Article
from googleapiclient.discovery import build
import httpx

from dashbot.config import logger


class GoogleCSEError(Exception):
    pass


class GoogleEnvError(Exception):
    pass


@dataclass(frozen=True)
class GoogleCSE:
    url: str
    title: str
    snippet: str
    source: str
    query: str


async def search_google(query: str) -> list[GoogleCSE]:
    # Get API credentials from environment variables
    google_api_key = os.getenv("GOOGLE_API_KEY")
    google_cse_id = os.getenv("GOOGLE_CSE_ID")

    if not google_api_key or not google_cse_id:
        raise GoogleEnvError("missing google api key or cse id")

    url = "https://customsearch.googleapis.com/customsearch/v1"
    params = {
        "q": query,
        "cx": google_cse_id,
        "key": google_api_key,
        "num": "10",
        "sort": "date",
        # "lr": "lang_de", # delete?
    }
    res = []
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, params=params)
        _ = resp.raise_for_status()
        r = resp.json()
        for item in r.get("items", []):
            res.append(
                GoogleCSE(
                    url=item.get("link"),
                    title=item.get("title"),
                    snippet=item.get("snippet"),
                    source=item.get("displayLink"),
                    query=query,
                )
            )
    return res



@dataclass(frozen=True)
class WebArticle:
    authors: list[str]
    content: str
    source: str
    publish_date: str | None
    google_cse: GoogleCSE


def extract_article(page: GoogleCSE) -> WebArticle:
    if not page.url:
        logger.warning("no url found for source: ", page.source)
        return WebArticle([], "", "", None, page)
    article = Article(page.url)
    article.download()
    article.parse()

    # Extract main content
    main_content = article.text
    authors = article.authors
    publish_date = article.publish_date

    return WebArticle(
        authors=authors,
        content=main_content,
        source=article.source_url if hasattr(article, "source_url") else page.url,
        publish_date=publish_date.isoformat() if publish_date else None,
        google_cse=page,
    )
