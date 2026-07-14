package com.example.bookstore;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;

public final class Json {
    public static final ObjectMapper MAPPER = new ObjectMapper()
            .disable(SerializationFeature.WRITE_DATES_AS_TIMESTAMPS);

    private Json() {}

    public static String toJson(Object value) throws Exception {
        return MAPPER.writeValueAsString(value);
    }

    @SuppressWarnings("unchecked")
    public static <T> T fromJson(String content, Class<T> type) throws Exception {
        return MAPPER.readValue(content, type);
    }
}
