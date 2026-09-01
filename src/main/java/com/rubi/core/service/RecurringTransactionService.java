package com.rubi.core.service;

import com.rubi.core.domain.*;
import com.rubi.core.repository.*;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Service
@RequiredArgsConstructor
public class RecurringTransactionService {

    private final RecurringTransactionRepository recurringTransactionRepository;
    private final RecurringFulfillmentRepository recurringFulfillmentRepository;
    private final RecurringOverrideRepository recurringOverrideRepository;
    private final AccountRepository accountRepository;
    private final LedgerService ledgerService;

    @Transactional
    public RecurringTransaction createRecurringTransaction(UUID accountId, String description, BigDecimal amount, String type, int dueDay, Category category) {
        Account account = accountRepository.findById(accountId)
                .orElseThrow(() -> new IllegalArgumentException("Account not found"));

        RecurringTransactionType transactionType = RecurringTransactionType.valueOf(type.toUpperCase());

        RecurringTransaction recurringTransaction = RecurringTransaction.builder()
                .account(account)
                .description(description)
                .amount(amount)
                .type(transactionType)
                .dueDay(dueDay)
                .category(category)
                .isActive(true)
                .createdAt(LocalDateTime.now())
                .build();

        return recurringTransactionRepository.save(recurringTransaction);
    }

    @Transactional
    public RecurringTransaction createRecurringTransaction(UUID accountId, String description, BigDecimal amount, String type, int dueDay) {
        return createRecurringTransaction(accountId, description, amount, type, dueDay, Category.UNCATEGORIZED);
    }

    public List<RecurringTransaction> getRecurringTransactions(UUID userId) {
        return recurringTransactionRepository.findByAccountOwnerIdAndIsActiveTrue(userId);
    }

    @Transactional
    public Transaction fulfillRecurring(UUID id, UUID currentUserId, String referenceMonth, UUID targetAccountId, BigDecimal customAmount, OffsetDateTime executionDate) {
        RecurringTransaction rec = recurringTransactionRepository.findById(id)
                .orElseThrow(() -> new IllegalArgumentException("Recurring transaction not found"));

        if (!rec.getAccount().getOwner().getId().equals(currentUserId)) {
            throw new SecurityException("Forbidden: Recurring transaction does not belong to current user");
        }

        Optional<RecurringFulfillment> existingFulfillment = recurringFulfillmentRepository
                .findByRecurringTransactionIdAndReferenceMonth(id, referenceMonth);
        if (existingFulfillment.isPresent()) {
            return existingFulfillment.get().getTransaction();
        }

        UUID accId = targetAccountId != null ? targetAccountId : rec.getAccount().getId();
        BigDecimal amt = customAmount;
        if (amt == null) {
            Optional<RecurringOverride> overrideOpt = recurringOverrideRepository
                    .findByRecurringTransactionIdAndReferenceMonth(id, referenceMonth);
            amt = overrideOpt.isPresent() ? overrideOpt.get().getOverrideAmount() : rec.getAmount();
        }

        LocalDateTime refDate = executionDate != null ? executionDate.toLocalDateTime() : LocalDateTime.now();
        String txTypeStr = rec.getType() == RecurringTransactionType.INCOME ? "CREDIT" : "DEBIT";

        Transaction tx = ledgerService.recordTransaction(
                accId,
                amt,
                txTypeStr,
                "[Recorrente " + referenceMonth + "] " + rec.getDescription(),
                rec.getCategory(),
                refDate
        );

        RecurringFulfillment fulfillment = RecurringFulfillment.builder()
                .recurringTransaction(rec)
                .transaction(tx)
                .referenceMonth(referenceMonth)
                .fulfilledAt(LocalDateTime.now())
                .build();

        recurringFulfillmentRepository.save(fulfillment);
        return tx;
    }

    @Transactional
    public void overrideRecurring(UUID id, UUID currentUserId, String referenceMonth, BigDecimal overrideAmount, Integer overrideDueDay) {
        RecurringTransaction rec = recurringTransactionRepository.findById(id)
                .orElseThrow(() -> new IllegalArgumentException("Recurring transaction not found"));

        if (!rec.getAccount().getOwner().getId().equals(currentUserId)) {
            throw new SecurityException("Forbidden: Recurring transaction does not belong to current user");
        }

        RecurringOverride override = recurringOverrideRepository
                .findByRecurringTransactionIdAndReferenceMonth(id, referenceMonth)
                .orElseGet(() -> RecurringOverride.builder()
                        .recurringTransaction(rec)
                        .referenceMonth(referenceMonth)
                        .createdAt(LocalDateTime.now())
                        .build());

        override.setOverrideAmount(overrideAmount);
        if (overrideDueDay != null) {
            override.setOverrideDueDay(overrideDueDay);
        }

        recurringOverrideRepository.save(override);
    }

    @Transactional
    public void deleteRecurringTransaction(UUID id, UUID currentUserId) {
        RecurringTransaction rec = recurringTransactionRepository.findById(id)
                .orElseThrow(() -> new IllegalArgumentException("Recurring transaction not found"));

        if (!rec.getAccount().getOwner().getId().equals(currentUserId)) {
            throw new SecurityException("Forbidden: Recurring transaction does not belong to current user");
        }

        rec.setIsActive(false);
        recurringTransactionRepository.save(rec);
    }
}
