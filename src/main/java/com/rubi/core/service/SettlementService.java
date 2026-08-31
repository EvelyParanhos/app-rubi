package com.rubi.core.service;

import com.rubi.core.domain.*;
import com.rubi.core.repository.TransactionRepository;
import com.rubi.core.repository.TransactionSplitRepository;
import com.rubi.core.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.UUID;

@Service
@RequiredArgsConstructor
public class SettlementService {

    private final TransactionSplitRepository transactionSplitRepository;
    private final TransactionRepository transactionRepository;
    private final UserRepository userRepository;

    public record NetBalanceResult(UUID creditorId, UUID debtorId, BigDecimal netAmount) {}

    @Transactional
    public TransactionSplit createSplit(UUID transactionId, UUID currentUserId, UUID debtorId, BigDecimal amount, String referenceMonth) {
        Transaction transaction = transactionRepository.findById(transactionId)
                .orElseThrow(() -> new IllegalArgumentException("Transaction not found"));

        User creditor = userRepository.findById(currentUserId)
                .orElseThrow(() -> new IllegalArgumentException("Creditor not found"));

        User debtor = userRepository.findById(debtorId)
                .orElseThrow(() -> new IllegalArgumentException("Debtor not found"));

        TransactionSplit split = TransactionSplit.builder()
                .transaction(transaction)
                .creditor(creditor)
                .debtor(debtor)
                .amount(amount)
                .status(SplitStatus.PENDING)
                .referenceMonth(referenceMonth)
                .createdAt(OffsetDateTime.now())
                .build();

        return transactionSplitRepository.save(split);
    }

    public NetBalanceResult getNetBalance(UUID currentUserId, UUID partnerId, String month) {
        BigDecimal balance = transactionSplitRepository.calculateNetBalanceForUser(currentUserId, month);

        if (balance.compareTo(BigDecimal.ZERO) > 0) {
            return new NetBalanceResult(currentUserId, partnerId, balance);
        } else if (balance.compareTo(BigDecimal.ZERO) < 0) {
            return new NetBalanceResult(partnerId, currentUserId, balance.abs());
        } else {
            return new NetBalanceResult(currentUserId, partnerId, BigDecimal.ZERO);
        }
    }

    @Transactional
    public void payNetBalance(UUID currentUserId, String month, UUID sourceAccountId, BigDecimal amount) {
        List<TransactionSplit> pendingSplits = transactionSplitRepository.findByReferenceMonthAndStatus(month, SplitStatus.PENDING);
        OffsetDateTime now = OffsetDateTime.now();
        for (TransactionSplit s : pendingSplits) {
            if (s.getCreditor().getId().equals(currentUserId) || s.getDebtor().getId().equals(currentUserId)) {
                s.setStatus(SplitStatus.SETTLED);
                s.setIsSettled(true);
                s.setSettledAt(now);
                transactionSplitRepository.save(s);
            }
        }
    }
}
