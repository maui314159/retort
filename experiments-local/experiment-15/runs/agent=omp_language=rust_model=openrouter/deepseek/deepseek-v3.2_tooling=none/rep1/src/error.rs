use axum::{
    http::StatusCode,
    response::{IntoResponse, Response},
    Json,
};
use serde_json::json;
use sqlx::Error as SqlxError;
use thiserror::Error;

#[derive(Error, Debug)]
pub enum AppError {
    #[error("Database error: {0}")]
    Database(#[from] SqlxError),

    #[error("Book not found")]
    NotFound,

    #[error("Validation error: {0}")]
    Validation(String),

    #[error("ISBN already exists")]
    DuplicateIsbn,


}
impl IntoResponse for AppError {
    fn into_response(self) -> Response {
        let (status, message) = match self {
            AppError::Database(_) => (StatusCode::INTERNAL_SERVER_ERROR, "Database error".to_string()),
            AppError::NotFound => (StatusCode::NOT_FOUND, "Book not found".to_string()),
            AppError::Validation(ref msg) => (StatusCode::BAD_REQUEST, msg.clone()),
            AppError::DuplicateIsbn => (StatusCode::CONFLICT, "ISBN already exists".to_string()),
        };

        let body = Json(json!({
            "error": message,
            "message": self.to_string()
        }));

        (status, body).into_response()
    }
}

impl From<String> for AppError {
    fn from(err: String) -> Self {
        AppError::Validation(err)
    }
}

impl From<&str> for AppError {
    fn from(err: &str) -> Self {
        AppError::Validation(err.to_string())
    }
}