import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

load_dotenv()

MYSQL_URL = os.getenv("MYSQL_URL", "mysql+asyncmy://root:password@localhost/jobplatform")

engine = create_async_engine(
    MYSQL_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False,
)

SessionLocal = async_sessionmaker(engine, class_=AsyncSession, autocommit=False, autoflush=False)
