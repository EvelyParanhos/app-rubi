package com.rubi.core.controller;

import com.rubi.api.CategoryBudgetsApi;
import com.rubi.core.domain.CategoryBudget;
import com.rubi.core.service.CategoryBudgetService;
import com.rubi.model.CategoryBudgetCreateRequest;
import com.rubi.model.CategoryBudgetResponse;
import com.rubi.model.CategoryEnum;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.bind.annotation.RestController;

import java.math.BigDecimal;
import java.util.List;
import java.util.UUID;

@RestController
@RequiredArgsConstructor
public class CategoryBudgetController implements CategoryBudgetsApi {

    private final CategoryBudgetService categoryBudgetService;

    @Override
    public ResponseEntity<List<CategoryBudgetResponse>> getCategoryBudgets() {
        UUID ownerId = getCurrentUserId();
        List<CategoryBudgetResponse> responseList = categoryBudgetService.getCategoryBudgets(ownerId);
        return ResponseEntity.ok(responseList);
    }

    @Override
    public ResponseEntity<CategoryBudgetResponse> saveCategoryBudget(CategoryBudgetCreateRequest request) {
        UUID ownerId = getCurrentUserId();

        BigDecimal limit = request.getMonthlyLimit() != null ? BigDecimal.valueOf(request.getMonthlyLimit()) : null;
        BigDecimal goal = request.getMonthlyGoal() != null ? BigDecimal.valueOf(request.getMonthlyGoal()) : null;

        CategoryBudget saved = categoryBudgetService.saveCategoryBudget(
                ownerId,
                request.getCategory().name(),
                limit,
                goal
        );

        CategoryEnum catEnum = CategoryEnum.fromValue(saved.getCategory().name());

        CategoryBudgetResponse response = new CategoryBudgetResponse()
                .id(saved.getId())
                .category(catEnum)
                .monthlyLimit(saved.getMonthlyLimit() != null ? saved.getMonthlyLimit().doubleValue() : null)
                .monthlyGoal(saved.getMonthlyGoal() != null ? saved.getMonthlyGoal().doubleValue() : null)
                .currentMonthSpent(0.0)
                .progressPercentage(0.0)
                .status(CategoryBudgetResponse.StatusEnum.OK);

        return ResponseEntity.ok(response);
    }

    @Override
    public ResponseEntity<Void> deleteCategoryBudget(CategoryEnum category) {
        UUID ownerId = getCurrentUserId();
        categoryBudgetService.deleteCategoryBudget(ownerId, category.name());
        return ResponseEntity.noContent().build();
    }

    private UUID getCurrentUserId() {
        Authentication auth = SecurityContextHolder.getContext().getAuthentication();
        if (auth != null && auth.isAuthenticated() && !"anonymousUser".equals(auth.getName())) {
            Object principal = auth.getPrincipal();
            if (principal instanceof UUID) {
                return (UUID) principal;
            }
            return UUID.fromString(principal.toString());
        }
        throw new SecurityException("Unauthorized");
    }
}
