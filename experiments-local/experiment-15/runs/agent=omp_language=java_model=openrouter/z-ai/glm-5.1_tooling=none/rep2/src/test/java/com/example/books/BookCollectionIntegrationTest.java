package com.example.books;

import com.example.books.model.Book;
import com.example.books.repository.BookRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import static org.hamcrest.Matchers.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest
@AutoConfigureMockMvc
class BookCollectionIntegrationTest {

    @Autowired
    MockMvc mvc;

    @Autowired
    BookRepository repository;

    @BeforeEach
    void clean() {
        repository.deleteAll();
    }

    @Test
    void createAndGetBook() throws Exception {
        String json = """
            {"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441172719"}
            """;

        mvc.perform(post("/books").contentType(MediaType.APPLICATION_JSON).content(json))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.id").isNumber())
                .andExpect(jsonPath("$.title").value("Dune"))
                .andExpect(jsonPath("$.author").value("Frank Herbert"))
                .andExpect(jsonPath("$.year").value(1965))
                .andExpect(jsonPath("$.isbn").value("978-0441172719"));

        mvc.perform(get("/books"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$", hasSize(1)))
                .andExpect(jsonPath("$[0].title").value("Dune"));
    }

    @Test
    void getBookById_andNotFound() throws Exception {
        String json = """
            {"title":"1984","author":"George Orwell","year":1949,"isbn":"978-0451524935"}
            """;

        String body = mvc.perform(post("/books").contentType(MediaType.APPLICATION_JSON).content(json))
                .andReturn().getResponse().getContentAsString();
        int id = com.fasterxml.jackson.databind.json.JsonMapper.builder().build().readTree(body).get("id").asInt();

        mvc.perform(get("/books/" + id))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.title").value("1984"));

        mvc.perform(get("/books/99999"))
                .andExpect(status().isNotFound());
    }

    @Test
    void updateBook() throws Exception {
        String json = """
            {"title":"Old Title","author":"Old Author","year":2000,"isbn":"111"}
            """;
        String body = mvc.perform(post("/books").contentType(MediaType.APPLICATION_JSON).content(json))
                .andReturn().getResponse().getContentAsString();
        int id = com.fasterxml.jackson.databind.json.JsonMapper.builder().build().readTree(body).get("id").asInt();

        String updateJson = """
            {"title":"New Title","author":"New Author"}
            """;
        mvc.perform(put("/books/" + id).contentType(MediaType.APPLICATION_JSON).content(updateJson))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.title").value("New Title"))
                .andExpect(jsonPath("$.author").value("New Author"))
                .andExpect(jsonPath("$.year").value(2000))
                .andExpect(jsonPath("$.isbn").value("111"));
    }

    @Test
    void deleteBook() throws Exception {
        String json = """
            {"title":"To Delete","author":"Author","year":2020,"isbn":"222"}
            """;
        String body = mvc.perform(post("/books").contentType(MediaType.APPLICATION_JSON).content(json))
                .andReturn().getResponse().getContentAsString();
        int id = com.fasterxml.jackson.databind.json.JsonMapper.builder().build().readTree(body).get("id").asInt();

        mvc.perform(delete("/books/" + id))
                .andExpect(status().isNoContent());

        mvc.perform(get("/books/" + id))
                .andExpect(status().isNotFound());

        mvc.perform(delete("/books/99999"))
                .andExpect(status().isNotFound());
    }

    @Test
    void filterByAuthor() throws Exception {
        String json1 = """
            {"title":"Book A","author":"Alice","year":2020,"isbn":"a1"}
            """;
        String json2 = """
            {"title":"Book B","author":"Bob","year":2021,"isbn":"b1"}
            """;
        mvc.perform(post("/books").contentType(MediaType.APPLICATION_JSON).content(json1));
        mvc.perform(post("/books").contentType(MediaType.APPLICATION_JSON).content(json2));

        mvc.perform(get("/books?author=Alice"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$", hasSize(1)))
                .andExpect(jsonPath("$[0].author").value("Alice"));
    }

    @Test
    void validationRejectsMissingTitleAndAuthor() throws Exception {
        String json = """
            {"year":2020}
            """;
        mvc.perform(post("/books").contentType(MediaType.APPLICATION_JSON).content(json))
                .andExpect(status().isBadRequest());
    }

    @Test
    void healthEndpoint() throws Exception {
        mvc.perform(get("/health"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("UP"));
    }
}
