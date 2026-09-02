package com.rubi.core.service;

import com.rubi.core.domain.*;
import com.rubi.core.repository.*;
import com.rubi.model.CategoryEnum;
import com.rubi.model.ForecastChecklistItem;
import com.rubi.model.MonthForecastItem;
import com.rubi.model.MonthlyForecastResponse;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.time.YearMonth;
import java.util.*;

@Service
@RequiredArgsConstructor
public class ForecastService {

    private final RecurringTransactionRepository recurringTransactionRepository;
    private final RecurringFulfillmentRepository recurringFulfillmentRepository;
    private final RecurringOverrideRepository recurringOverrideRepository;
    private final CreditCardRepository creditCardRepository;
    private final InvoiceRepository invoiceRepository;
    private final TransactionRepository transactionRepository;

    public MonthlyForecastResponse getMonthlyForecast(UUID userId, String startMonthStr, int monthsCount) {
        if (monthsCount < 1 || monthsCount > 24) {
            monthsCount = 12;
        }

        YearMonth startYm;
        if (startMonthStr != null && !startMonthStr.isBlank()) {
            startYm = YearMonth.parse(startMonthStr);
        } else {
            startYm = YearMonth.now();
        }

        List<RecurringTransaction> userRecList = recurringTransactionRepository.findAllByOwnerIdAndIsActiveTrue(userId);
        List<CreditCard> userCards = creditCardRepository.findByAccountOwnerIdAndIsActiveTrue(userId);

        List<MonthForecastItem> monthForecastList = new ArrayList<>();

        for (int i = 0; i < monthsCount; i++) {
            YearMonth currentYm = startYm.plusMonths(i);
            String currentMonthStr = currentYm.toString();

            BigDecimal totalIncome = BigDecimal.ZERO;
            BigDecimal totalExpense = BigDecimal.ZERO;
            BigDecimal unfulfilledCreditCardRecTotal = BigDecimal.ZERO;

            List<ForecastChecklistItem> checklistItems = new ArrayList<>();

            for (RecurringTransaction rec : userRecList) {
                Optional<RecurringOverride> overrideOpt = recurringOverrideRepository
                        .findByRecurringTransactionIdAndReferenceMonth(rec.getId(), currentMonthStr);

                BigDecimal effectiveAmount = rec.getAmount();
                Integer effectiveDueDay = rec.getDueDay();
                boolean isOverridden = false;

                if (overrideOpt.isPresent()) {
                    effectiveAmount = overrideOpt.get().getOverrideAmount();
                    if (overrideOpt.get().getOverrideDueDay() != null) {
                        effectiveDueDay = overrideOpt.get().getOverrideDueDay();
                    }
                    isOverridden = true;
                }

                Optional<RecurringFulfillment> fulfillmentOpt = recurringFulfillmentRepository
                        .findByRecurringTransactionIdAndReferenceMonth(rec.getId(), currentMonthStr);

                boolean isFulfilled = fulfillmentOpt.isPresent();
                String statusStr = isFulfilled ? "REALIZADO" : "PREVISTO";
                UUID fulfilledTxId = isFulfilled ? fulfillmentOpt.get().getTransaction().getId() : null;

                if (rec.getCreditCard() != null) {
                    if (!isFulfilled && rec.getType() == RecurringTransactionType.EXPENSE) {
                        unfulfilledCreditCardRecTotal = unfulfilledCreditCardRecTotal.add(effectiveAmount);
                    }
                } else {
                    if (rec.getType() == RecurringTransactionType.INCOME) {
                        totalIncome = totalIncome.add(effectiveAmount);
                    } else {
                        totalExpense = totalExpense.add(effectiveAmount);
                    }
                }

                CategoryEnum catEnum = rec.getCategory() != null ? CategoryEnum.fromValue(rec.getCategory().name()) : CategoryEnum.UNCATEGORIZED;

                ForecastChecklistItem item = new ForecastChecklistItem()
                        .recurringTransactionId(rec.getId())
                        .description(rec.getDescription())
                        .amount(effectiveAmount.doubleValue())
                        .type(rec.getType().name())
                        .dueDay(effectiveDueDay)
                        .category(catEnum)
                        .accountId(rec.getAccount() != null ? rec.getAccount().getId() : null)
                        .creditCardId(rec.getCreditCard() != null ? rec.getCreditCard().getId() : null)
                        .creditCardName(rec.getCreditCard() != null ? rec.getCreditCard().getName() : null)
                        .status(ForecastChecklistItem.StatusEnum.fromValue(statusStr))
                        .fulfilledTransactionId(fulfilledTxId)
                        .isOverridden(isOverridden);

                checklistItems.add(item);
            }

            // Sum credit card invoice totals for current month
            BigDecimal creditCardInvoicesTotal = unfulfilledCreditCardRecTotal;
            for (CreditCard card : userCards) {
                Optional<Invoice> invoiceOpt = invoiceRepository.findByCreditCardIdAndReferenceMonth(card.getId(), currentMonthStr);
                if (invoiceOpt.isPresent()) {
                    BigDecimal invoiceAmt = transactionRepository.sumAmountByInvoiceId(invoiceOpt.get().getId());
                    if (invoiceAmt != null) {
                        creditCardInvoicesTotal = creditCardInvoicesTotal.add(invoiceAmt);
                    }
                }
            }

            BigDecimal netBalance = totalIncome.subtract(totalExpense).subtract(creditCardInvoicesTotal);

            MonthForecastItem monthItem = new MonthForecastItem()
                    .month(currentMonthStr)
                    .totalIncome(totalIncome.doubleValue())
                    .totalExpense(totalExpense.doubleValue())
                    .creditCardInvoicesTotal(creditCardInvoicesTotal.doubleValue())
                    .netBalance(netBalance.doubleValue())
                    .checklistItems(checklistItems);

            monthForecastList.add(monthItem);
        }

        return new MonthlyForecastResponse()
                .startMonth(startYm.toString())
                .months(monthForecastList);
    }
}
