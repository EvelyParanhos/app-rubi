package com.rubi.core.repository;

import com.rubi.core.domain.Partnership;
import com.rubi.core.domain.PartnershipStatus;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;
import java.util.UUID;

@Repository
public interface PartnershipRepository extends JpaRepository<Partnership, UUID> {

    @Query("SELECT CASE WHEN COUNT(p) > 0 THEN true ELSE false END FROM Partnership p WHERE (p.user1.id = :user1Id OR p.user2.id = :user2Id) AND p.status = :status")
    boolean existsByUser1IdOrUser2IdAndStatus(@Param("user1Id") UUID user1Id, @Param("user2Id") UUID user2Id, @Param("status") PartnershipStatus status);

    @Query("SELECT p FROM Partnership p WHERE (p.user1.id = :userId OR p.user2.id = :userId) AND p.status = :status")
    java.util.Optional<Partnership> findActivePartnership(@Param("userId") UUID userId, @Param("status") PartnershipStatus status);
}
