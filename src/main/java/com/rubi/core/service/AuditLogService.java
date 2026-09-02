package com.rubi.core.service;

import com.rubi.core.domain.AuditLog;
import com.rubi.core.repository.AuditLogRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.UUID;

@Service
@Slf4j
@RequiredArgsConstructor
public class AuditLogService {

    private final AuditLogRepository auditLogRepository;

    @Transactional(propagation = Propagation.REQUIRES_NEW)
    public void logAction(UUID userId, String entityName, UUID entityId, String action, String details) {
        try {
            AuditLog auditLog = AuditLog.builder()
                    .userId(userId)
                    .entityName(entityName)
                    .entityId(entityId != null ? entityId : UUID.nameUUIDFromBytes((entityName + action).getBytes()))
                    .action(action)
                    .details(details)
                    .createdAt(LocalDateTime.now())
                    .build();

            auditLogRepository.save(auditLog);
            log.info("[AUDIT_LOG] User: {}, Entity: {}, ID: {}, Action: {}, Details: {}", userId, entityName, entityId, action, details);
        } catch (Exception e) {
            log.error("[AUDIT_LOG_ERROR] Failed to save audit log: {}", e.getMessage(), e);
        }
    }
}
