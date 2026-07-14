package com.bookcollection;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.autoconfigure.data.jdbc.JdbcRepositoriesAutoConfiguration;

@SpringBootApplication(exclude = {JdbcRepositoriesAutoConfiguration.class})
public class BookCollectionApplication {
    public static void main(String[] args) {
        SpringApplication.run(BookCollectionApplication.class, args);
    }
}