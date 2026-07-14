use crate::db::Db;
use crate::error::{AppError, AppResult, JsonRequest};
use crate::models::{Book, CreateBook, UpdateBook};
use axum::extract::{Path, Query, State};
use axum::http::StatusCode;
use axum::response::{IntoResponse, Response};
use axum::routing::{get, post};
use axum::{Json, Router};
use serde::Deserialize;
use std::net::SocketAddr;
use tokio::net::TcpListener;
use uuid::Uuid;

#[derive(Clone)]
pub struct AppState {
    pub db: Db,
}

pub async fn run_app(db_path: &str, addr: SocketAddr) -> AppResult<()> {
    let db = if db_path == ":memory:" {
        Db::open_in_memory()?
    } else {
        Db::open(db_path)?
    };
    let state = AppState { db };
    let app = router(state);
    tracing::info!("listening on {addr}");
    let listener = TcpListener::bind(addr).await?;
    axum::serve(listener, app).await?;
    Ok(())
}

pub fn router(state: AppState) -> Router {
    Router::new()
        .route("/health", get(health))
        .route("/books", post(create_book).get(list_books))
        .route(
            "/books/:id",
            get(get_book).put(update_book).delete(delete_book),
        )
        .with_state(state)
}

async fn health() -> impl IntoResponse {
    (StatusCode::OK, Json(serde_json::json!({ "status": "ok" })))
}

#[derive(Debug, Deserialize)]
pub struct ListQuery {
    pub author: Option<String>,
}

async fn list_books(
    State(state): State<AppState>,
    Query(q): Query<ListQuery>,
) -> AppResult<Json<Vec<Book>>> {
    let books = state.db.list(q.author.as_deref())?;
    Ok(Json(books))
}

async fn create_book(
    State(state): State<AppState>,
    JsonRequest(body): JsonRequest<CreateBook>,
) -> Result<Response, AppError> {
    if body.title.trim().is_empty() {
        return Err(AppError::BadRequest("title is required".into()));
    }
    if body.author.trim().is_empty() {
        return Err(AppError::BadRequest("author is required".into()));
    }
    if let Some(year) = body.year {
        if !(0..=3000).contains(&year) {
            return Err(AppError::BadRequest("year out of valid range".into()));
        }
    }
    if let Some(ref isbn) = body.isbn {
        if isbn.trim().is_empty() {
            return Err(AppError::BadRequest("isbn must not be blank if provided".into()));
        }
    }
    let id = Uuid::new_v4().to_string();
    let book = state.db.insert(&id, &body)?;
    Ok((StatusCode::CREATED, Json(book)).into_response())
}

async fn get_book(
    State(state): State<AppState>,
    Path(id): Path<String>,
) -> AppResult<Json<Book>> {
    let book = state.db.get(&id)?;
    Ok(Json(book))
}

async fn update_book(
    State(state): State<AppState>,
    Path(id): Path<String>,
    JsonRequest(body): JsonRequest<UpdateBook>,
) -> Result<Response, AppError> {
    if body.is_empty() {
        return Err(AppError::BadRequest("no fields provided to update".into()));
    }
    if let Some(ref title) = body.title {
        if title.trim().is_empty() {
            return Err(AppError::BadRequest("title must not be blank".into()));
        }
    }
    if let Some(ref author) = body.author {
        if author.trim().is_empty() {
            return Err(AppError::BadRequest("author must not be blank".into()));
        }
    }
    if let Some(year) = body.year {
        if !(0..=3000).contains(&year) {
            return Err(AppError::BadRequest("year out of valid range".into()));
        }
    }
    let book = state.db.update(&id, &body)?;
    Ok((StatusCode::OK, Json(book)).into_response())
}

async fn delete_book(
    State(state): State<AppState>,
    Path(id): Path<String>,
) -> Result<Response, AppError> {
    state.db.delete(&id)?;
    Ok((StatusCode::NO_CONTENT, "").into_response())
}
