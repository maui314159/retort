package com.example.books;

import org.springframework.beans.BeansException;
import org.springframework.beans.factory.config.BeanFactoryPostProcessor;
import org.springframework.beans.factory.config.ConfigurableListableBeanFactory;
import org.springframework.context.EnvironmentAware;
import org.springframework.core.env.Environment;
import org.springframework.stereotype.Component;

import java.io.File;

/**
 * Creates the parent directory of the SQLite file configured in
 * {@code spring.datasource.url} before any DataSource bean is instantiated.
 * Runs as a {@link BeanFactoryPostProcessor}, so it fires before Hikari tries
 * to open a JDBC connection.
 */
@Component
public class SqliteDirEnsurer implements BeanFactoryPostProcessor, EnvironmentAware {

    private Environment env;

    @Override
    public void setEnvironment(Environment environment) {
        this.env = environment;
    }

    @Override
    public void postProcessBeanFactory(ConfigurableListableBeanFactory beanFactory) throws BeansException {
        String url = env.getProperty("spring.datasource.url");
        if (url == null || !url.startsWith("jdbc:sqlite:")) return;

        String path = url.substring("jdbc:sqlite:".length());
        if (path.isBlank() || path.equals(":memory:") || path.contains(":") && path.startsWith("file:")) {
            return;
        }

        File target = new File(path);
        File parent = target.getParentFile();
        if (parent != null && !parent.exists() && !parent.mkdirs()) {
            throw new IllegalStateException("Could not create SQLite data directory: " + parent);
        }
    }
}
