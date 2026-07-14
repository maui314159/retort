use crate::db::Database;
use crate::models::{
    BookResponse, CreateBookRequest, ErrorResponse, HealthResponse, UpdateBookRequest,
};
use actix_web::{web, HttpResponse, Responder};
use chrono::Utc;
use validator::Validate;

pub async fn health() -> impl Responder {
    HttpResponse::Ok().json(HealthResponse {
        status: "healthy".to_string(),
        timestamp: Utc::now(),
    })
}

pub async fn create_book(
    db: web::Data<Database>,
    req: web::Json<CreateBookRequest>,
) -> impl Responder {
    if let Err(e) = req.validate() {
        return HttpResponse::BadRequest().json(ErrorResponse {
            error: "ValidationError".to_string(),
            message: format!("{}", e),
        });
    }

    match db
        .create_book(&req.title, &req.author, req.year, req.isbn.as_deref())
        .await
    {
        Ok(book) => HttpResponse::Created().json(BookResponse::from(book)),
        Err(e) => HttpResponse::InternalServerError().json(ErrorResponse {
            error: "DatabaseError".to_string(),
            message: format!("{}", e),
        }),
    }
}

pub async fn list_books(
    db: web::Data<Database>,
    query: web::Query<std::collections::HashMap<String, String>>,
) -> impl Responder {
    let author_filter = query.get("author").map(|s| s.as_str());

    match db.list_books(author_filter).await {
        Ok(books) => {
            let responses: Vec<BookResponse> = books.into_iter().map(BookResponse::from).collect();
            HttpResponse::Ok().json(responses)
        }
        Err(e) => HttpResponse::InternalServerError().json(ErrorResponse {
            error: "DatabaseError".to_string(),
            message: format!("{}", e),
        }),
    }
}

pub async fn get_book(
    db: web::Data<Database>,
    path: web::Path<String>,
) -> impl Responder {
    let id = path.into_inner();

    match db.get_book(&id).await {
        Ok(book) => HttpResponse::Ok().json(BookResponse::from(book)),
        Err(sqlx::Error::RowNotFound) => HttpResponse::NotFound().json(ErrorResponse {
            error: "NotFound".to_string(),
            message: format!("Book with id {} not found", id),
        }),
        Err(e) => HttpResponse::InternalServerError().json(ErrorResponse {
            error: "DatabaseError".to_string(),
            message: format!("{}", e),
        }),
    }
}

pub async fn update_book(
    db: web::Data<Database>,
    path: web::Path<String>,
    req: web::Json<UpdateBookRequest>,
) -> impl Responder {
    let id = path.into_inner();

    if let Err(e) = req.validate() {
        return HttpResponse::BadRequest().json(ErrorResponse {
            error: "ValidationError".to_string(),
            message: format!("{}", e),
        });
    }

    // Check if book exists
    if let Err(sqlx::Error::RowNotFound) = db.get_book(&id).await {
        return HttpResponse::NotFound().json(ErrorResponse {
            error: "NotFound".to_string(),
            message: format!("Book with id {} not found", id),
        });
    }

    let isbn_update = req.isbn.as_deref();

    match db
        .update_book(
            &id,
            req.title.as_deref(),
            req.author.as_deref(),
            req.year,
            isbn_update,
        )
        .await
    {
        Ok(book) => HttpResponse::Ok().json(BookResponse::from(book)),
        Err(e) => HttpResponse::InternalServerError().json(ErrorResponse {
            error: "DatabaseError".to_string(),
            message: format!("{}", e),
        }),
    }
}

pub async fn delete_book(
    db: web::Data<Database>,
    path: web::Path<String>,
) -> impl Responder {
    let id = path.into_inner();

    // Check if book exists
    if let Err(sqlx::Error::RowNotFound) = db.get_book(&id).await {
        return HttpResponse::NotFound().json(ErrorResponse {
            error: "NotFound".to_string(),
            message: format!("Book with id {} not found", id),
        });
    }

    match db.delete_book(&id).await {
        Ok(_) => HttpResponse::NoContent().finish(),
        Err(e) => HttpResponse::InternalServerError().json(ErrorResponse {
            error: "DatabaseError".to_string(),
            message: format!("{}", e),
        }),
    }
}
