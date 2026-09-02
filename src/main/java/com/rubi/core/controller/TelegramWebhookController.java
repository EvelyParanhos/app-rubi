package com.rubi.core.controller;

import com.rubi.api.WebhookApi;
import com.rubi.core.service.AuditLogService;
import com.rubi.core.service.TelegramSessionService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.RestController;

import java.util.UUID;

@RestController
@Slf4j
@RequiredArgsConstructor
public class TelegramWebhookController implements WebhookApi {

    private final TelegramSessionService telegramSessionService;
    private final AuditLogService auditLogService;

    @Override
    public ResponseEntity<Void> handleTelegramWebhook(Object body) {
        log.info("[TELEGRAM WEBHOOK] Update recebido: {}", body);
        auditLogService.logAction(null, "TelegramWebhook", UUID.nameUUIDFromBytes(body.toString().getBytes()), "TELEGRAM_INPUT", body.toString());
        return ResponseEntity.ok().build();
    }
}
