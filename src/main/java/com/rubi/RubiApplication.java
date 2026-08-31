package com.rubi;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication
@EnableScheduling
public class RubiApplication {
    public static void main(String[] args) {
        SpringApplication.run(RubiApplication.class, args);
    }
}
