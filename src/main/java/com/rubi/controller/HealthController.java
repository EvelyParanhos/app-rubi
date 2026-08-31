package com.rubi.controller;

import com.rubi.api.DefaultApi;
import com.rubi.model.HealthStatus;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequiredArgsConstructor
public class HealthController implements DefaultApi {

    private final JdbcTemplate jdbcTemplate;

    @Override
    public ResponseEntity<HealthStatus> getHealth() {
        try {
            jdbcTemplate.queryForObject("SELECT 1", Integer.class);
            return ResponseEntity.ok(new HealthStatus("Rubi Core Ativo - Banco Conectado"));
        } catch (Exception e) {
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                    .body(new HealthStatus("Erro de conexao com o banco: " + e.getMessage()));
        }
    }
}
