//! Data types for the book collection API.

use serde::{Deserialize, Serialize};

/// A book stored in the collection.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct Book {
    pub id: i64,
    pub title: String,
    pub author: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub year: Option<i64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub isbn: Option<String>,
}

/// Payload accepted by `POST /books` and `PUT /books`.
///
/// Every field is optional at the deserialization layer so handlers can
/// return their own 400 validation errors instead of axum's default 422.
#[derive(Debug, Deserialize)]
pub struct BookInput {
    pub title: Option<String>,
    pub author: Option<String>,
    pub year: Option<i64>,
    pub isbn: Option<String>,
}
