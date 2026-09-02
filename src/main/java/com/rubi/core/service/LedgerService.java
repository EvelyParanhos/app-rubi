package com.rubi.core.service;

import com.rubi.core.domain.*;
import com.rubi.core.repository.AccountRepository;
import com.rubi.core.repository.TransactionRepository;
import com.rubi.core.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.time.YearMonth;
import java.util.List;
import java.util.UUID;

@Service
@RequiredArgsConstructor
public class LedgerService {

    private final AccountRepository accountRepository;
    private final TransactionRepository transactionRepository;
    private final UserRepository userRepository;

    @Transactional
    public Account createAccount(UUID ownerId, String name, String type, BigDecimal initialBalance, BigDecimal goalAmount) {
        User owner = userRepository.findById(ownerId)
                .orElseThrow(() -> new IllegalArgumentException("Owner not found"));

        AccountType accountType = AccountType.valueOf(type.toUpperCase());

        Account account = Account.builder()
                .owner(owner)
                .name(name)
                .type(accountType)
                .goalAmount(goalAmount)
                .isActive(true)
                .createdAt(LocalDateTime.now())
                .build();

        Account savedAccount = accountRepository.save(account);

        if (initialBalance != null && initialBalance.compareTo(BigDecimal.ZERO) > 0) {
            Transaction initialTransaction = Transaction.builder()
                    .account(savedAccount)
                    .sourceAccount(savedAccount)
                    .destAccount(savedAccount)
                    .amount(initialBalance)
                    .type(TransactionType.OPENING_BALANCE)
                    .description("Saldo Inicial")
                    .referenceDate(LocalDateTime.now())
                    .status(TransactionStatus.CONFIRMED)
                    .build();
            transactionRepository.save(initialTransaction);
        }

        return savedAccount;
    }

    public Account createAccount(UUID ownerId, String name, String type, BigDecimal initialBalance) {
        return createAccount(ownerId, name, type, initialBalance, null);
    }

    public Account createAccount(UUID ownerId, String name, String type) {
        return createAccount(ownerId, name, type, BigDecimal.ZERO, null);
    }

    public BigDecimal getAccountBalance(UUID accountId) {
        return transactionRepository.calculateBalance(accountId);
    }

    public BigDecimal getPocketCurrentMonthProgress(UUID accountId) {
        YearMonth nowYm = YearMonth.now();
        LocalDateTime monthStart = nowYm.atDay(1).atStartOfDay();
        LocalDateTime monthEnd = nowYm.atEndOfMonth().atTime(23, 59, 59);

        List<Transaction> txList = transactionRepository.findByAccountIdOrderByReferenceDateDesc(accountId);
        BigDecimal monthCredits = BigDecimal.ZERO;

        for (Transaction tx : txList) {
            if (tx.getStatus() == TransactionStatus.CONFIRMED
                    && (tx.getType() == TransactionType.CREDIT || tx.getType() == TransactionType.OPENING_BALANCE)
                    && tx.getReferenceDate() != null
                    && !tx.getReferenceDate().isBefore(monthStart)
                    && !tx.getReferenceDate().isAfter(monthEnd)) {
                monthCredits = monthCredits.add(tx.getAmount());
            }
        }
        return monthCredits;
    }

    @Transactional
    public void transfer(UUID sourceAccountId, UUID targetAccountId, BigDecimal amount, String description, Category category) {
        if (amount == null || amount.compareTo(BigDecimal.ZERO) <= 0) {
            throw new IllegalArgumentException("Transfer amount must be greater than zero");
        }

        Account sourceAccount = accountRepository.findById(sourceAccountId)
                .orElseThrow(() -> new IllegalArgumentException("Source account not found"));

        Account targetAccount = accountRepository.findById(targetAccountId)
                .orElseThrow(() -> new IllegalArgumentException("Target account not found"));

        // Infer category = INVESTMENTS if transferring to a POCKET account and no category specified
        if (category == null && targetAccount.getType() == AccountType.POCKET) {
            category = Category.INVESTMENTS;
        }

        Transaction debitTransaction = Transaction.builder()
                .account(sourceAccount)
                .sourceAccount(sourceAccount)
                .destAccount(targetAccount)
                .amount(amount)
                .type(TransactionType.DEBIT)
                .description(description)
                .category(category)
                .referenceDate(LocalDateTime.now())
                .status(TransactionStatus.CONFIRMED)
                .build();

        Transaction creditTransaction = Transaction.builder()
                .account(targetAccount)
                .sourceAccount(sourceAccount)
                .destAccount(targetAccount)
                .amount(amount)
                .type(TransactionType.CREDIT)
                .description(description)
                .category(category)
                .referenceDate(LocalDateTime.now())
                .status(TransactionStatus.CONFIRMED)
                .build();

        transactionRepository.save(debitTransaction);
        transactionRepository.save(creditTransaction);
    }

    @Transactional
    public void transfer(UUID sourceAccountId, UUID targetAccountId, BigDecimal amount, String description) {
        transfer(sourceAccountId, targetAccountId, amount, description, null);
    }

    @Transactional
    public Transaction recordTransaction(UUID accountId, BigDecimal amount, String typeStr, String description, Category category, LocalDateTime referenceDate) {
        Account account = accountRepository.findById(accountId)
                .orElseThrow(() -> new IllegalArgumentException("Account not found"));

        TransactionType type = TransactionType.valueOf(typeStr);
        if (referenceDate == null) {
            referenceDate = LocalDateTime.now();
        }

        Transaction transaction = Transaction.builder()
                .account(account)
                .amount(amount)
                .type(type)
                .description(description)
                .category(category)
                .referenceDate(referenceDate)
                .status(TransactionStatus.CONFIRMED)
                .build();

        return transactionRepository.save(transaction);
    }
}
