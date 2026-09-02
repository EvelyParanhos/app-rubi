package com.rubi.core.repository;

import com.rubi.core.domain.Category;
import com.rubi.core.domain.CategoryBudget;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Repository
public interface CategoryBudgetRepository extends JpaRepository<CategoryBudget, UUID> {

    List<CategoryBudget> findByOwnerId(UUID ownerId);

    Optional<CategoryBudget> findByOwnerIdAndCategory(UUID ownerId, Category category);

    void deleteByOwnerIdAndCategory(UUID ownerId, Category category);
}
