package com.example.books;

import static org.hamcrest.Matchers.hasSize;
import static org.hamcrest.Matchers.is;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.example.books.repository.BookRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
class BookControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private BookRepository repository;

    @BeforeEach
    void cleanUp() {
        repository.deleteAll();
    }

    private String bookJson(String title, String author, Integer year, String isbn) {
        StringBuilder sb = new StringBuilder("{");
        if (title != null) sb.append("\"title\":\"").append(title).append("\",");
        if (author != null) sb.append("\"author\":\"").append(author).append("\",");
        if (year != null) sb.append("\"year\":").append(year).append(",");
        if (isbn != null) sb.append("\"isbn\":\"").append(isbn).append("\",");
        // strip trailing comma
        String s = sb.toString();
        if (s.endsWith(",")) s = s.substring(0, s.length() - 1);
        return s + "}";
    }

    @Test
    void healthEndpointReturnsUp() throws Exception {
        mockMvc.perform(get("/health"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status", is("UP")));
    }

    @Test
    void createBookReturnsCreatedAndCanBeFetched() throws Exception {
        String body = bookJson("The Hobbit", "J.R.R. Tolkien", 1937, "978-0261102217");
        String location = mockMvc.perform(post("/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(body))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.title", is("The Hobbit")))
                .andExpect(jsonPath("$.author", is("J.R.R. Tolkien")))
                .andExpect(jsonPath("$.year", is(1937)))
                .andReturn().getResponse().getContentAsString();

        Long id = Long.parseLong(extractField(location, "id"));

        mockMvc.perform(get("/books/" + id))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.id", is(id.intValue())))
                .andExpect(jsonPath("$.isbn", is("978-0261102217")));
    }

    @Test
    void listBooksSupportsAuthorFilter() throws Exception {
        mockMvc.perform(post("/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(bookJson("Book A", "Author One", 2001, null)))
                .andExpect(status().isCreated());
        mockMvc.perform(post("/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(bookJson("Book B", "Author Two", 2002, null)))
                .andExpect(status().isCreated());
        mockMvc.perform(post("/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(bookJson("Book C", "Author One", 2003, null)))
                .andExpect(status().isCreated());

        mockMvc.perform(get("/books"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$", hasSize(3)));

        mockMvc.perform(get("/books").param("author", "Author One"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$", hasSize(2)))
                .andExpect(jsonPath("$[0].author", is("Author One")));
    }

    @Test
    void updateBookReplacesFields() throws Exception {
        String created = mockMvc.perform(post("/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(bookJson("Old Title", "Old Author", 1990, "old-isbn")))
                .andReturn().getResponse().getContentAsString();
        Long id = Long.parseLong(extractField(created, "id"));

        mockMvc.perform(put("/books/" + id)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(bookJson("New Title", "New Author", 2000, "new-isbn")))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.title", is("New Title")))
                .andExpect(jsonPath("$.author", is("New Author")))
                .andExpect(jsonPath("$.year", is(2000)))
                .andExpect(jsonPath("$.isbn", is("new-isbn")));
    }

    @Test
    void deleteBookReturnsNoContentAndSubsequentGetIs404() throws Exception {
        String created = mockMvc.perform(post("/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(bookJson("To Delete", "Author", 2010, null)))
                .andReturn().getResponse().getContentAsString();
        Long id = Long.parseLong(extractField(created, "id"));

        mockMvc.perform(delete("/books/" + id))
                .andExpect(status().isNoContent());

        mockMvc.perform(get("/books/" + id))
                .andExpect(status().isNotFound());
    }

    @Test
    void createBookWithMissingRequiredFieldsReturns400() throws Exception {
        // missing title and author
        String body = "{\"year\":1999}";
        mockMvc.perform(post("/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(body))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.errors.title").exists())
                .andExpect(jsonPath("$.errors.author").exists());
    }

    @Test
    void getNonExistentBookReturns404() throws Exception {
        mockMvc.perform(get("/books/999999"))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.status", is(404)));
    }

    private static String extractField(String json, String field) {
        String key = "\"" + field + "\":";
        int start = json.indexOf(key) + key.length();
        int end = start;
        while (end < json.length() && json.charAt(end) != ',' && json.charAt(end) != '}') {
            end++;
        }
        return json.substring(start, end).trim();
    }
}
