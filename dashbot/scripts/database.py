import datetime
import os
from sqlalchemy import DateTime, create_engine, Integer, String, TIMESTAMP, func, ARRAY
from sqlalchemy.ext.declarative import declarative_base
from dotenv import load_dotenv
from sqlalchemy.orm import Mapped, mapped_column, sessionmaker, Session


_ = load_dotenv()
DB_HOST = os.environ.get("DB_HOST")
DB_PORT = os.environ.get("DB_PORT", 5432)
DB_NAME = os.environ.get("DB_NAME")
DB_USER = os.environ.get("DB_USER")
DB_PASSWORD = os.environ.get("DB_PASSWORD")


# Safety check
required_vars = ["DB_HOST", "DB_NAME", "DB_USER", "DB_PASSWORD"]
missing = [var for var in required_vars if not os.environ.get(var)]
if missing:
    raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

DATABASE_URL = (
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)


engine = create_engine(DATABASE_URL)
Base = declarative_base()

# Session factory for runtime queries
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class NewsFeed(Base):
    __tablename__ = "news_feed"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String)
    content: Mapped[str] = mapped_column(String)
    source: Mapped[str] = mapped_column(String)
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    feedback: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(TIMESTAMP, server_default=func.now())
    deleted_at: Mapped[DateTime | None] = mapped_column(TIMESTAMP, nullable=True)


class ContextRules(Base):
    __tablename__ = "context_rules"
    id: Mapped[int] = mapped_column(primary_key=True)
    importance: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rule: Mapped[str] = mapped_column(String)
    news_feed_ids: Mapped[list[int] | None] = mapped_column(
        ARRAY(Integer),
        nullable=True,
    )
    created_at: Mapped[DateTime] = mapped_column(TIMESTAMP, server_default=func.now())
    deleted_at: Mapped[DateTime | None] = mapped_column(TIMESTAMP, nullable=True)


# ---- CREATE TABLE ----
if __name__ == "__main__":
    # Drop all tables
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    print("tables created")


"""
Lets start with the news dashboard.
So we wanna let the ai search continously, with a lambda job
for personalized top news and then save those to the database.
We wanna score them


Fields NewsFeed:
- news
- date
- source
- score
- feedback
- deleted (only display none deleted)

Lets have a second database where the ai can deal with the feedback.

Fields ContextRules:
- importance
- rule
- date
- deleted

So the core of this website is the news feed. Where we display the
results of the database. Ranked ordered from the date i guess.

So the databases are created. Next lets either create the backend
logic or lets make some fake data for now and make the front end
look reasonable.

"""
