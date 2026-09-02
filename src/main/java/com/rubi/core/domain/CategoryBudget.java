package com.rubi.core.domain;

import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.UUID;

@Entity
@Table(name = "category_budgets", uniqueConstraints = {
    @UniqueConstraint(columnNames = {"owner_id", "category"})
})
@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class CategoryBudget {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "owner_id", nullable = false)
    private User owner;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 50)
    private Category category;

    @Column(name = "monthly_limit", precision = 19, scale = 4)
    private BigDecimal monthlyLimit;

    @Column(name = "monthly_goal", precision = 19, scale = 4)
    private BigDecimal monthlyGoal;

    @Column(name = "created_at", nullable = false)
    private LocalDateTime createdAt;

    @Column(name = "updated_at", nullable = false)
    private LocalDateTime updatedAt;
}
