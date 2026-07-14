package com.example.books.config;

import com.example.books.repository.BookRepository;
import org.springframework.boot.context.event.ApplicationReadyEvent;
import org.springframework.context.event.EventListener;
import org.springframework.stereotype.Component;

@Component
public class SchemaInitializer {

    private final BookRepository repository;

    public SchemaInitializer(BookRepository repository) {
        this.repository = repository;
    }

    @EventListener(ApplicationReadyEvent.class)
    public void init() {
        repository.initSchema();
    }
}
