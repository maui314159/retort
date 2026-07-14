package com.example.books;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ObjectNode;

import java.io.IOException;

public final class JsonUtil {
    private static final ObjectMapper MAPPER = new ObjectMapper();

    private JsonUtil() {
    }

    public static ObjectMapper mapper() {
        return MAPPER;
    }

    public static String toJson(Object value) {
        try {
            return MAPPER.writeValueAsString(value);
        } catch (IOException e) {
            throw new RuntimeException("Failed to serialize JSON", e);
        }
    }

    public static JsonNode parse(String body) throws IOException {
        if (body == null || body.isBlank()) {
            return MAPPER.readTree("{}");
        }
        return MAPPER.readTree(body);
    }

    public static String errorJson(String message) {
        ObjectNode node = MAPPER.createObjectNode();
        node.put("error", message);
        return node.toString();
    }
}
