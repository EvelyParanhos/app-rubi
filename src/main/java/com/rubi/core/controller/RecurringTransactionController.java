package com.rubi.core.controller;

import com.rubi.api.RecurringTransactionsApi;
import com.rubi.core.domain.RecurringTransaction;
import com.rubi.core.service.RecurringTransactionService;
import com.rubi.model.RecurringTransactionCreateRequest;
import com.rubi.model.RecurringTransactionResponse;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.bind.annotation.RestController;

import java.math.BigDecimal;
import java.util.List;
import java.util.UUID;
import java.util.stream.Collectors;

import com.rubi.core.domain.Category;
import com.rubi.model.CategoryEnum;

@RestController
@RequiredArgsConstructor
public class RecurringTransactionController implements RecurringTransactionsApi {

    private final RecurringTransactionService recurringTransactionService;

    @Override
    public ResponseEntity<RecurringTransactionResponse> createRecurringTransaction(RecurringTransactionCreateRequest request) {
        Category domainCategory = request.getCategory() != null ? Category.valueOf(request.getCategory().name()) : Category.UNCATEGORIZED;

        RecurringTransaction rec = recurringTransactionService.createRecurringTransaction(
                request.getAccountId(),
                request.getDescription(),
                BigDecimal.valueOf(request.getAmount()),
                request.getType().name(),
                request.getDueDay(),
                domainCategory
        );

        CategoryEnum catEnum = rec.getCategory() != null ? CategoryEnum.fromValue(rec.getCategory().name()) : CategoryEnum.UNCATEGORIZED;

        RecurringTransactionResponse response = new RecurringTransactionResponse()
                .id(rec.getId())
                .accountId(rec.getAccount() != null ? rec.getAccount().getId() : null)
                .description(rec.getDescription())
                .amount(rec.getAmount().doubleValue())
                .type(rec.getType().name())
                .dueDay(rec.getDueDay())
                .category(catEnum);

        return ResponseEntity.status(HttpStatus.CREATED).body(response);
    }

    @Override
    public ResponseEntity<List<RecurringTransactionResponse>> getRecurringTransactions() {
        UUID userId = getCurrentUserId();
        List<RecurringTransaction> recList = recurringTransactionService.getRecurringTransactions(userId);

        List<RecurringTransactionResponse> responseList = recList.stream()
                .map(r -> {
                    CategoryEnum catEnum = r.getCategory() != null ? CategoryEnum.fromValue(r.getCategory().name()) : CategoryEnum.UNCATEGORIZED;
                    return new RecurringTransactionResponse()
                            .id(r.getId())
                            .accountId(r.getAccount() != null ? r.getAccount().getId() : null)
                            .description(r.getDescription())
                            .amount(r.getAmount().doubleValue())
                            .type(r.getType().name())
                            .dueDay(r.getDueDay())
                            .category(catEnum);
                })
                .collect(Collectors.toList());

        return ResponseEntity.ok(responseList);
    }

    @Override
    public ResponseEntity<Void> deleteRecurringTransaction(UUID id) {
        UUID currentUserId = getCurrentUserId();
        recurringTransactionService.deleteRecurringTransaction(id, currentUserId);
        return ResponseEntity.noContent().build();
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
