package com.example.books;

import javax.sql.DataSource;

import org.springframework.boot.ApplicationRunner;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.jdbc.core.JdbcTemplate;

@Configuration
public class SchemaInitializer {

    @Bean
    ApplicationRunner bookSchemaInitializer(DataSource ds) {
        return args -> {
            JdbcTemplate jdbc = new JdbcTemplate(ds);
            String sql = """
                CREATE TABLE IF NOT EXISTS books (
                    id    INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    author TEXT NOT NULL,
                    year  INTEGER,
                    isbn  TEXT
                );
                """;
            jdbc.execute(sql);
        };
    }
}
