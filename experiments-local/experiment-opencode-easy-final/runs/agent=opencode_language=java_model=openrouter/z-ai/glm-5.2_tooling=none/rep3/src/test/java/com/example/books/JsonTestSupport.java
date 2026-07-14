package com.example.books;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

public final class JsonTestSupport {
    private static final ObjectMapper MAPPER = new ObjectMapper();

    private JsonTestSupport() {
    }

    public static Long extractId(String json) {
        try {
            JsonNode node = MAPPER.readTree(json);
            return node.get("id").asLong();
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
    }
}
