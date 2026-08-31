package com.rubi.core.service;

import com.rubi.core.domain.Account;
import com.rubi.core.domain.RecurringTransaction;
import com.rubi.core.domain.RecurringTransactionType;
import com.rubi.core.repository.AccountRepository;
import com.rubi.core.repository.RecurringTransactionRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;
import java.util.UUID;

import com.rubi.core.domain.Category;

@Service
@RequiredArgsConstructor
public class RecurringTransactionService {

    private final RecurringTransactionRepository recurringTransactionRepository;
    private final AccountRepository accountRepository;

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
