package com.rubi.core.scheduler;

import com.rubi.core.domain.*;
import com.rubi.core.repository.RecurringTransactionRepository;
import com.rubi.core.service.AuditLogService;
import com.rubi.core.service.RecurringTransactionService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

import java.time.YearMonth;
import java.util.List;
import java.util.UUID;

@Component
@Slf4j
@RequiredArgsConstructor
public class RecurringTransactionScheduler {

    private final RecurringTransactionRepository recurringTransactionRepository;
    private final RecurringTransactionService recurringTransactionService;
    private final AuditLogService auditLogService;

    private static final int MAX_RETRIES = 3;

    /**
     * Roda no 1º dia de cada mês às 00:00:00 (RN10 / Épico 5.4)
     * Materializa Salários (INCOME) e Gastos Fixos (EXPENSE) com retentativas, DLQ logging,
     * registro de RecurringFulfillment e vínculo correto com Faturas de Cartão (Invoice).
     */
    @Scheduled(cron = "0 0 0 1 * ?")
    @Transactional
    public void materializeRecurringTransactions() {
        log.info("[CRON JOB RECORRÊNCIAS] Iniciando materialização mensal de transações recorrentes...");
        List<RecurringTransaction> activeList = recurringTransactionRepository.findByIsActiveTrue();

        String currentMonthStr = YearMonth.now().toString();
        int successCount = 0;
        int failureCount = 0;

        for (RecurringTransaction rec : activeList) {
            boolean processed = false;
            int attempt = 0;
            Exception lastException = null;

            UUID ownerId = rec.getAccount() != null ? rec.getAccount().getOwner().getId() :
                    (rec.getCreditCard() != null ? rec.getCreditCard().getAccount().getOwner().getId() : null);

            if (ownerId == null) {
                log.warn("[CRON JOB RECORRÊNCIAS] Ignorando recorrente sem proprietário ID: {}", rec.getId());
                continue;
            }

            while (!processed && attempt < MAX_RETRIES) {
                attempt++;
                try {
                    Transaction tx = recurringTransactionService.fulfillRecurring(
                            rec.getId(),
                            ownerId,
                            currentMonthStr,
                            null,
                            null,
                            null
                    );

                    processed = true;
                    successCount++;
                    log.info("[CRON JOB RECORRÊNCIAS] Materializada/Cumprida recorrente (Tentativa {}): {} (R$ {}) [Tx ID: {}]",
                            attempt, rec.getDescription(), rec.getAmount(), tx.getId());
                } catch (Exception e) {
                    lastException = e;
                    log.warn("[CRON JOB RECORRÊNCIAS] Tentativa {} falhou para recorrente ID {}: {}",
                            attempt, rec.getId(), e.getMessage());
                    try {
                        Thread.sleep(100L * attempt);
                    } catch (InterruptedException ignored) {}
                }
            }

            if (!processed) {
                failureCount++;
                String errMsg = lastException != null ? lastException.getMessage() : "Unknown error";
                log.error("CRITICAL_SCHEDULER_ALERT: Falha ao materializar recorrente ID {} após {} tentativas. Erro: {}",
                        rec.getId(), MAX_RETRIES, errMsg);

                auditLogService.logAction(
                        ownerId,
                        "RecurringTransaction",
                        rec.getId(),
                        "DLQ_RECURRING_FAILURE",
                        "Falha na materialização mensal após 3 tentativas. Erro: " + errMsg
                );
            }
        }

        log.info("[CRON JOB RECORRÊNCIAS] Concluída materialização. Sucesso: {}, Falhas/DLQ: {}", successCount, failureCount);
    }
}
