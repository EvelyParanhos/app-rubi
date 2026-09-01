package com.rubi.core.repository;

import com.rubi.core.domain.RecurringOverride;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Repository
public interface RecurringOverrideRepository extends JpaRepository<RecurringOverride, UUID> {

    Optional<RecurringOverride> findByRecurringTransactionIdAndReferenceMonth(UUID recurringTransactionId, String referenceMonth);

    List<RecurringOverride> findByReferenceMonth(String referenceMonth);
}
