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
@Table(name = "recurring_overrides", uniqueConstraints = {
    @UniqueConstraint(columnNames = {"recurring_transaction_id", "reference_month"})
})
@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class RecurringOverride {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "recurring_transaction_id", nullable = false)
    private RecurringTransaction recurringTransaction;

    @Column(name = "reference_month", nullable = false, length = 7)
    private String referenceMonth;

    @Column(name = "override_amount", nullable = false, precision = 19, scale = 4)
    private BigDecimal overrideAmount;

    @Column(name = "override_due_day")
    private Integer overrideDueDay;

    @Column(name = "created_at", nullable = false)
    private LocalDateTime createdAt;
}
