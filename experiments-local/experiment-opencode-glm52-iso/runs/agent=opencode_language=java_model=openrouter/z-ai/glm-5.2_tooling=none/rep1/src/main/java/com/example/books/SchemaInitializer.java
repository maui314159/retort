package com.example.books;

import com.example.books.repository.BookRepository;
import org.springframework.boot.ApplicationRunner;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class SchemaInitializer {

    @Bean
    ApplicationRunner schemaBootstrap(BookRepository repository) {
        return args -> repository.initSchema();
    }
}
