package com.rubi.core.controller;

import com.rubi.api.AccountsApi;
import com.rubi.core.domain.Account;
import com.rubi.core.domain.AccountType;
import com.rubi.core.repository.AccountRepository;
import com.rubi.core.service.LedgerService;
import com.rubi.model.AccountCreateRequest;
import com.rubi.model.AccountCreateResponse;
import com.rubi.model.AccountResponse;
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

@RestController
@RequiredArgsConstructor
public class AccountController implements AccountsApi {

    private final LedgerService ledgerService;
    private final AccountRepository accountRepository;

    @Override
    public ResponseEntity<AccountCreateResponse> createAccount(AccountCreateRequest accountCreateRequest) {
        UUID ownerId = getCurrentUserId();

        BigDecimal initialBalance = accountCreateRequest.getInitialBalance() != null ?
                BigDecimal.valueOf(accountCreateRequest.getInitialBalance()) : BigDecimal.ZERO;

        BigDecimal goalAmount = accountCreateRequest.getGoalAmount() != null ?
                BigDecimal.valueOf(accountCreateRequest.getGoalAmount()) : null;

        Account account = ledgerService.createAccount(
                ownerId,
                accountCreateRequest.getName(),
                accountCreateRequest.getType().name(),
                initialBalance,
                goalAmount
        );

        AccountCreateResponse response = new AccountCreateResponse()
                .id(account.getId());

        return ResponseEntity.status(HttpStatus.CREATED).body(response);
    }

    @Override
    public ResponseEntity<List<AccountResponse>> getAccounts() {
        UUID ownerId = getCurrentUserId();
        List<Account> accounts = accountRepository.findByOwnerIdAndIsActiveTrue(ownerId);

        List<AccountResponse> responseList = accounts.stream()
                .map(a -> {
                    BigDecimal bal = ledgerService.getAccountBalance(a.getId());
                    Double progress = null;
                    if (a.getType() == AccountType.POCKET) {
                        BigDecimal monthCredits = ledgerService.getPocketCurrentMonthProgress(a.getId());
                        progress = monthCredits != null ? monthCredits.doubleValue() : 0.0;
                    }

                    return new AccountResponse()
                            .id(a.getId())
                            .name(a.getName())
                            .type(a.getType().name())
                            .balance(bal != null ? bal.doubleValue() : 0.0)
                            .goalAmount(a.getGoalAmount() != null ? a.getGoalAmount().doubleValue() : null)
                            .currentMonthProgress(progress);
                })
                .collect(Collectors.toList());

        return ResponseEntity.ok(responseList);
    }

    @Override
    public ResponseEntity<Void> updateAccount(UUID id, AccountCreateRequest accountCreateRequest) {
        UUID currentUserId = getCurrentUserId();
        Account account = accountRepository.findById(id)
                .orElseThrow(() -> new IllegalArgumentException("Account not found"));

        if (!account.getOwner().getId().equals(currentUserId)) {
            throw new SecurityException("Forbidden: Account does not belong to current user");
        }

        account.setName(accountCreateRequest.getName());
        account.setType(AccountType.valueOf(accountCreateRequest.getType().name()));
        if (accountCreateRequest.getGoalAmount() != null) {
            account.setGoalAmount(BigDecimal.valueOf(accountCreateRequest.getGoalAmount()));
        } else {
            account.setGoalAmount(null);
        }

        accountRepository.save(account);
        return ResponseEntity.ok().build();
    }

    @Override
    public ResponseEntity<Void> deleteAccount(UUID id) {
        UUID currentUserId = getCurrentUserId();
        Account account = accountRepository.findById(id)
                .orElseThrow(() -> new IllegalArgumentException("Account not found"));

        if (!account.getOwner().getId().equals(currentUserId)) {
            throw new SecurityException("Forbidden: Account does not belong to current user");
        }

        account.setIsActive(false); // Soft Delete
        accountRepository.save(account);
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
