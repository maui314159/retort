package com.example.books;

import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;

public class TestClient {
    private final HttpClient client;
    private final String base;

    public TestClient(int port) {
        this.client = HttpClient.newBuilder()
                .connectTimeout(Duration.ofSeconds(5))
                .build();
        this.base = "http://localhost:" + port;
    }

    public Response get(String path) throws IOException, InterruptedException {
        return send("GET", path, null);
    }

    public Response post(String path, String body) throws IOException, InterruptedException {
        return send("POST", path, body);
    }

    public Response put(String path, String body) throws IOException, InterruptedException {
        return send("PUT", path, body);
    }

    public Response delete(String path) throws IOException, InterruptedException {
        return send("DELETE", path, null);
    }

    private Response send(String method, String path, String body) throws IOException, InterruptedException {
        HttpRequest.Builder builder = HttpRequest.newBuilder()
                .uri(URI.create(base + path))
                .timeout(Duration.ofSeconds(5));
        HttpRequest.BodyPublisher publisher = body == null
                ? HttpRequest.BodyPublishers.noBody()
                : HttpRequest.BodyPublishers.ofString(body, StandardCharsets.UTF_8);
        switch (method) {
            case "GET" -> builder.GET();
            case "POST" -> builder.POST(publisher);
            case "PUT" -> builder.PUT(publisher);
            case "DELETE" -> builder.method("DELETE", publisher);
            default -> throw new IllegalArgumentException(method);
        }
        HttpResponse<String> resp = client.send(builder.build(), HttpResponse.BodyHandlers.ofString(StandardCharsets.UTF_8));
        return new Response(resp.statusCode(), resp.body());
    }

    public static class Response {
        public final int status;
        public final String body;

        Response(int status, String body) {
            this.status = status;
            this.body = body;
        }
    }
}
