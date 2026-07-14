package com.example.bookstore.config;

import org.hibernate.community.dialect.SQLiteDialect;

public class CustomSQLiteDialect extends org.hibernate.community.dialect.SQLiteDialect {
    public CustomSQLiteDialect() {
        super();
    }
}