use async_trait::async_trait;
use axum::extract::rejection::JsonRejection;
use axum::extract::{FromRequest, Request};
use axum::http::StatusCode;
use axum::response::{IntoResponse, Response};
use axum::Json;
use serde::de::DeserializeOwned;
use serde_json::json;
use std::fmt;

#[derive(Debug)]
pub enum AppError {
    NotFound(String),
    BadRequest(String),
    Internal(String),
}

impl fmt::Display for AppError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            AppError::NotFound(msg) => write!(f, "not found: {msg}"),
            AppError::BadRequest(msg) => write!(f, "bad request: {msg}"),
            AppError::Internal(msg) => write!(f, "internal error: {msg}"),
        }
    }
}

impl std::error::Error for AppError {}

impl From<rusqlite::Error> for AppError {
    fn from(err: rusqlite::Error) -> Self {
        AppError::Internal(err.to_string())
    }
}

impl From<std::io::Error> for AppError {
    fn from(err: std::io::Error) -> Self {
        AppError::Internal(err.to_string())
    }
}

impl From<tokio::task::JoinError> for AppError {
    fn from(err: tokio::task::JoinError) -> Self {
        AppError::Internal(err.to_string())
    }
}

impl From<serde_json::Error> for AppError {
    fn from(err: serde_json::Error) -> Self {
        AppError::Internal(err.to_string())
    }
}

impl IntoResponse for AppError {
    fn into_response(self) -> Response {
        let (status, body) = match self {
            AppError::NotFound(msg) => (StatusCode::NOT_FOUND, json!({ "error": "not_found", "message": msg })),
            AppError::BadRequest(msg) => (StatusCode::BAD_REQUEST, json!({ "error": "bad_request", "message": msg })),
            AppError::Internal(msg) => (StatusCode::INTERNAL_SERVER_ERROR, json!({ "error": "internal_error", "message": msg })),
        };
        (status, Json(body)).into_response()
    }
}

pub type AppResult<T> = Result<T, AppError>;

/// Wrapper around `axum::Json` that converts deserialization rejections into
/// `400 Bad Request` (axum's default is 422). Missing required fields such as
/// `title`/`author` are reported by serde as deserialization errors, so this
/// ensures the "title and author are required" validation surfaces as 400.
#[derive(Debug, Clone, Copy, Default)]
pub struct JsonRequest<T>(pub T);

#[async_trait]
impl<S, T> FromRequest<S> for JsonRequest<T>
where
    T: DeserializeOwned,
    S: Send + Sync,
{
    type Rejection = AppError;

    async fn from_request(req: Request, state: &S) -> Result<Self, Self::Rejection> {
        match Json::<T>::from_request(req, state).await {
            Ok(Json(value)) => Ok(JsonRequest(value)),
            Err(rejection) => {
                let msg = match rejection {
                    JsonRejection::JsonDataError(err) => {
                        format!("invalid request body: {err}")
                    }
                    JsonRejection::MissingJsonContentType(_) => {
                        "request body must be valid JSON".to_string()
                    }
                    other => other.body_text(),
                };
                Err(AppError::BadRequest(msg))
            }
        }
    }
}
