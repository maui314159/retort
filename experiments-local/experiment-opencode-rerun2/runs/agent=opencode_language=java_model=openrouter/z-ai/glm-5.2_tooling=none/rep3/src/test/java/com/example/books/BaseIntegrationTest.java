package com.example.books;

import com.example.books.repository.BookRepository;
import org.junit.jupiter.api.BeforeEach;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.TestPropertySource;
import org.springframework.test.web.servlet.MockMvc;

@SpringBootTest
@AutoConfigureMockMvc
@TestPropertySource(properties = {
        "spring.datasource.url=jdbc:sqlite:file:memtestdb?mode=memory&cache=shared",
        "spring.datasource.hikari.maximum-pool-size=1"
})
public abstract class BaseIntegrationTest {

    @Autowired
    protected MockMvc mockMvc;

    @Autowired
    protected BookRepository repository;

    @BeforeEach
    void cleanDb() {
        repository.initSchema();
        repository.findAll(null).forEach(b -> repository.deleteById(b.getId()));
    }
}
