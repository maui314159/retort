use actix_web::{web, HttpResponse, Responder};
use sqlx::SqlitePool;
use crate::models::*;
use crate::db;

pub async fn health_check() -> impl Responder {
    HttpResponse::Ok().json(HealthResponse {
        status: "healthy".to_string(),
        timestamp: chrono::Utc::now().to_rfc3339(),
    })
}

pub async fn create_book(
    pool: web::Data<SqlitePool>,
    req: web::Json<CreateBookRequest>,
) -> impl Responder {
    let book = Book {
        id: None,
        title: req.title.clone(),
        author: req.author.clone(),
        year: req.year,
        isbn: req.isbn.clone(),
        created_at: None,
        updated_at: None,
    };

    if let Err(err) = book.validate() {
        return HttpResponse::BadRequest().json(ErrorResponse { error: err });
    }

    match db::create_book(pool.get_ref(), req.into_inner()).await {
        Ok(book) => HttpResponse::Created().json(BookResponse::from(book)),
        Err(e) => HttpResponse::InternalServerError().json(ErrorResponse {
            error: format!("Failed to create book: {}", e),
        }),
    }
}

pub async fn get_books(
    pool: web::Data<SqlitePool>,
    query: web::Query<std::collections::HashMap<String, String>>,
) -> impl Responder {
    let author_filter = query.get("author").cloned();

    match db::get_all_books(pool.get_ref(), author_filter).await {
        Ok(books) => {
            let responses: Vec<BookResponse> = books.into_iter().map(BookResponse::from).collect();
            HttpResponse::Ok().json(responses)
        }
        Err(e) => HttpResponse::InternalServerError().json(ErrorResponse {
            error: format!("Failed to fetch books: {}", e),
        }),
    }
}

pub async fn get_book(
    pool: web::Data<SqlitePool>,
    path: web::Path<i64>,
) -> impl Responder {
    let id = path.into_inner();

    match db::get_book_by_id(pool.get_ref(), id).await {
        Ok(Some(book)) => HttpResponse::Ok().json(BookResponse::from(book)),
        Ok(None) => HttpResponse::NotFound().json(ErrorResponse {
            error: format!("Book with id {} not found", id),
        }),
        Err(e) => HttpResponse::InternalServerError().json(ErrorResponse {
            error: format!("Failed to fetch book: {}", e),
        }),
    }
}

pub async fn update_book(
    pool: web::Data<SqlitePool>,
    path: web::Path<i64>,
    req: web::Json<UpdateBookRequest>,
) -> impl Responder {
    let id = path.into_inner();

    match db::update_book(pool.get_ref(), id, req.into_inner()).await {
        Ok(Some(book)) => HttpResponse::Ok().json(BookResponse::from(book)),
        Ok(None) => HttpResponse::NotFound().json(ErrorResponse {
            error: format!("Book with id {} not found", id),
        }),
        Err(e) => HttpResponse::InternalServerError().json(ErrorResponse {
            error: format!("Failed to update book: {}", e),
        }),
    }
}

pub async fn delete_book(
    pool: web::Data<SqlitePool>,
    path: web::Path<i64>,
) -> impl Responder {
    let id = path.into_inner();

    match db::delete_book(pool.get_ref(), id).await {
        Ok(true) => HttpResponse::Ok().json(SuccessResponse {
            message: format!("Book with id {} deleted successfully", id),
        }),
        Ok(false) => HttpResponse::NotFound().json(ErrorResponse {
            error: format!("Book with id {} not found", id),
        }),
        Err(e) => HttpResponse::InternalServerError().json(ErrorResponse {
            error: format!("Failed to delete book: {}", e),
        }),
    }
}
