package com.bookcollection.controller;

import com.bookcollection.BookCollectionApplication;
import com.bookcollection.dto.BookRequest;
import com.bookcollection.dto.BookResponse;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.BeforeEach;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;
import static org.assertj.core.api.Assertions.assertThat;

@SpringBootTest(classes = BookCollectionApplication.class)
@AutoConfigureMockMvc
public class BookControllerTest {
    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;
    @Autowired
    private JdbcTemplate jdbcTemplate;

    @BeforeEach
    public void setUp() {
        jdbcTemplate.execute("DELETE FROM books");
    }

    @Test
    public void testHealthCheck() throws Exception {
        mockMvc.perform(get("/health"))
                .andExpect(status().isOk())
                .andExpect(content().string("UP"));
    }

    @Test
    public void testCreateBookValid() throws Exception {
        BookRequest request = new BookRequest();
        request.setTitle("The Hobbit");
        request.setAuthor("J.R.R. Tolkien");
        request.setYear(1937);
        request.setIsbn("978-0547928227");

        MvcResult result = mockMvc.perform(post("/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isCreated())
                .andReturn();

        BookResponse response = objectMapper.readValue(result.getResponse().getContentAsString(), BookResponse.class);
        assertThat(response.getId()).isNotNull();
        assertThat(response.getTitle()).isEqualTo("The Hobbit");
        assertThat(response.getAuthor()).isEqualTo("J.R.R. Tolkien");
    }

    @Test
    public void testCreateBookMissingTitle() throws Exception {
        BookRequest request = new BookRequest();
        request.setAuthor("J.R.R. Tolkien");
        request.setYear(1937);

        mockMvc.perform(post("/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isBadRequest());
    }

    @Test
    public void testGetAllBooks() throws Exception {
        BookRequest request = new BookRequest();
        request.setTitle("The Hobbit");
        request.setAuthor("J.R.R. Tolkien");
        mockMvc.perform(post("/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isCreated());

        mockMvc.perform(get("/books"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.length()").value(1));
    }

    @Test
    public void testGetBooksByAuthor() throws Exception {
        BookRequest request = new BookRequest();
        request.setTitle("The Hobbit");
        request.setAuthor("J.R.R. Tolkien");
        mockMvc.perform(post("/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isCreated());

        mockMvc.perform(get("/books?author=Tolkien"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.length()").value(1));

        mockMvc.perform(get("/books?author=Rowling"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.length()").value(0));
    }

    @Test
    public void testGetBookByIdNotFound() throws Exception {
        mockMvc.perform(get("/books/999"))
                .andExpect(status().isNotFound());
    }

    @Test
    public void testUpdateBook() throws Exception {
        BookRequest createRequest = new BookRequest();
        createRequest.setTitle("The Hobbit");
        createRequest.setAuthor("J.R.R. Tolkien");
        MvcResult createResult = mockMvc.perform(post("/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(createRequest)))
                .andExpect(status().isCreated())
                .andReturn();
        BookResponse createResponse = objectMapper.readValue(createResult.getResponse().getContentAsString(), BookResponse.class);
        Long bookId = createResponse.getId();

        BookRequest updateRequest = new BookRequest();
        updateRequest.setTitle("The Lord of the Rings");
        updateRequest.setAuthor("J.R.R. Tolkien");
        updateRequest.setYear(1954);
        mockMvc.perform(put("/books/" + bookId)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(updateRequest)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.title").value("The Lord of the Rings"))
                .andExpect(jsonPath("$.year").value(1954));
    }

    @Test
    public void testDeleteBook() throws Exception {
        BookRequest createRequest = new BookRequest();
        createRequest.setTitle("The Hobbit");
        createRequest.setAuthor("J.R.R. Tolkien");
        MvcResult createResult = mockMvc.perform(post("/books")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(createRequest)))
                .andExpect(status().isCreated())
                .andReturn();
        BookResponse createResponse = objectMapper.readValue(createResult.getResponse().getContentAsString(), BookResponse.class);
        Long bookId = createResponse.getId();

        mockMvc.perform(delete("/books/" + bookId))
                .andExpect(status().isNoContent());

        mockMvc.perform(get("/books/" + bookId))
                .andExpect(status().isNotFound());
    }
}
