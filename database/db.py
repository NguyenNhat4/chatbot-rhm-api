# db.py
import os
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.automap import automap_base

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

metadata = MetaData(schema="public")
metadata.reflect(bind=engine)

Base = automap_base(metadata=metadata)
Base.prepare()

# Access ORM classes
Users = Base.classes.users


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
