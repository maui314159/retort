package com.example.bookapi;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

/**
 * Small helper shared by tests to pull the {@code id} field out of a JSON
 * response body without re-instantiating an {@link ObjectMapper} everywhere.
 */
final class JsonTestSupport {

    private static final ObjectMapper MAPPER = new ObjectMapper();

    private JsonTestSupport() {
    }

    static Long idOf(String json) throws Exception {
        JsonNode node = MAPPER.readTree(json);
        if (!node.has("id")) {
            throw new IllegalStateException("Response missing id field: " + json);
        }
        return node.get("id").asLong();
    }
}
