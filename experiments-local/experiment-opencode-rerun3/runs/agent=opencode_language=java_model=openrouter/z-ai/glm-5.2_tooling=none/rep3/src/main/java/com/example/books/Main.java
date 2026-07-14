package com.example.books;

import com.sun.net.httpserver.HttpServer;

import java.io.IOException;
import java.net.InetSocketAddress;
import java.util.concurrent.Executors;

public class Main {

    public static void main(String[] args) throws Exception {
        int port = portFromArgs(args);
        String dbPath = dbPathFromArgs(args);
        start(port, dbPath);
    }

    public static HttpServer start(int port, String dbPath) throws IOException {
        BookRepository repository = new BookRepository(dbPath);
        HttpServer server = HttpServer.create(new InetSocketAddress(port), 0);
        server.createContext("/health", new HealthHandler());
        server.createContext("/books", new BookHandler(repository));
        server.setExecutor(Executors.newFixedThreadPool(8));
        server.start();
        int actualPort = server.getAddress().getPort();
        System.out.println("Book API listening on http://localhost:" + actualPort
                + " (db=" + dbPath + ")");
        Runtime.getRuntime().addShutdownHook(new Thread(() -> {
            System.out.println("Shutting down...");
            server.stop(0);
            repository.close();
        }));
        return server;
    }

    private static int portFromArgs(String[] args) {
        for (int i = 0; i < args.length - 1; i++) {
            if ("--port".equals(args[i])) {
                return Integer.parseInt(args[i + 1]);
            }
        }
        String env = System.getenv("BOOKAPI_PORT");
        if (env != null && !env.isBlank()) {
            return Integer.parseInt(env);
        }
        return 8080;
    }

    private static String dbPathFromArgs(String[] args) {
        for (int i = 0; i < args.length - 1; i++) {
            if ("--db".equals(args[i])) {
                return args[i + 1];
            }
        }
        String env = System.getenv("BOOKAPI_DB");
        if (env != null && !env.isBlank()) {
            return env;
        }
        return "books.db";
    }
}
