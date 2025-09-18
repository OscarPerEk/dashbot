import os
import json
from typing import Any, cast
from dataclasses import dataclass
from openai import OpenAI
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from dashbot.api import cse
from dashbot.config import logger
from dashbot.scripts.database import NewsFeed, DATABASE_URL


@dataclass(frozen=True)
class Topic:
    topic: str
    importance: int
    pages: list[int]


def generate_topics(pages: list[cse.GoogleCSE]) -> list[Topic]:
    """
    Call ChatGpt API to figure out the topics based on the title
    and snippet of each page in pages. Marshall the result into
    a list of Topic.
    """
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise ValueError("OPENAI_API_KEY is not set")

    if not pages:
        return []

    page_summaries = [
        {"title": p.title, "snippet": p.snippet, "id": id} for id, p in enumerate(pages)
    ]

    # Ask the model for a structured list of topics with importance 1-10
    client = OpenAI(api_key=openai_api_key)

    messages = [
        {
            "role": "system",
            "content": (
                "You cluster pages into concise news topics and rate each topic by importance. "
                "Return strictly a JSON array."
            ),
        },
        {
            "role": "user",
            "content": (
                "Given these pages (title, snippet, id), group them into topics.\n"
                "Rules:\n"
                "- topic: a few words to one short sentence (e.g., 'american politics', 'ukraine war').\n"
                "- importance: integer 1-10; 10 = major breaking news (e.g., head of state shot),\n"
                " - ids: list of ids of the pages that belong to the topic\n"
                "  7-9 = significant global/national developments, 4-6 = notable but routine updates,\n"
                "  1-3 = minor or niche items.\n"
                "- Consider recency and urgency from wording (e.g., 'breaking', 'shooting', 'earthquake', 'resignation').\n"
                "- Merge duplicates; avoid overly broad/overly granular labels.\n"
                "Return EXACTLY this JSON shape and nothing else: \n"
                '[{"topic": "text", "importance": 1, "ids": [1, 2, 3]}]\n\n'
                f"pages: {json.dumps(page_summaries, ensure_ascii=False)}"
            ),
        },
    ]

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=cast(Any, messages),  # type: ignore[arg-type]
    )
    content = response.choices[0].message.content or "[]"
    print("inside generate_topics")
    print(f"Content: {content}")
    if not content:
        logger.error("no content found when generating topics")
        return []
    topics_payload: list[dict[str, Any]] = json.loads(content)

    result: list[Topic] = []
    for item in topics_payload:
        try:
            topic_str = str(item.get("topic", "")).strip()
            importance_val = int(item.get("importance", 1))
            if not topic_str:
                continue
            if importance_val < 1:
                importance_val = 1
            if importance_val > 10:
                importance_val = 10
            ids_val = [int(id) for id in item.get("ids", [])]
            result.append(Topic(topic_str, importance_val, ids_val))
        except Exception:
            logger.error("failed to parse response when generating topics")
            continue

    return result


def personalize_topics(topics: list[Topic]) -> list[Topic]:
    """Return top 5 topics by importance"""
    return sorted(topics, key=lambda x: x.importance, reverse=True)[:5]


def get_pages_per_topic(
    pages: list[cse.GoogleCSE], topic: Topic
) -> list[cse.GoogleCSE]:
    """Filter pages to only include those that belong to the topics"""
    result = []
    for id, page in enumerate(pages):
        if id in topic.pages:
            result.append(page)
    return result


def generate_summary(context: str) -> str:
    openai_api_key = os.getenv("OPENAI_API_KEY")
    client = OpenAI(api_key=openai_api_key)
    if not openai_api_key:
        raise ValueError("OPENAI_API_KEY is not set")

    messages = [
        {
            "role": "system",
            "content": (
                "You are a sceptical, open minded journalist and scientist.\n"
                "Return a html string with the summary. Nothing else than the html string.\n"
                "Please use daisyui and tailwindcss to style your answer.\n"
                "Please use headers and paragraphs to structure your answer.\n"
                "Usse h2 class=text-2xl to make headers and use spacing between headers and paragraphs.\n"
                'Your answer will end up inside <div class="list-col-wrap text-xs">'
            ),
        },
        {
            "role": "user",
            "content": (
                "Given the following news stories.\n"
                "Return a consice summary that captures the most important news. \n"
                "Use easy, colourful, fun language and write in English. \n"
                "List the main points, facts and sympathies. \n"
                "Add arguments for and against the stories. If someone would disagree, what would their strongest arguments be. \n"
                "Be facts oriented and try to think of the higher picture. \n"
                "Give a bit of background information and a timeline. \n"
                "List some important people involved and give a short summary on them and a timeline. \n"
                "Feel free to change the structure. Most important is to make a fun and engaging summary. \n"
                f"Articles: {context}"
            ),
        },
    ]

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=cast(Any, messages),  # type: ignore[arg-type]
    )
    r = response.choices[0].message.content or ""
    r.replace("```html", "").replace("```", "")
    return r


def add_news_to_database(summary: str, source: str, title: str, image: str):
    """Create a NewsFeed item and add it to the database"""
    news_feed = NewsFeed(
        title=title,
        content=summary,
        source=source,
        score=0,
        image=image,
    )
    engine = create_engine(DATABASE_URL, echo=True)
    with Session(engine) as session:
        session.add(news_feed)
        session.commit()
