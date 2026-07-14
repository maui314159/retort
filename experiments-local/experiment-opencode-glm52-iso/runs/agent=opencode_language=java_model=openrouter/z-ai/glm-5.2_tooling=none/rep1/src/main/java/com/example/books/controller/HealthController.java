package com.example.books.controller;

import com.example.books.repository.BookRepository;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

@RestController
public class HealthController {

    private final BookRepository repository;

    public HealthController(BookRepository repository) {
        this.repository = repository;
    }

    @GetMapping("/health")
    public Map<String, String> health() {
        String status;
        try {
            repository.findAll();
            status = "UP";
        } catch (Exception e) {
            status = "DOWN";
        }
        return Map.of("status", status);
    }
}
