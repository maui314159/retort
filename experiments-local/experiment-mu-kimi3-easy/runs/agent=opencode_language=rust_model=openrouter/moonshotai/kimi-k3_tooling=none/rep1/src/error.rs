//! Error type mapping domain failures to HTTP responses with JSON bodies.

use axum::{
    http::StatusCode,
    response::{IntoResponse, Response},
    Json,
};
use serde_json::json;

/// Errors surfaced by handlers. Every variant carries a client-facing
/// message and maps to a distinct status code.
pub enum ApiError {
    /// 400 — the request failed input validation.
    BadRequest(String),
    /// 404 — the requested book does not exist.
    NotFound(String),
    /// 500 — an unexpected internal failure (e.g. database error).
    Internal(String),
}

impl IntoResponse for ApiError {
    fn into_response(self) -> Response {
        let (status, message) = match self {
            ApiError::BadRequest(m) => (StatusCode::BAD_REQUEST, m),
            ApiError::NotFound(m) => (StatusCode::NOT_FOUND, m),
            ApiError::Internal(m) => (StatusCode::INTERNAL_SERVER_ERROR, m),
        };
        (status, Json(json!({ "error": message }))).into_response()
    }
}

impl From<rusqlite::Error> for ApiError {
    fn from(e: rusqlite::Error) -> Self {
        ApiError::Internal(format!("database error: {e}"))
    }
}
