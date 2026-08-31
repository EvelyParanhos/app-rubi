package com.rubi.core.repository;

import com.rubi.core.domain.Invoice;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import java.util.Optional;
import java.util.UUID;

import java.util.List;

@Repository
public interface InvoiceRepository extends JpaRepository<Invoice, UUID> {
    Optional<Invoice> findByCreditCardIdAndReferenceMonth(UUID creditCardId, String referenceMonth);
    List<Invoice> findByCreditCardIdOrderByReferenceMonthDesc(UUID creditCardId);
}
