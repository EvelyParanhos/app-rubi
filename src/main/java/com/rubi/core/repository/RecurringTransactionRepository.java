package com.rubi.core.repository;

import com.rubi.core.domain.RecurringTransaction;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.UUID;

@Repository
public interface RecurringTransactionRepository extends JpaRepository<RecurringTransaction, UUID> {
    List<RecurringTransaction> findByAccountOwnerIdAndIsActiveTrue(UUID ownerId);

    List<RecurringTransaction> findByCreditCardAccountOwnerIdAndIsActiveTrue(UUID ownerId);

    @Query("SELECT r FROM RecurringTransaction r WHERE r.isActive = true AND ((r.account IS NOT NULL AND r.account.owner.id = :ownerId) OR (r.creditCard IS NOT NULL AND r.creditCard.account.owner.id = :ownerId))")
    List<RecurringTransaction> findAllByOwnerIdAndIsActiveTrue(@Param("ownerId") UUID ownerId);

    List<RecurringTransaction> findByIsActiveTrue();
}
