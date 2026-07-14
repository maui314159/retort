package com.example.books.exception;

import java.util.Map;

public class ErrorResponse {

    private final int status;
    private final String error;
    private final String message;
    private final Map<String, String> details;

    public ErrorResponse(int status, String error, String message, Map<String, String> details) {
        this.status = status;
        this.error = error;
        this.message = message;
        this.details = details;
    }

    public int getStatus() {
        return status;
    }

    public String getError() {
        return error;
    }

    public String getMessage() {
        return message;
    }

    public Map<String, String> getDetails() {
        return details;
    }
}
