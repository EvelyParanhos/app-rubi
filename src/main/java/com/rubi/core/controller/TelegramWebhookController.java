package com.rubi.core.controller;

import com.rubi.api.WebhookApi;
import com.rubi.core.service.TelegramSessionService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

@RestController
@Slf4j
@RequiredArgsConstructor
public class TelegramWebhookController implements WebhookApi {

    private final TelegramSessionService telegramSessionService;

    @Override
    public ResponseEntity<Void> handleTelegramWebhook(Object body) {
        log.info("[TELEGRAM WEBHOOK] Update recebido: {}", body);
        return ResponseEntity.ok().build();
    }
}
