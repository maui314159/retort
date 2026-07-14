pub mod db;
mod handlers;
pub mod models;

use actix_web::{web, App};
use rusqlite::Connection;
use std::sync::Mutex;

pub struct AppState {
    pub conn: Mutex<Connection>,
}

pub fn create_app(conn: Connection) -> App<
    impl actix_web::dev::ServiceFactory<
        actix_web::dev::ServiceRequest,
        Config = (),
        Response = actix_web::dev::ServiceResponse<impl actix_web::body::MessageBody>,
        Error = actix_web::Error,
        InitError = (),
    >,
> {
    App::new()
        .app_data(web::Data::new(AppState {
            conn: Mutex::new(conn),
        }))
        .route("/health", web::get().to(handlers::health))
        .route("/books", web::post().to(handlers::create_book))
        .route("/books", web::get().to(handlers::list_books))
        .route("/books/{id}", web::get().to(handlers::get_book))
        .route("/books/{id}", web::put().to(handlers::update_book))
        .route("/books/{id}", web::delete().to(handlers::delete_book))
}
