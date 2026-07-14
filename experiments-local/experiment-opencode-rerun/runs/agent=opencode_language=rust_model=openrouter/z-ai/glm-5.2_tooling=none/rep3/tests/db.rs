use books_api::{db, init_state};
use books_api::models::CreateBook;

#[test]
fn insert_and_get_book() {
    let state = init_state(":memory:").unwrap();
    let conn = state.conn.lock().unwrap();
    let input = CreateBook {
        title: "Dune".into(),
        author: "Herbert".into(),
        year: Some(1965),
        isbn: Some("abc".into()),
    };
    let book = db::insert_book(&conn, &input).unwrap();
    assert_eq!(book.title, "Dune");
    let fetched = db::get_book(&conn, book.id).unwrap().unwrap();
    assert_eq!(fetched.author, "Herbert");
    assert_eq!(fetched.year, Some(1965));
}

#[test]
fn list_books_with_filter() {
    let state = init_state(":memory:").unwrap();
    let conn = state.conn.lock().unwrap();
    for (t, a) in [("x", "A"), ("y", "B"), ("z", "A")] {
        db::insert_book(
            &conn,
            &CreateBook {
                title: t.into(),
                author: a.into(),
                year: None,
                isbn: None,
            },
        )
        .unwrap();
    }
    let all = db::list_books(&conn, None).unwrap();
    assert_eq!(all.len(), 3);
    let filtered = db::list_books(&conn, Some("A")).unwrap();
    assert_eq!(filtered.len(), 2);
}

#[test]
fn update_and_delete() {
    let state = init_state(":memory:").unwrap();
    let conn = state.conn.lock().unwrap();
    let book = db::insert_book(
        &conn,
        &CreateBook {
            title: "Old".into(),
            author: "Auth".into(),
            year: None,
            isbn: None,
        },
    )
    .unwrap();

    use books_api::models::UpdateBook;
    let updated = db::update_book(
        &conn,
        book.id,
        &UpdateBook {
            title: Some("New".into()),
            author: None,
            year: Some(2000),
            isbn: None,
        },
    )
    .unwrap()
    .unwrap();
    assert_eq!(updated.title, "New");
    assert_eq!(updated.year, Some(2000));

    assert!(db::delete_book(&conn, book.id).unwrap());
    assert!(db::get_book(&conn, book.id).unwrap().is_none());
}
