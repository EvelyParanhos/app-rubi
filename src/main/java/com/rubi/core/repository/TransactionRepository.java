package com.rubi.core.repository;

import com.rubi.core.domain.Transaction;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;
import java.math.BigDecimal;
import java.util.UUID;

import java.time.LocalDateTime;
import java.util.List;

@Repository
public interface TransactionRepository extends JpaRepository<Transaction, UUID> {

    @Query("SELECT COALESCE(SUM(CASE WHEN t.type = com.rubi.core.domain.TransactionType.CREDIT THEN t.amount ELSE -t.amount END), 0) FROM Transaction t WHERE t.account.id = :accountId")
    BigDecimal calculateBalance(@Param("accountId") UUID accountId);

    @Query("SELECT COALESCE(SUM(CASE WHEN t.type = com.rubi.core.domain.TransactionType.DEBIT THEN t.amount ELSE -t.amount END), 0) FROM Transaction t WHERE t.invoice.id = :invoiceId")
    BigDecimal sumAmountByInvoiceId(@Param("invoiceId") UUID invoiceId);

    List<Transaction> findByAccountOwnerIdOrderByReferenceDateDesc(UUID ownerId);

    List<Transaction> findByAccountOwnerIdAndReferenceDateBetweenOrderByReferenceDateDesc(UUID ownerId, LocalDateTime start, LocalDateTime end);

    List<Transaction> findByAccountIdOrderByReferenceDateDesc(UUID accountId);

    List<Transaction> findByInvoiceIdOrderByReferenceDateDesc(UUID invoiceId);
}
