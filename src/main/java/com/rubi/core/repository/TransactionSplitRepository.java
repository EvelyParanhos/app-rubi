package com.rubi.core.repository;

import com.rubi.core.domain.TransactionSplit;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;
import java.math.BigDecimal;
import java.util.UUID;

import java.util.List;
import com.rubi.core.domain.SplitStatus;

@Repository
public interface TransactionSplitRepository extends JpaRepository<TransactionSplit, UUID> {

    @Query("SELECT COALESCE(SUM(CASE WHEN s.creditor.id = :userId THEN s.amount ELSE -s.amount END), 0) FROM TransactionSplit s WHERE (s.creditor.id = :userId OR s.debtor.id = :userId) AND s.referenceMonth = :month AND s.status = com.rubi.core.domain.SplitStatus.PENDING")
    BigDecimal calculateNetBalanceForUser(@Param("userId") UUID userId, @Param("month") String month);

    List<TransactionSplit> findByReferenceMonthAndStatus(String referenceMonth, SplitStatus status);

    List<TransactionSplit> findByTransactionId(UUID transactionId);

    void deleteByTransactionId(UUID transactionId);
}
