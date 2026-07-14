use book_collection_api::{db, models::Book};

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let pool = db::create_pool().await?;
    db::run_migrations(&pool).await?;
    
    // Test creating a book directly
    let book = Book::new(
        "Test Book".to_string(),
        "Test Author".to_string(),
        2023,
        "1234567890".to_string(),
    );
    
    println!("Book created: {:?}", book);
    
    Ok(())
}