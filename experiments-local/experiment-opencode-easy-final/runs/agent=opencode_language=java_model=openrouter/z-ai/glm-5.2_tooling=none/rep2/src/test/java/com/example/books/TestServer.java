package com.example.books;

import com.sun.net.httpserver.HttpServer;

import java.io.IOException;
import java.net.InetSocketAddress;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.sql.SQLException;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * Starts an in-process HTTP server bound to an ephemeral port backed by an
 * in-memory SQLite database, exposing a real end-to-end test fixture.
 */
public class TestServer implements AutoCloseable {

    private final HttpServer server;
    private final BookRepository repository;
    private final ExecutorService executor;
    private final HttpClient client = HttpClient.newHttpClient();
    private final int port;

    public TestServer() throws IOException, SQLException {
        this.repository = new BookRepository(":memory:");
        this.server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        server.createContext("/health", new HealthHandler());
        server.createContext("/books", new BookHandler(repository));
        this.executor = Executors.newSingleThreadExecutor();
        server.setExecutor(executor);
        server.start();
        this.port = server.getAddress().getPort();
    }

    public int port() { return port; }

    public HttpResponse<String> send(String method, String path, String body) throws IOException, InterruptedException {
        HttpRequest.Builder b = HttpRequest.newBuilder()
                .uri(URI.create("http://127.0.0.1:" + port + path));
        if (body == null) b.method(method, HttpRequest.BodyPublishers.noBody());
        else b.method(method, HttpRequest.BodyPublishers.ofString(body));
        return client.send(b.header("Content-Type", "application/json").build(),
                HttpResponse.BodyHandlers.ofString());
    }

    @Override
    public void close() {
        server.stop(0);
        executor.shutdownNow();
        try { repository.close(); } catch (SQLException e) { /* ignore */ }
    }
}
