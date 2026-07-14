use axum::http::StatusCode;
use serde::Serialize;

#[derive(Debug)]
pub enum AppError {
    NotFound(String),
    Validation(String),
    Internal(String),
}

#[derive(Serialize)]
pub struct ErrorResponse {
    pub error: String,
}

impl axum::response::IntoResponse for AppError {
    fn into_response(self) -> axum::response::Response {
        let (status, message) = match self {
            AppError::NotFound(msg) => (StatusCode::NOT_FOUND, msg),
            AppError::Validation(msg) => (StatusCode::BAD_REQUEST, msg),
            AppError::Internal(msg) => (StatusCode::INTERNAL_SERVER_ERROR, msg),
        };
        let body = ErrorResponse { error: message };
        (status, axum::Json(body)).into_response()
    }
}

impl From<sqlx::Error> for AppError {
    fn from(e: sqlx::Error) -> Self {
        AppError::Internal(e.to_string())
    }
}
