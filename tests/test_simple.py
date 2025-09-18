"""Simple tests that call real APIs with minimal test data."""

import pytest
from dashbot.api import cse
from dashbot.api.ai import generate_topics, personalize_topics, get_pages_per_topic, generate_summary
from dashbot.api.cse import extract_article, GoogleCSE, search_google
import asyncio


def test_generate_topics():
    """Test AI topic generation with real OpenAI API."""
    # Simple test data - just a few pages
    pages = [
        GoogleCSE(
            url="https://www.bbc.com/news/science-environment-123456",
            title="Climate change: New study shows rising temperatures",
            snippet="Scientists report that global temperatures have increased significantly...",
            source="BBC News"
        ),
        GoogleCSE(
            url="https://www.reuters.com/business/energy/123456",
            title="Renewable energy investments reach record high",
            snippet="Global investments in renewable energy sources have reached unprecedented levels...",
            source="Reuters"
        )
    ]
    
    topics = generate_topics(pages)
    
    # Just check it returns something reasonable
    assert len(topics) > 0
    assert topics[0].topic is not None
    assert topics[0].importance >= 1
    assert topics[0].importance <= 10
    for topic in topics:
        print(f"Generated topic: {topic.topic} (importance: {topic.importance})")


def test_personalize_topics():
    """Test topic personalization."""
    # Simple test data
    topics = [
        ("Climate Change", 8, [0, 1]),
        ("Energy News", 6, [2]),
        ("Tech News", 4, [3, 4]),
        ("Sports", 2, [5]),
        ("Politics", 7, [6, 7]),
        ("Health", 3, [8])
    ]
    
    # Convert to Topic objects
    from dashbot.api.ai import Topic
    topic_objects = [Topic(topic, importance, pages) for topic, importance, pages in topics]
    
    personalized = personalize_topics(topic_objects)
    
    # Should return top 5 by importance
    assert len(personalized) == 5
    assert personalized[0].importance == 8  # Climate Change
    assert personalized[1].importance == 7  # Politics
    assert personalized[2].importance == 6  # Energy News
    print(f"Top topic: {personalized[0].topic} (importance: {personalized[0].importance})")


def test_get_pages_per_topic():
    """Test filtering pages by topic."""
    # Simple test data
    pages = [
        GoogleCSE("url1", "Climate Article 1", "snippet1", "2024-01-01", "source1"),
        GoogleCSE("url2", "Climate Article 2", "snippet2", "2024-01-02", "source2"), 
        GoogleCSE("url3", "Tech Article", "snippet3", "2024-01-03", "source3")
    ]
    
    from dashbot.api.ai import Topic
    topic = Topic("Climate Change", 8, [0, 1])  # Pages 0 and 1
    
    filtered_pages = get_pages_per_topic(pages, topic)
    
    assert len(filtered_pages) == 2
    assert filtered_pages[0].title == "Climate Article 1"
    assert filtered_pages[1].title == "Climate Article 2"
    print(f"Filtered {len(filtered_pages)} pages for topic: {topic.topic}")


def test_extract_article():
    """Test article extraction with real newspaper3k."""
    # Use a simple, reliable article URL
    page = GoogleCSE(
        url="https://www.br.de/nachrichten/deutschland-welt/krieg-in-israel-und-gaza-im-news-ticker-vom-15-bis-21-september,Uwqjbdh",  # Replace with a real BBC article URL
        title="Test Article",
        snippet="Test snippet",
        source="BR"
    )

    article = extract_article(page)
    assert article.content is not None
    assert len(article.content) > 0
    print(f"Extracted article content: {article.content}")


def test_generate_summary():
    """Test AI summary generation with real OpenAI API."""
    # Simple test context
    context = """
    Climate change is affecting global temperatures. Scientists report that 2023 was the hottest year on record.
    Renewable energy investments are increasing worldwide. Solar and wind power installations reached new highs.
    Governments are implementing new climate policies. The Paris Agreement targets are being reviewed.
    """
    
    summary = generate_summary(context)
    
    assert summary is not None
    assert len(summary) > 0
    print(f"Generated summary: {summary[:200]}...")


@pytest.mark.asyncio
async def test_search_google():
    """Test search google with real Google Custom Search API."""
    pages = await cse.search_google("climate change")
    assert len(pages) > 0
    print(f"Searched for 'climate change' and found {len(pages)} pages")
    for id, page in enumerate(pages):
        print(f"Page id: {id}")
        print(f"Title: {page.title}")
        print(f"Snippet: {page.snippet}")
        print(f"URL: {page.url}")
        print(f"Source: {page.source}")
        print("-"*50)

def test_extract_article1():
    article = cse.extract_article(GoogleCSE(
        url="https://www.climatechangeauthority.gov.au/latest-news", 
        title="Test Article",
        snippet="Test snippet",
        source="Test Source"
    ))
    assert article.content is not None
    assert len(article.content) > 0
    print(f"Extracted article content: {article.content}")
    print(f"Extracted article authors: {article.authors}")
    print(f"Extracted article source: {article.source}")
    print(f"Extracted article publish date: {article.publish_date}")
    print(f"Extracted article google cse: {article.google_cse}")

if __name__ == "__main__":
    # Run tests individually
    asyncio.run(test_search_google())
    test_generate_topics()
    test_personalize_topics() 
    test_get_pages_per_topic()
    test_extract_article()
    test_generate_summary()
    test_search_google()
