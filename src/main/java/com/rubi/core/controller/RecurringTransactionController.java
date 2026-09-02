package com.rubi.core.controller;

import com.rubi.api.RecurringTransactionsApi;
import com.rubi.core.domain.Category;
import com.rubi.core.domain.RecurringTransaction;
import com.rubi.core.domain.Transaction;
import com.rubi.core.service.RecurringTransactionService;
import com.rubi.model.*;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.bind.annotation.RestController;

import java.math.BigDecimal;
import java.time.ZoneOffset;
import java.util.List;
import java.util.UUID;
import java.util.stream.Collectors;

@RestController
@RequiredArgsConstructor
public class RecurringTransactionController implements RecurringTransactionsApi {

    private final RecurringTransactionService recurringTransactionService;

    @Override
    public ResponseEntity<RecurringTransactionResponse> createRecurringTransaction(RecurringTransactionCreateRequest request) {
        Category domainCategory = request.getCategory() != null ? Category.valueOf(request.getCategory().name()) : Category.UNCATEGORIZED;

        RecurringTransaction rec = recurringTransactionService.createRecurringTransaction(
                request.getAccountId(),
                request.getCreditCardId(),
                request.getDescription(),
                BigDecimal.valueOf(request.getAmount()),
                request.getType().name(),
                request.getDueDay(),
                domainCategory
        );

        return ResponseEntity.status(HttpStatus.CREATED).body(toResponse(rec));
    }

    @Override
    public ResponseEntity<RecurringTransactionResponse> updateRecurringTransaction(UUID id, RecurringTransactionCreateRequest request) {
        UUID currentUserId = getCurrentUserId();
        Category domainCategory = request.getCategory() != null ? Category.valueOf(request.getCategory().name()) : Category.UNCATEGORIZED;

        BigDecimal amt = request.getAmount() != null ? BigDecimal.valueOf(request.getAmount()) : null;

        RecurringTransaction updated = recurringTransactionService.updateRecurringTransaction(
                id,
                currentUserId,
                request.getAccountId(),
                request.getCreditCardId(),
                request.getDescription(),
                amt,
                request.getType() != null ? request.getType().name() : null,
                request.getDueDay() != null ? request.getDueDay() : 0,
                domainCategory
        );

        return ResponseEntity.ok(toResponse(updated));
    }

    @Override
    public ResponseEntity<List<RecurringTransactionResponse>> getRecurringTransactions() {
        UUID userId = getCurrentUserId();
        List<RecurringTransaction> recList = recurringTransactionService.getRecurringTransactions(userId);

        List<RecurringTransactionResponse> responseList = recList.stream()
                .map(this::toResponse)
                .collect(Collectors.toList());

        return ResponseEntity.ok(responseList);
    }

    @Override
    public ResponseEntity<TransactionResponse> fulfillRecurringTransaction(UUID id, FulfillRecurringRequest request) {
        UUID currentUserId = getCurrentUserId();

        BigDecimal customAmt = request.getAmount() != null ? BigDecimal.valueOf(request.getAmount()) : null;

        Transaction tx = recurringTransactionService.fulfillRecurring(
                id,
                currentUserId,
                request.getReferenceMonth(),
                request.getAccountId(),
                customAmt,
                request.getExecutionDate()
        );

        CategoryEnum catEnum = null;
        if (tx.getCategory() != null) {
            try {
                catEnum = CategoryEnum.fromValue(tx.getCategory().name());
            } catch (Exception e) {
                catEnum = CategoryEnum.UNCATEGORIZED;
            }
        }

        TransactionResponse txResponse = new TransactionResponse()
                .id(tx.getId())
                .accountId(tx.getAccount() != null ? tx.getAccount().getId() : null)
                .accountName(tx.getAccount() != null ? tx.getAccount().getName() : null)
                .amount(tx.getAmount().doubleValue())
                .type(tx.getType().name())
                .description(tx.getDescription())
                .category(catEnum)
                .referenceDate(tx.getReferenceDate() != null ? tx.getReferenceDate().atOffset(ZoneOffset.UTC) : null);

        return ResponseEntity.status(HttpStatus.CREATED).body(txResponse);
    }

    @Override
    public ResponseEntity<Void> overrideRecurringTransaction(UUID id, OverrideRecurringRequest request) {
        UUID currentUserId = getCurrentUserId();

        BigDecimal overrideAmt = BigDecimal.valueOf(request.getOverrideAmount());

        recurringTransactionService.overrideRecurring(
                id,
                currentUserId,
                request.getReferenceMonth(),
                overrideAmt,
                request.getOverrideDueDay()
        );

        return ResponseEntity.ok().build();
    }

    @Override
    public ResponseEntity<Void> deleteRecurringTransaction(UUID id) {
        UUID currentUserId = getCurrentUserId();
        recurringTransactionService.deleteRecurringTransaction(id, currentUserId);
        return ResponseEntity.noContent().build();
    }

    private RecurringTransactionResponse toResponse(RecurringTransaction r) {
        CategoryEnum catEnum = r.getCategory() != null ? CategoryEnum.fromValue(r.getCategory().name()) : CategoryEnum.UNCATEGORIZED;
        return new RecurringTransactionResponse()
                .id(r.getId())
                .accountId(r.getAccount() != null ? r.getAccount().getId() : null)
                .creditCardId(r.getCreditCard() != null ? r.getCreditCard().getId() : null)
                .creditCardName(r.getCreditCard() != null ? r.getCreditCard().getName() : null)
                .description(r.getDescription())
                .amount(r.getAmount().doubleValue())
                .type(r.getType().name())
                .dueDay(r.getDueDay())
                .category(catEnum);
    }

    private UUID getCurrentUserId() {
        Authentication auth = SecurityContextHolder.getContext().getAuthentication();
        if (auth != null && auth.isAuthenticated() && !"anonymousUser".equals(auth.getName())) {
            Object principal = auth.getPrincipal();
            if (principal instanceof UUID) {
                return (UUID) principal;
            }
            return UUID.fromString(principal.toString());
        }
        throw new SecurityException("Unauthorized");
    }
}
