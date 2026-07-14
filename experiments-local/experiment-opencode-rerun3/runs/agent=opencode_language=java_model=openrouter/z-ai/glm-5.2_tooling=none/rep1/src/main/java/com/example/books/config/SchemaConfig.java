package com.example.books.config;

import com.example.books.repository.BookRepository;
import org.springframework.boot.ApplicationRunner;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class SchemaConfig {

    @Bean
    ApplicationRunner schemaInitializer(BookRepository bookRepository) {
        return args -> bookRepository.initSchema();
    }
}
