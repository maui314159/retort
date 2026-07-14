//! Book Collection REST API
//!
//! A small REST service for managing a book collection, backed by SQLite.
//! Exposes CRUD endpoints for books plus a health check.

pub mod db;
pub mod error;
pub mod handlers;
pub mod model;
pub mod router;

pub use error::{AppError, AppResult};
pub use model::{Book, BookCreate, BookUpdate};
pub use router::build_router;
