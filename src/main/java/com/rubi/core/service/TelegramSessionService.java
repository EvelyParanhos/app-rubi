package com.rubi.core.service;

import com.rubi.core.domain.*;
import com.rubi.core.repository.AccountRepository;
import com.rubi.core.repository.TransactionRepository;
import lombok.Data;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

@Service
@Slf4j
@RequiredArgsConstructor
public class TelegramSessionService {

    public enum OnboardingStep {
        STEP_START,
        STEP_OPENING_BALANCE,
        STEP_CREDIT_CARD,
        STEP_RECURRING_LOOP,
        STEP_COMPLETED
    }

    @Data
    public static class UserSession {
        private String chatId;
        private UUID userId;
        private OnboardingStep step = OnboardingStep.STEP_START;
        private UUID primaryAccountId;
    }

    private final Map<String, UserSession> sessions = new ConcurrentHashMap<>();
    private final LedgerService ledgerService;
    private final AccountRepository accountRepository;
    private final TransactionRepository transactionRepository;

    public UserSession getOrCreateSession(String chatId, UUID userId) {
        return sessions.computeIfAbsent(chatId, k -> {
            UserSession session = new UserSession();
            session.setChatId(chatId);
            session.setUserId(userId);
            return session;
        });
    }

    @Transactional
    public Account processOpeningBalance(String chatId, BigDecimal balance) {
        UserSession session = sessions.get(chatId);
        if (session == null) {
            throw new IllegalStateException("Session not found for chatId: " + chatId);
        }

        // Criar Conta Base
        Account account = ledgerService.createAccount(
                session.getUserId(),
                "Conta Corrente Base",
                "CHECKING",
                false,
                BigDecimal.ZERO
        );

        // Lançamento com tipo OPENING_BALANCE (Épico 4.3 - Sem afetar DRE mensal)
        if (balance != null && balance.compareTo(BigDecimal.ZERO) > 0) {
            Transaction openingBalanceTx = Transaction.builder()
                    .account(account)
                    .amount(balance)
                    .type(TransactionType.OPENING_BALANCE)
                    .description("Saldo Inicial de Abertura")
                    .referenceDate(LocalDateTime.now())
                    .status("CONFIRMED")
                    .build();
            transactionRepository.save(openingBalanceTx);
        }

        session.setPrimaryAccountId(account.getId());
        session.setStep(OnboardingStep.STEP_CREDIT_CARD);
        return account;
    }

    public void advanceStep(String chatId, OnboardingStep nextStep) {
        UserSession session = sessions.get(chatId);
        if (session != null) {
            session.setStep(nextStep);
        }
    }
}
