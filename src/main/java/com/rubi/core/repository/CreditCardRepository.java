package com.rubi.core.repository;

import com.rubi.core.domain.CreditCard;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.UUID;

@Repository
public interface CreditCardRepository extends JpaRepository<CreditCard, UUID> {
    List<CreditCard> findByAccountOwnerIdAndIsActiveTrue(UUID ownerId);
}
