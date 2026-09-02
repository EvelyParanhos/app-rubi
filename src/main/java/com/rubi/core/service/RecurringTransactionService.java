package com.rubi.core.service;

import com.rubi.core.domain.*;
import com.rubi.core.repository.*;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
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
    private final CreditCardRepository creditCardRepository;
    private final LedgerService ledgerService;
    private final CreditCardService creditCardService;
    private final AuditLogService auditLogService;

    @Transactional
    public RecurringTransaction createRecurringTransaction(UUID accountId, UUID creditCardId, String description, BigDecimal amount, String type, int dueDay, Category category) {
        Account account = null;
        if (accountId != null) {
            account = accountRepository.findById(accountId)
                    .orElseThrow(() -> new IllegalArgumentException("Account not found"));
        }

        CreditCard creditCard = null;
        if (creditCardId != null) {
            creditCard = creditCardRepository.findById(creditCardId)
                    .orElseThrow(() -> new IllegalArgumentException("Credit card not found"));
        }

        if (account == null && creditCard == null) {
            throw new IllegalArgumentException("Either accountId or creditCardId must be specified");
        }

        RecurringTransactionType transactionType = RecurringTransactionType.valueOf(type.toUpperCase());

        RecurringTransaction recurringTransaction = RecurringTransaction.builder()
                .account(account)
                .creditCard(creditCard)
                .description(description)
                .amount(amount)
                .type(transactionType)
                .dueDay(dueDay)
                .category(category)
                .isActive(true)
                .createdAt(LocalDateTime.now())
                .build();

        RecurringTransaction saved = recurringTransactionRepository.save(recurringTransaction);

        UUID ownerId = account != null ? account.getOwner().getId() : creditCard.getAccount().getOwner().getId();
        auditLogService.logAction(ownerId, "RecurringTransaction", saved.getId(), "CREATE_RECURRING", "Description: " + description + ", Amount: " + amount);

        return saved;
    }

    @Transactional
    public RecurringTransaction createRecurringTransaction(UUID accountId, String description, BigDecimal amount, String type, int dueDay) {
        return createRecurringTransaction(accountId, null, description, amount, type, dueDay, Category.UNCATEGORIZED);
    }

    @Transactional
    public RecurringTransaction updateRecurringTransaction(UUID id, UUID currentUserId, UUID accountId, UUID creditCardId, String description, BigDecimal amount, String type, int dueDay, Category category) {
        RecurringTransaction rec = recurringTransactionRepository.findById(id)
                .orElseThrow(() -> new IllegalArgumentException("Recurring transaction not found"));

        UUID ownerId = rec.getAccount() != null ? rec.getAccount().getOwner().getId() :
                (rec.getCreditCard() != null ? rec.getCreditCard().getAccount().getOwner().getId() : null);

        if (ownerId != null && !ownerId.equals(currentUserId)) {
            throw new SecurityException("Forbidden: Recurring transaction does not belong to current user");
        }

        if (accountId != null) {
            Account account = accountRepository.findById(accountId)
                    .orElseThrow(() -> new IllegalArgumentException("Account not found"));
            rec.setAccount(account);
            rec.setCreditCard(null);
        } else if (creditCardId != null) {
            CreditCard creditCard = creditCardRepository.findById(creditCardId)
                    .orElseThrow(() -> new IllegalArgumentException("Credit card not found"));
            rec.setCreditCard(creditCard);
            rec.setAccount(null);
        }

        if (description != null) rec.setDescription(description);
        if (amount != null) rec.setAmount(amount);
        if (type != null) rec.setType(RecurringTransactionType.valueOf(type.toUpperCase()));
        if (dueDay > 0) rec.setDueDay(dueDay);
        if (category != null) rec.setCategory(category);

        RecurringTransaction updated = recurringTransactionRepository.save(rec);
        auditLogService.logAction(currentUserId, "RecurringTransaction", updated.getId(), "UPDATE_MASTER_RECURRING", "Master rule updated: " + description);
        return updated;
    }

    public List<RecurringTransaction> getRecurringTransactions(UUID userId) {
        List<RecurringTransaction> list = recurringTransactionRepository.findByAccountOwnerIdAndIsActiveTrue(userId);
        List<RecurringTransaction> cardList = recurringTransactionRepository.findByCreditCardAccountOwnerIdAndIsActiveTrue(userId);

        for (RecurringTransaction cardRec : cardList) {
            if (!list.contains(cardRec)) {
                list.add(cardRec);
            }
        }
        return list;
    }

    @Transactional
    public Transaction fulfillRecurring(UUID id, UUID currentUserId, String referenceMonth, UUID targetAccountId, BigDecimal customAmount, OffsetDateTime executionDate) {
        RecurringTransaction rec = recurringTransactionRepository.findById(id)
                .orElseThrow(() -> new IllegalArgumentException("Recurring transaction not found"));

        UUID ownerId = rec.getAccount() != null ? rec.getAccount().getOwner().getId() :
                (rec.getCreditCard() != null ? rec.getCreditCard().getAccount().getOwner().getId() : null);

        if (ownerId != null && !ownerId.equals(currentUserId)) {
            throw new SecurityException("Forbidden: Recurring transaction does not belong to current user");
        }

        Optional<RecurringFulfillment> existingFulfillment = recurringFulfillmentRepository
                .findByRecurringTransactionIdAndReferenceMonth(id, referenceMonth);
        if (existingFulfillment.isPresent()) {
            return existingFulfillment.get().getTransaction();
        }

        BigDecimal amt = customAmount;
        if (amt == null) {
            Optional<RecurringOverride> overrideOpt = recurringOverrideRepository
                    .findByRecurringTransactionIdAndReferenceMonth(id, referenceMonth);
            amt = overrideOpt.isPresent() ? overrideOpt.get().getOverrideAmount() : rec.getAmount();
        }

        Transaction tx;
        if (rec.getCreditCard() != null) {
            OffsetDateTime pDate = executionDate != null ? executionDate : OffsetDateTime.now(ZoneOffset.UTC);
            tx = creditCardService.processPurchase(
                    rec.getCreditCard().getId(),
                    amt,
                    "[Recorrente " + referenceMonth + "] " + rec.getDescription(),
                    rec.getCategory(),
                    1,
                    pDate
            );
        } else {
            UUID accId = targetAccountId != null ? targetAccountId : rec.getAccount().getId();
            LocalDateTime refDate = executionDate != null ? executionDate.toLocalDateTime() : LocalDateTime.now();
            String txTypeStr = rec.getType() == RecurringTransactionType.INCOME ? "CREDIT" : "DEBIT";

            tx = ledgerService.recordTransaction(
                    accId,
                    amt,
                    txTypeStr,
                    "[Recorrente " + referenceMonth + "] " + rec.getDescription(),
                    rec.getCategory(),
                    refDate
            );
        }

        RecurringFulfillment fulfillment = RecurringFulfillment.builder()
                .recurringTransaction(rec)
                .transaction(tx)
                .referenceMonth(referenceMonth)
                .fulfilledAt(LocalDateTime.now())
                .build();

        recurringFulfillmentRepository.save(fulfillment);
        auditLogService.logAction(currentUserId, "RecurringFulfillment", rec.getId(), "FULFILL_RECURRING", "Fulfilled for month " + referenceMonth + " Amount: R$ " + amt);
        return tx;
    }

    @Transactional
    public void overrideRecurring(UUID id, UUID currentUserId, String referenceMonth, BigDecimal overrideAmount, Integer overrideDueDay) {
        RecurringTransaction rec = recurringTransactionRepository.findById(id)
                .orElseThrow(() -> new IllegalArgumentException("Recurring transaction not found"));

        UUID ownerId = rec.getAccount() != null ? rec.getAccount().getOwner().getId() :
                (rec.getCreditCard() != null ? rec.getCreditCard().getAccount().getOwner().getId() : null);

        if (ownerId != null && !ownerId.equals(currentUserId)) {
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
        auditLogService.logAction(currentUserId, "RecurringOverride", rec.getId(), "OVERRIDE_RECURRING", "Overridden month " + referenceMonth + " Amount: R$ " + overrideAmount);
    }

    @Transactional
    public void deleteRecurringTransaction(UUID id, UUID currentUserId) {
        RecurringTransaction rec = recurringTransactionRepository.findById(id)
                .orElseThrow(() -> new IllegalArgumentException("Recurring transaction not found"));

        UUID ownerId = rec.getAccount() != null ? rec.getAccount().getOwner().getId() :
                (rec.getCreditCard() != null ? rec.getCreditCard().getAccount().getOwner().getId() : null);

        if (ownerId != null && !ownerId.equals(currentUserId)) {
            throw new SecurityException("Forbidden: Recurring transaction does not belong to current user");
        }

        rec.setIsActive(false);
        recurringTransactionRepository.save(rec);
        auditLogService.logAction(currentUserId, "RecurringTransaction", id, "DELETE_RECURRING", "Soft deleted recurring rule: " + rec.getDescription());
    }
}
