#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    books_api::serve().await
}
