import sys
import unittest
from test_api import test_health_check, test_create_book, test_create_book_validation, test_list_books, test_list_books_with_author_filter, test_get_book, test_get_book_not_found, test_update_book, test_update_book_not_found, test_delete_book, test_delete_book_not_found

def run_tests():
    test_functions = [
        test_health_check,
        test_create_book,
        test_create_book_validation,
        test_list_books,
        test_list_books_with_author_filter,
        test_get_book,
        test_get_book_not_found,
        test_update_book,
        test_update_book_not_found,
        test_delete_book,
        test_delete_book_not_found,
    ]
    
    passed = 0
    failed = 0
    
    for test_func in test_functions:
        try:
            test_func()
            print(f"✓ {test_func.__name__} passed")
            passed += 1
        except Exception as e:
            print(f"✗ {test_func.__name__} failed: {e}")
            failed += 1
    
    print(f"\nTotal: {passed} passed, {failed} failed")
    return failed == 0

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)