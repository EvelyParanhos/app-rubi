package com.rubi.core.scheduler;

import com.rubi.core.domain.RecurringTransaction;
import com.rubi.core.domain.RecurringTransactionType;
import com.rubi.core.domain.Transaction;
import com.rubi.core.domain.TransactionType;
import com.rubi.core.repository.RecurringTransactionRepository;
import com.rubi.core.repository.TransactionRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;

@Component
@Slf4j
@RequiredArgsConstructor
public class RecurringTransactionScheduler {

    private final RecurringTransactionRepository recurringTransactionRepository;
    private final TransactionRepository transactionRepository;

    /**
     * Roda no 1º dia de cada mês às 00:00:00 (RN10 / Épico 5.4)
     * Materializa Salários (INCOME) e Gastos Fixos (EXPENSE) com status PENDING_ADJUSTMENT.
     */
    @Scheduled(cron = "0 0 0 1 * ?")
    @Transactional
    public void materializeRecurringTransactions() {
        log.info("[CRON JOB RECORRÊNCIAS] Iniciando materialização mensal de transações recorrentes...");
        List<RecurringTransaction> activeList = recurringTransactionRepository.findByIsActiveTrue();

        for (RecurringTransaction rec : activeList) {
            TransactionType txType = rec.getType() == RecurringTransactionType.INCOME ?
                    TransactionType.CREDIT : TransactionType.DEBIT;

            Transaction tx = Transaction.builder()
                    .account(rec.getAccount())
                    .amount(rec.getAmount())
                    .type(txType)
                    .description("[Recorrente] " + rec.getDescription())
                    .category(rec.getCategory())
                    .referenceDate(LocalDateTime.now())
                    .status("PENDING_ADJUSTMENT")
                    .build();

            transactionRepository.save(tx);
            log.info("[CRON JOB RECORRÊNCIAS] Materializada transação recorrente: {} (R$ {}) para conta {}",
                    rec.getDescription(), rec.getAmount(), rec.getAccount().getId());
        }

        log.info("[CRON JOB RECORRÊNCIAS] Concluída materialização de {} transações recorrentes.", activeList.size());
    }
}
