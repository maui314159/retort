use actix_web::{web, HttpRequest, HttpResponse};

use crate::db;
use crate::models::{CreateBook, ErrorResponse, UpdateBook};
use crate::AppState;

pub async fn health() -> HttpResponse {
    HttpResponse::Ok().json(serde_json::json!({ "status": "ok" }))
}

pub async fn create_book(body: web::Json<CreateBook>, state: web::Data<AppState>) -> HttpResponse {
    if let Err(e) = body.validate() {
        return HttpResponse::BadRequest().json(ErrorResponse { error: e });
    }

    let book = crate::models::Book {
        id: uuid::Uuid::new_v4().to_string(),
        title: body.title.clone(),
        author: body.author.clone(),
        year: body.year,
        isbn: body.isbn.clone(),
    };

    let conn = state.conn.lock().unwrap();
    match db::insert_book(&conn, &book) {
        Ok(()) => HttpResponse::Created().json(book),
        Err(e) => HttpResponse::InternalServerError().json(ErrorResponse { error: e.to_string() }),
    }
}

pub async fn list_books(req: HttpRequest, state: web::Data<AppState>) -> HttpResponse {
    let author_filter = req.query_string()
        .split('&')
        .filter_map(|pair| {
            let mut parts = pair.splitn(2, '=');
            let key = parts.next()?;
            let val = parts.next()?;
            if key == "author" {
                Some(urlencoding::decode(val).ok()?.into_owned())
            } else {
                None
            }
        })
        .next();

    let conn = state.conn.lock().unwrap();
    match db::list_books(&conn, author_filter.as_deref()) {
        Ok(books) => HttpResponse::Ok().json(books),
        Err(e) => HttpResponse::InternalServerError().json(ErrorResponse { error: e.to_string() }),
    }
}

pub async fn get_book(path: web::Path<String>, state: web::Data<AppState>) -> HttpResponse {
    let id = path.into_inner();
    let conn = state.conn.lock().unwrap();
    match db::get_book(&conn, &id) {
        Ok(Some(book)) => HttpResponse::Ok().json(book),
        Ok(None) => HttpResponse::NotFound().json(ErrorResponse { error: "book not found".into() }),
        Err(e) => HttpResponse::InternalServerError().json(ErrorResponse { error: e.to_string() }),
    }
}

pub async fn update_book(
    path: web::Path<String>,
    body: web::Json<UpdateBook>,
    state: web::Data<AppState>,
) -> HttpResponse {
    let id = path.into_inner();

    // Validate: if title/author provided, they must be non-empty
    if let Some(ref t) = body.title {
        if t.trim().is_empty() {
            return HttpResponse::BadRequest().json(ErrorResponse { error: "title must not be empty".into() });
        }
    }
    if let Some(ref a) = body.author {
        if a.trim().is_empty() {
            return HttpResponse::BadRequest().json(ErrorResponse { error: "author must not be empty".into() });
        }
    }

    let conn = state.conn.lock().unwrap();
    match db::update_book(&conn, &id, body.title.as_deref(), body.author.as_deref(), body.year, body.isbn.as_deref()) {
        Ok(true) => {
            match db::get_book(&conn, &id) {
                Ok(Some(book)) => HttpResponse::Ok().json(book),
                Ok(None) => HttpResponse::NotFound().json(ErrorResponse { error: "book not found".into() }),
                Err(e) => HttpResponse::InternalServerError().json(ErrorResponse { error: e.to_string() }),
            }
        }
        Ok(false) => HttpResponse::NotFound().json(ErrorResponse { error: "book not found".into() }),
        Err(e) => HttpResponse::InternalServerError().json(ErrorResponse { error: e.to_string() }),
    }
}

pub async fn delete_book(path: web::Path<String>, state: web::Data<AppState>) -> HttpResponse {
    let id = path.into_inner();
    let conn = state.conn.lock().unwrap();
    match db::delete_book(&conn, &id) {
        Ok(true) => HttpResponse::NoContent().finish(),
        Ok(false) => HttpResponse::NotFound().json(ErrorResponse { error: "book not found".into() }),
        Err(e) => HttpResponse::InternalServerError().json(ErrorResponse { error: e.to_string() }),
    }
}
