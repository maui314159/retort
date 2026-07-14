from fastapi import FastAPI
from app.routers import books, health
from app.database import engine, Base
import os

def create_tables():
    Base.metadata.create_all(bind=engine)

app = FastAPI(title="Book Collection API", version="1.0.0")

app.include_router(books.router, prefix="/books", tags=["books"])
app.include_router(health.router, prefix="/health", tags=["health"])

@app.get("/")
def read_root():
    return {"message": "Book Collection API"}

# Create tables on startup if not in testing mode
if os.getenv("TESTING") != "1":
    create_tables()