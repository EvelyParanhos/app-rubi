package com.rubi.core.repository;

import com.rubi.core.domain.RecurringFulfillment;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Repository
public interface RecurringFulfillmentRepository extends JpaRepository<RecurringFulfillment, UUID> {

    Optional<RecurringFulfillment> findByRecurringTransactionIdAndReferenceMonth(UUID recurringTransactionId, String referenceMonth);

    List<RecurringFulfillment> findByReferenceMonth(String referenceMonth);

    List<RecurringFulfillment> findByRecurringTransactionId(UUID recurringTransactionId);
}
