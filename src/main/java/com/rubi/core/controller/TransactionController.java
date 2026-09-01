package com.rubi.core.controller;

import com.rubi.api.TransactionsApi;
import com.rubi.core.domain.Transaction;
import com.rubi.core.repository.TransactionRepository;
import com.rubi.core.service.LedgerService;
import com.rubi.model.TransferRequest;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.bind.annotation.RestController;

import java.math.BigDecimal;
import java.util.UUID;

import com.rubi.core.domain.Category;
import com.rubi.model.CategoryEnum;
import com.rubi.model.TransactionCreateRequest;
import com.rubi.model.TransactionResponse;

import java.time.LocalDateTime;
import java.time.YearMonth;
import java.time.ZoneOffset;
import java.util.List;
import java.util.stream.Collectors;

import org.springframework.transaction.annotation.Transactional;

@RestController
@RequiredArgsConstructor
public class TransactionController implements TransactionsApi {

    private final LedgerService ledgerService;
    private final TransactionRepository transactionRepository;

    @Override
    public ResponseEntity<TransactionResponse> createTransaction(TransactionCreateRequest request) {
        Category domainCategory = request.getCategory() != null ? Category.valueOf(request.getCategory().name()) : Category.UNCATEGORIZED;

        Transaction t = ledgerService.recordTransaction(
                request.getAccountId(),
                BigDecimal.valueOf(request.getAmount()),
                request.getType().name(),
                request.getDescription(),
                domainCategory,
                request.getReferenceDate() != null ? request.getReferenceDate().toLocalDateTime() : LocalDateTime.now()
        );

        return ResponseEntity.status(HttpStatus.CREATED).body(toResponse(t));
    }

    @Override
    public ResponseEntity<List<TransactionResponse>> getTransactions(String month, UUID accountId, CategoryEnum category) {
        UUID currentUserId = getCurrentUserId();
        List<Transaction> list;

        if (accountId != null) {
            list = transactionRepository.findByAccountIdOrderByReferenceDateDesc(accountId);
        } else if (month != null && !month.isBlank()) {
            YearMonth ym = YearMonth.parse(month);
            LocalDateTime start = ym.atDay(1).atStartOfDay();
            LocalDateTime end = ym.atEndOfMonth().atTime(23, 59, 59);
            list = transactionRepository.findByAccountOwnerIdAndReferenceDateBetweenOrderByReferenceDateDesc(currentUserId, start, end);
        } else {
            list = transactionRepository.findByAccountOwnerIdOrderByReferenceDateDesc(currentUserId);
        }

        if (category != null) {
            String catName = category.name();
            list = list.stream()
                    .filter(t -> t.getCategory() != null && t.getCategory().name().equals(catName))
                    .collect(Collectors.toList());
        }

        List<TransactionResponse> responses = list.stream().map(this::toResponse).collect(Collectors.toList());
        return ResponseEntity.ok(responses);
    }

    @Override
    public ResponseEntity<Void> transferFunds(TransferRequest transferRequest) {
        ledgerService.transfer(
                transferRequest.getSourceAccountId(),
                transferRequest.getTargetAccountId(),
                BigDecimal.valueOf(transferRequest.getAmount()),
                transferRequest.getDescription()
        );
        return ResponseEntity.status(HttpStatus.CREATED).build();
    }

    @Override
    @Transactional
    public ResponseEntity<TransactionResponse> updateTransaction(UUID id, TransactionCreateRequest request) {
        UUID currentUserId = getCurrentUserId();
        Transaction transaction = transactionRepository.findById(id)
                .orElseThrow(() -> new IllegalArgumentException("Transaction not found"));

        if (!transaction.getAccount().getOwner().getId().equals(currentUserId)) {
            throw new SecurityException("Forbidden: Transaction does not belong to current user");
        }

        if (request.getAmount() != null) {
            transaction.setAmount(BigDecimal.valueOf(request.getAmount()));
        }
        if (request.getDescription() != null) {
            transaction.setDescription(request.getDescription());
        }
        if (request.getCategory() != null) {
            transaction.setCategory(Category.valueOf(request.getCategory().name()));
        }

        Transaction updated = transactionRepository.save(transaction);
        return ResponseEntity.ok(toResponse(updated));
    }

    @Override
    @Transactional
    public ResponseEntity<Void> deleteTransaction(UUID id) {
        UUID currentUserId = getCurrentUserId();
        Transaction transaction = transactionRepository.findById(id)
                .orElseThrow(() -> new IllegalArgumentException("Transaction not found"));

        if (!transaction.getAccount().getOwner().getId().equals(currentUserId)) {
            throw new SecurityException("Forbidden: Transaction does not belong to current user");
        }

        transactionRepository.delete(transaction);
        return ResponseEntity.noContent().build();
    }

    private TransactionResponse toResponse(Transaction t) {
        CategoryEnum catEnum = null;
        if (t.getCategory() != null) {
            try {
                catEnum = CategoryEnum.fromValue(t.getCategory().name());
            } catch (Exception e) {
                catEnum = CategoryEnum.UNCATEGORIZED;
            }
        }
        return new TransactionResponse()
                .id(t.getId())
                .accountId(t.getAccount().getId())
                .accountName(t.getAccount() != null ? t.getAccount().getName() : null)
                .amount(t.getAmount().doubleValue())
                .type(t.getType().name())
                .description(t.getDescription())
                .category(catEnum)
                .referenceDate(t.getReferenceDate() != null ? t.getReferenceDate().atOffset(ZoneOffset.UTC) : null);
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
