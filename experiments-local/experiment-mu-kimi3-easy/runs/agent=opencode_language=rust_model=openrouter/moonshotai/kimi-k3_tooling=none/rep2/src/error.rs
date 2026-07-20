use axum::{
    http::StatusCode,
    response::{IntoResponse, Response},
    Json,
};

use crate::models::ErrorResponse;

/// Errors surfaced to API clients as JSON bodies with suitable status codes.
#[derive(Debug)]
pub enum ApiError {
    /// 400 — input failed validation.
    BadRequest(String),
    /// 404 — the requested book does not exist.
    NotFound(String),
    /// 500 — unexpected server-side failure (e.g. database error).
    Internal(String),
}

impl IntoResponse for ApiError {
    fn into_response(self) -> Response {
        let (status, message) = match self {
            ApiError::BadRequest(m) => (StatusCode::BAD_REQUEST, m),
            ApiError::NotFound(m) => (StatusCode::NOT_FOUND, m),
            ApiError::Internal(m) => (StatusCode::INTERNAL_SERVER_ERROR, m),
        };
        (status, Json(ErrorResponse { error: message })).into_response()
    }
}

impl From<rusqlite::Error> for ApiError {
    fn from(err: rusqlite::Error) -> Self {
        ApiError::Internal(format!("database error: {err}"))
    }
}
