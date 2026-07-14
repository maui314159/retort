package com.example.books;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.JsonNode;

import java.io.IOException;
import java.io.InputStream;

public class JsonUtil {

    public static final ObjectMapper MAPPER = new ObjectMapper();

    public static String toJson(Object value) throws IOException {
        return MAPPER.writeValueAsString(value);
    }

    public static <T> T fromJson(InputStream in, Class<T> type) throws IOException {
        return MAPPER.readValue(in, type);
    }

    public static JsonNode readTree(InputStream in) throws IOException {
        return MAPPER.readTree(in);
    }
}
