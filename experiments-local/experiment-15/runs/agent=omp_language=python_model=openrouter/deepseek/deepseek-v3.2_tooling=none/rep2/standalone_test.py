#!/usr/bin/env python3
"""
Standalone test that doesn't import anything from main.py
"""
import sys
from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, Column, Integer, String, select
from sqlalchemy.orm import declarative_base, Session, sessionmaker
from pydantic import BaseModel, Field
from typing import Optional, List

print("Creating in-memory database...")
engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
print(f"Engine created: {engine}")

Base = declarative_base()

class BookDB(Base):
    __tablename__ = "books"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    author = Column(String, nullable=False)
    year = Column(Integer, nullable=True)
    isbn = Column(String, nullable=True)

print("Creating tables...")
Base.metadata.create_all(bind=engine)
print("Tables created")

# Verify tables exist
with engine.connect() as conn:
    result = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='books'")
    tables = result.fetchall()
    print(f"Tables in database: {tables}")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Create app
app = FastAPI()

@app.get("/test")
def test():
    return {"message": "test"}

client = TestClient(app)

print("\nTesting endpoint...")
response = client.get("/test")
print(f"Response: {response.status_code}, {response.json()}")

print("\nTest complete")