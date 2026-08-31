package com.rubi.core.repository;

import com.rubi.core.domain.RecurringTransaction;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.UUID;

@Repository
public interface RecurringTransactionRepository extends JpaRepository<RecurringTransaction, UUID> {
    List<RecurringTransaction> findByAccountOwnerIdAndIsActiveTrue(UUID ownerId);
    List<RecurringTransaction> findByIsActiveTrue();
}
