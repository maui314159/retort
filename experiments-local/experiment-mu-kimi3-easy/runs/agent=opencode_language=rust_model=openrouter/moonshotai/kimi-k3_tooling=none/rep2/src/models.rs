use serde::{Deserialize, Serialize};

/// A book stored in the collection.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct Book {
    pub id: i64,
    pub title: String,
    pub author: String,
    pub year: Option<i64>,
    pub isbn: Option<String>,
}

/// Payload accepted when creating or replacing a book.
///
/// `title` and `author` are required (missing fields are rejected by serde
/// with 422; blank values are rejected by handler validation with 400).
#[derive(Debug, Clone, Deserialize)]
pub struct BookInput {
    pub title: String,
    pub author: String,
    #[serde(default)]
    pub year: Option<i64>,
    #[serde(default)]
    pub isbn: Option<String>,
}

/// JSON body returned for error responses.
#[derive(Debug, Serialize)]
pub struct ErrorResponse {
    pub error: String,
}
