"""SQLite database helpers for the Book Collection API."""

import os
import sqlite3

from flask import g

DB_PATH = os.environ.get("BOOKS_DB_PATH", "books.db")


def get_db():
    """Return a per-request SQLite connection (cached on flask.g)."""
    if "db" not in g:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        g.db = conn
    return g.db


def init_db(path=None):
    """Create the books table if it does not already exist."""
    target = path or DB_PATH
    conn = sqlite3.connect(target)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS books (
                id    INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT    NOT NULL,
                author TEXT   NOT NULL,
                year  INTEGER,
                isbn  TEXT
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def close_db(exc=None):
    """Close the per-request DB connection (registered as teardown)."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def reset_db(path=None):
    """Drop and recreate the books table. Used by tests."""
    target = path or DB_PATH
    conn = sqlite3.connect(target)
    try:
        conn.execute("DROP TABLE IF EXISTS books")
        conn.execute(
            """
            CREATE TABLE books (
                id    INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT    NOT NULL,
                author TEXT   NOT NULL,
                year  INTEGER,
                isbn  TEXT
            )
            """
        )
        conn.commit()
    finally:
        conn.close()
