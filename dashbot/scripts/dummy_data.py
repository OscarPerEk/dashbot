from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from dashbot.scripts.database import DATABASE_URL, NewsFeed


dummy_news = [
    {
        "title": "AI beats humans at chess again",
        "content": "In a stunning match yesterday, the AI system X defeated world champion Y in three rounds. Experts say this marks a new era where AI can challenge even the best human minds in strategy games.",
        "source": "TechDaily",
        "score": 3,
    },
    {
        "title": "Local farmer wins national award",
        "content": "Farmer John Doe has been recognized nationally for his sustainable farming practices. His innovative techniques have increased crop yields while protecting local wildlife habitats.",
        "source": "CountryNews",
        "score": 1,
    },
    {
        "title": "New species of bird discovered in Amazon",
        "content": "Scientists have discovered a previously unknown bird species deep in the Amazon rainforest. The discovery highlights the rich biodiversity still unexplored in the region.",
        "source": "NatureToday",
        "score": 2,
    },
    {
        "title": "Stock market hits all-time high",
        "content": "The stock market surged today, reaching record levels across multiple indices. Analysts attribute the rise to strong corporate earnings and investor optimism.",
        "source": "FinanceWeekly",
        "score": 0,
    },
    {
        "title": "Breakthrough in renewable energy technology",
        "content": "Researchers have developed a new method to increase solar panel efficiency significantly. This innovation could reduce costs and accelerate the adoption of clean energy worldwide.",
        "source": "ScienceNow",
        "score": 3,
    },
]


def main():
    engine = create_engine(DATABASE_URL, echo=True)
    with Session(engine) as session:
        for item in dummy_news:
            feed = NewsFeed(
                title=item["title"],
                content=item["content"],
                source=item["source"],
                score=item["score"],
                created_at=datetime.now(),
            )
            session.add(feed)
        session.commit()


if __name__ == "__main__":
    main()
    print("Dummy news entries added successfully!")
