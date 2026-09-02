package com.rubi.core.service;

import com.rubi.core.domain.*;
import com.rubi.core.repository.CategoryBudgetRepository;
import com.rubi.core.repository.TransactionRepository;
import com.rubi.core.repository.UserRepository;
import com.rubi.model.CategoryBudgetResponse;
import com.rubi.model.CategoryEnum;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDateTime;
import java.time.YearMonth;
import java.util.*;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class CategoryBudgetService {

    private final CategoryBudgetRepository categoryBudgetRepository;
    private final TransactionRepository transactionRepository;
    private final UserRepository userRepository;

    public List<CategoryBudgetResponse> getCategoryBudgets(UUID ownerId) {
        List<CategoryBudget> budgets = categoryBudgetRepository.findByOwnerId(ownerId);

        YearMonth nowYm = YearMonth.now();
        LocalDateTime monthStart = nowYm.atDay(1).atStartOfDay();
        LocalDateTime monthEnd = nowYm.atEndOfMonth().atTime(23, 59, 59);

        List<Transaction> monthTxList = transactionRepository.findByAccountOwnerIdAndReferenceDateBetweenOrderByReferenceDateDesc(ownerId, monthStart, monthEnd);

        Map<Category, BigDecimal> categorySpentMap = new HashMap<>();
        for (Transaction tx : monthTxList) {
            if (tx.getType() == TransactionType.DEBIT && tx.getCategory() != null) {
                categorySpentMap.put(
                        tx.getCategory(),
                        categorySpentMap.getOrDefault(tx.getCategory(), BigDecimal.ZERO).add(tx.getAmount())
                );
            }
        }

        return budgets.stream().map(b -> {
            BigDecimal spent = categorySpentMap.getOrDefault(b.getCategory(), BigDecimal.ZERO);
            double progress = 0.0;
            String status = "OK";

            if (b.getMonthlyLimit() != null && b.getMonthlyLimit().compareTo(BigDecimal.ZERO) > 0) {
                progress = spent.divide(b.getMonthlyLimit(), 4, RoundingMode.HALF_UP).doubleValue() * 100.0;
                if (progress >= 100.0) {
                    status = "EXCEEDED";
                } else if (progress >= 80.0) {
                    status = "WARNING";
                }
            }

            CategoryEnum catEnum = CategoryEnum.fromValue(b.getCategory().name());

            return new CategoryBudgetResponse()
                    .id(b.getId())
                    .category(catEnum)
                    .monthlyLimit(b.getMonthlyLimit() != null ? b.getMonthlyLimit().doubleValue() : null)
                    .monthlyGoal(b.getMonthlyGoal() != null ? b.getMonthlyGoal().doubleValue() : null)
                    .currentMonthSpent(spent.doubleValue())
                    .progressPercentage(progress)
                    .status(CategoryBudgetResponse.StatusEnum.fromValue(status));
        }).collect(Collectors.toList());
    }

    @Transactional
    public CategoryBudget saveCategoryBudget(UUID ownerId, String categoryStr, BigDecimal monthlyLimit, BigDecimal monthlyGoal) {
        User owner = userRepository.findById(ownerId)
                .orElseThrow(() -> new IllegalArgumentException("User not found"));

        Category category = Category.valueOf(categoryStr.toUpperCase());

        CategoryBudget budget = categoryBudgetRepository.findByOwnerIdAndCategory(ownerId, category)
                .orElseGet(() -> CategoryBudget.builder()
                        .owner(owner)
                        .category(category)
                        .createdAt(LocalDateTime.now())
                        .build());

        budget.setMonthlyLimit(monthlyLimit);
        budget.setMonthlyGoal(monthlyGoal);
        budget.setUpdatedAt(LocalDateTime.now());

        return categoryBudgetRepository.save(budget);
    }

    @Transactional
    public void deleteCategoryBudget(UUID ownerId, String categoryStr) {
        Category category = Category.valueOf(categoryStr.toUpperCase());
        categoryBudgetRepository.deleteByOwnerIdAndCategory(ownerId, category);
    }
}
