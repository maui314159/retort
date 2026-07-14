package com.example.books;

import com.fasterxml.jackson.databind.ObjectMapper;
import io.javalin.Javalin;
import io.javalin.http.HttpStatus;

public class Main {

    public static Javalin createApp(String dbPath) {
        BookRepository repository = new BookRepository(dbPath);
        ObjectMapper mapper = new ObjectMapper();
        BookController controller = new BookController(repository, mapper);

        Javalin app = Javalin.create();

        app.get("/health", controller::health);

        app.post("/books", controller::create);
        app.get("/books", controller::list);
        app.get("/books/{id}", controller::getOne);
        app.put("/books/{id}", controller::update);
        app.delete("/books/{id}", controller::delete);

        registerExceptionHandlers(app);

        return app;
    }

    private static void registerExceptionHandlers(Javalin app) {
        app.exception(ValidationException.class, (e, ctx) -> {
            ctx.json(BookController.errorBody(e.getMessage())).status(HttpStatus.BAD_REQUEST);
        });
        app.exception(BookController.NotFoundException.class, (e, ctx) -> {
            ctx.json(BookController.errorBody(e.getMessage())).status(HttpStatus.NOT_FOUND);
        });
        app.exception(Exception.class, (e, ctx) -> {
            ctx.json(BookController.errorBody("Internal server error")).status(HttpStatus.INTERNAL_SERVER_ERROR);
        });
    }

    public static void main(String[] args) {
        String dbPath = System.getenv().getOrDefault("DB_PATH", "books.db");
        int port = Integer.parseInt(System.getenv().getOrDefault("PORT", "7000"));
        Javalin app = createApp(dbPath);
        app.start(port);
    }
}
