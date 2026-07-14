use axum::http::StatusCode;
use axum::response::{IntoResponse, Response};
use axum::Json;
use serde_json::json;
use thiserror::Error;

/// Application-wide error type. Convertible into an axum `Response` so handlers
/// can return `Result<T, AppError>` and let the framework shape the HTTP reply.
#[derive(Debug, Error)]
pub enum AppError {
    #[error("book not found")]
    NotFound,

    #[error("validation failed: {0}")]
    Validation(String),

    #[error("invalid input: {0}")]
    BadRequest(String),
    #[error("database error: {0}")]
    Database(#[from] rusqlite::Error),

    #[error("pool error: {0}")]
    Pool(String),

    #[error("internal error: {0}")]
    Internal(String),
}

impl AppError {
    /// HTTP status code that corresponds to this error variant.
    fn status(&self) -> StatusCode {
        match self {
            AppError::NotFound => StatusCode::NOT_FOUND,
            AppError::Validation(_) | AppError::BadRequest(_) => StatusCode::BAD_REQUEST,
            AppError::Database(_) | AppError::Pool(_) | AppError::Internal(_) => {
                StatusCode::INTERNAL_SERVER_ERROR
            }
        }
    }
}

impl IntoResponse for AppError {
    fn into_response(self) -> Response {
        let status = self.status();
        let body = Json(json!({ "error": self.to_string() }));
        (status, body).into_response()
    }
}

pub type AppResult<T> = Result<T, AppError>;
