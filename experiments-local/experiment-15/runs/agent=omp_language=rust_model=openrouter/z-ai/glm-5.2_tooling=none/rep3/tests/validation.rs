use book_collection::models::validate_required;

#[test]
fn validate_accepts_nonempty() {
    assert!(validate_required("Title", "Author").is_ok());
    assert!(validate_required(" T ", " A ").is_ok());
}

#[test]
fn validate_rejects_empty_title() {
    let err = validate_required("", "Author").unwrap_err();
    assert_eq!(err.field, "title");
}

#[test]
fn validate_rejects_whitespace_only_author() {
    let err = validate_required("Title", "   ").unwrap_err();
    assert_eq!(err.field, "author");
}
