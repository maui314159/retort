//! Application error type with HTTP response conversion via `IntoResponse`.

use axum::http::StatusCode;
use axum::response::{IntoResponse, Response};
use axum::Json;
use serde_json::json;
use thiserror::Error;

/// Result alias used across the application.
pub type AppResult<T> = Result<T, AppError>;

/// Top-level error type for the API.
///
/// Variants map to specific HTTP status codes via [`IntoResponse`].
#[derive(Debug, Error)]
pub enum AppError {
    /// A required field was missing or failed validation (HTTP 400).
    #[error("validation error: {0}")]
    Validation(String),

    /// A book was not found (HTTP 404).
    #[error("book not found")]
    NotFound,

    /// The request path or query contained a value that could not be parsed (HTTP 400).
    #[error("bad request: {0}")]
    BadRequest(String),

    /// Underlying database error (HTTP 500).
    #[error("database error: {0}")]
    Database(#[from] sqlx::Error),

    /// Catch-all for unexpected failures (HTTP 500).
    #[error("internal error: {0}")]
    Internal(String),
}

impl AppError {
    fn status_and_code(&self) -> (StatusCode, &'static str) {
        match self {
            AppError::Validation(_) => (StatusCode::BAD_REQUEST, "validation_error"),
            AppError::NotFound => (StatusCode::NOT_FOUND, "not_found"),
            AppError::BadRequest(_) => (StatusCode::BAD_REQUEST, "bad_request"),
            AppError::Database(_) | AppError::Internal(_) => {
                (StatusCode::INTERNAL_SERVER_ERROR, "internal_error")
            }
        }
    }
}

impl IntoResponse for AppError {
    fn into_response(self) -> Response {
        let (status, code) = self.status_and_code();

        // Log server-side errors so operators can see them.
        if status == StatusCode::INTERNAL_SERVER_ERROR {
            tracing::error!(error = ?self, "request failed with internal error");
        } else {
            tracing::debug!(error = %self, "request rejected");
        }

        let message = self.to_string();
        let body = Json(json!({
            "error": {
                "code": code,
                "message": message,
            }
        }));

        (status, body).into_response()
    }
}
