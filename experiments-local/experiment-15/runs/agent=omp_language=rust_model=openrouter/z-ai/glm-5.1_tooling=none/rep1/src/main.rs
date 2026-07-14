use actix_web::HttpServer;
use rusqlite::Connection;

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    let _conn = book_api::db::init_db("books.db").expect("Failed to initialize database");
    let server = HttpServer::new(move || {
        let conn = Connection::open("books.db").expect("Failed to open database");
        book_api::create_app(conn)
    })
    .bind("127.0.0.1:8080")?
    .run();
    println!("Server running at http://127.0.0.1:8080");
    server.await
}
