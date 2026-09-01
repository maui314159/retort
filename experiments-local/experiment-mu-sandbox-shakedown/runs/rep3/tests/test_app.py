"""Unit and integration tests for the Books API.

Runs with pytest (pytest -v) or the stdlib runner (python -m unittest discover).
"""

import http.client
import json
import os
import shutil
import tempfile
import threading
import unittest

from app import BookStore, ValidationError, create_server, validate_book_payload


# --------------------------------------------------------------------- #
# Unit tests: storage layer
# --------------------------------------------------------------------- #
class BookStoreTests(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(prefix="books_store_", suffix=".db")
        os.close(fd)
        self.store = BookStore(self.db_path)
        self.store.init_schema()

    def tearDown(self):
        os.remove(self.db_path)

    def test_create_and_get_roundtrip(self):
        book = self.store.create(
            {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441172719"}
        )
        self.assertEqual(self.store.get(book["id"]), book)
        self.assertEqual(book["title"], "Dune")

    def test_get_missing_book_returns_none(self):
        self.assertIsNone(self.store.get(999))

    def test_list_filters_by_author(self):
        self.store.create({"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": None})
        self.store.create({"title": "1984", "author": "George Orwell", "year": 1949, "isbn": None})
        self.assertEqual(len(self.store.list()), 2)
        books = self.store.list(author="George Orwell")
        self.assertEqual([b["title"] for b in books], ["1984"])

    def test_update_changes_fields(self):
        book = self.store.create({"title": "Old", "author": "A", "year": 2000, "isbn": "x"})
        updated = self.store.update(
            book["id"], {"title": "New", "author": "B", "year": 2001, "isbn": "y"}
        )
        self.assertEqual(updated["title"], "New")
        self.assertEqual(updated["year"], 2001)
        self.assertEqual(self.store.get(book["id"])["title"], "New")

    def test_update_missing_book_returns_none(self):
        fields = {"title": "T", "author": "A", "year": None, "isbn": None}
        self.assertIsNone(self.store.update(1234, fields))

    def test_delete_removes_book(self):
        book = self.store.create({"title": "T", "author": "A", "year": None, "isbn": None})
        self.assertTrue(self.store.delete(book["id"]))
        self.assertIsNone(self.store.get(book["id"]))
        self.assertFalse(self.store.delete(book["id"]))


# --------------------------------------------------------------------- #
# Unit tests: payload validation
# --------------------------------------------------------------------- #
class ValidateBookPayloadTests(unittest.TestCase):
    def test_valid_payload_is_cleaned(self):
        fields = validate_book_payload(
            {"title": "  Dune ", "author": "Frank Herbert", "year": 1965, "isbn": "123", "extra": "ignored"}
        )
        self.assertEqual(fields["title"], "Dune")
        self.assertEqual(fields["year"], 1965)
        self.assertEqual(set(fields), {"title", "author", "year", "isbn"})

    def test_optional_fields_default_to_none(self):
        self.assertEqual(
            validate_book_payload({"title": "T", "author": "A"}),
            {"title": "T", "author": "A", "year": None, "isbn": None},
        )

    def test_missing_title_raises(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_book_payload({"author": "A"})
        self.assertTrue(any("title" in message for message in ctx.exception.errors))

    def test_blank_title_raises(self):
        with self.assertRaises(ValidationError):
            validate_book_payload({"title": "   ", "author": "A"})

    def test_missing_author_raises(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_book_payload({"title": "T"})
        self.assertTrue(any("author" in message for message in ctx.exception.errors))

    def test_year_must_be_integer(self):
        with self.assertRaises(ValidationError):
            validate_book_payload({"title": "T", "author": "A", "year": "1965"})

    def test_non_object_payload_raises(self):
        with self.assertRaises(ValidationError):
            validate_book_payload(["not", "a", "dict"])


# --------------------------------------------------------------------- #
# Integration tests: full HTTP API
# --------------------------------------------------------------------- #
class APIIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmpdir = tempfile.mkdtemp(prefix="books_api_")
        db_path = os.path.join(cls.tmpdir, "books.db")
        cls.server = create_server("127.0.0.1", 0, db_path)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)
        shutil.rmtree(cls.tmpdir, ignore_errors=True)

    def request(self, method, path, payload=None, raw_body=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        headers = {}
        body = None
        if payload is not None:
            body = json.dumps(payload)
            headers["Content-Type"] = "application/json"
        elif raw_body is not None:
            body = raw_body
        conn.request(method, path, body=body, headers=headers)
        response = conn.getresponse()
        raw = response.read()
        status = response.status
        resp_headers = {k.lower(): v for k, v in response.getheaders()}
        conn.close()
        data = json.loads(raw) if raw else None
        return status, data, resp_headers

    def create_book(self, **overrides):
        payload = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": None}
        payload.update(overrides)
        status, data, _ = self.request("POST", "/books", payload)
        self.assertEqual(status, 201)
        return data

    def test_health(self):
        status, data, _ = self.request("GET", "/health")
        self.assertEqual(status, 200)
        self.assertEqual(data, {"status": "ok"})

    def test_create_book_returns_201_and_location(self):
        status, data, headers = self.request(
            "POST",
            "/books",
            {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441172719"},
        )
        self.assertEqual(status, 201)
        self.assertIsInstance(data["id"], int)
        self.assertEqual(data["title"], "Dune")
        self.assertEqual(headers.get("location"), f"/books/{data['id']}")

    def test_create_book_requires_title_and_author(self):
        status, data, _ = self.request("POST", "/books", {"title": "No Author"})
        self.assertEqual(status, 400)
        self.assertIn("errors", data)
        status, _, _ = self.request("POST", "/books", {"author": "No Title"})
        self.assertEqual(status, 400)

    def test_create_book_rejects_invalid_json(self):
        status, _, _ = self.request("POST", "/books", raw_body="{not json")
        self.assertEqual(status, 400)

    def test_create_book_rejects_empty_body(self):
        status, _, _ = self.request("POST", "/books")
        self.assertEqual(status, 400)

    def test_get_book_by_id(self):
        created = self.create_book(title="1984", author="George Orwell", year=1949)
        status, data, _ = self.request("GET", f"/books/{created['id']}")
        self.assertEqual(status, 200)
        self.assertEqual(data["author"], "George Orwell")
        self.assertEqual(data["year"], 1949)

    def test_get_missing_book_returns_404(self):
        status, _, _ = self.request("GET", "/books/424242")
        self.assertEqual(status, 404)

    def test_list_books_and_author_filter(self):
        self.create_book(title="Dune", author="Frank Herbert")
        self.create_book(title="Animal Farm", author="George Orwell")

        status, books, _ = self.request("GET", "/books")
        self.assertEqual(status, 200)
        self.assertGreaterEqual(len(books), 2)
        self.assertTrue(all({"id", "title", "author", "year", "isbn"} <= set(b) for b in books))

        status, filtered, _ = self.request("GET", "/books?author=George%20Orwell")
        self.assertEqual(status, 200)
        titles = [b["title"] for b in filtered]
        self.assertIn("Animal Farm", titles)
        self.assertNotIn("Dune", titles)
        self.assertTrue(all(b["author"] == "George Orwell" for b in filtered))

    def test_update_book(self):
        created = self.create_book(title="Old Title", author="A", year=2000)
        status, updated, _ = self.request(
            "PUT",
            f"/books/{created['id']}",
            {"title": "New Title", "author": "B", "year": 2001, "isbn": "isbn-1"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(updated["title"], "New Title")
        status, fetched, _ = self.request("GET", f"/books/{created['id']}")
        self.assertEqual(fetched["title"], "New Title")
        self.assertEqual(fetched["isbn"], "isbn-1")

    def test_update_missing_book_returns_404(self):
        status, _, _ = self.request("PUT", "/books/424242", {"title": "T", "author": "A"})
        self.assertEqual(status, 404)

    def test_update_book_validates_payload(self):
        created = self.create_book(title="T", author="A")
        status, _, _ = self.request("PUT", f"/books/{created['id']}", {"title": "Only Title"})
        self.assertEqual(status, 400)
        status, _, _ = self.request(
            "PUT", f"/books/{created['id']}", {"title": "T", "author": "A", "year": "abc"}
        )
        self.assertEqual(status, 400)

    def test_delete_book(self):
        created = self.create_book(title="Delete Me")
        status, data, _ = self.request("DELETE", f"/books/{created['id']}")
        self.assertEqual(status, 204)
        self.assertIsNone(data)
        status, _, _ = self.request("GET", f"/books/{created['id']}")
        self.assertEqual(status, 404)
        status, _, _ = self.request("DELETE", f"/books/{created['id']}")
        self.assertEqual(status, 404)

    def test_unknown_path_returns_404(self):
        status, _, _ = self.request("GET", "/nope")
        self.assertEqual(status, 404)

    def test_method_not_allowed(self):
        status, _, headers = self.request("DELETE", "/books")
        self.assertEqual(status, 405)
        self.assertIn("GET", headers.get("allow", ""))


if __name__ == "__main__":
    unittest.main()
