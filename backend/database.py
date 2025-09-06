# backend/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# DATABASE_URL = "sqlite:///./app.db"  <- OLD
# NEW: PostgreSQL connection URL. Assumes a DB named 'flowcfd' exists.
# Replace with your actual database credentials and host.
DATABASE_URL = "postgresql://user:password@localhost/flowcfd"

engine = create_engine(
    DATABASE_URL, future=True, pool_pre_ping=True
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)
Base = declarative_base()
