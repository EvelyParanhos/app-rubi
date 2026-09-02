package com.rubi.core.service;

import com.rubi.core.domain.*;
import com.rubi.core.repository.AccountRepository;
import com.rubi.core.repository.CreditCardRepository;
import com.rubi.core.repository.InvoiceRepository;
import com.rubi.core.repository.TransactionRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDateTime;
import java.time.OffsetDateTime;
import java.time.YearMonth;
import java.util.UUID;

@Service
@RequiredArgsConstructor
public class CreditCardService {

    private final CreditCardRepository creditCardRepository;
    private final InvoiceRepository invoiceRepository;
    private final AccountRepository accountRepository;
    private final TransactionRepository transactionRepository;

    public CreditCard createCreditCard(UUID accountId, String name, BigDecimal creditLimit, Integer closingDay, Integer dueDay) {
        Account account = accountRepository.findById(accountId)
                .orElseThrow(() -> new IllegalArgumentException("Account not found"));

        if (account.getType() != AccountType.LIABILITY) {
            throw new IllegalArgumentException("Account must be of type LIABILITY");
        }

        CreditCard creditCard = CreditCard.builder()
                .account(account)
                .name(name)
                .creditLimit(creditLimit)
                .closingDay(closingDay)
                .dueDay(dueDay)
                .isActive(true)
                .createdAt(LocalDateTime.now())
                .build();

        return creditCardRepository.save(creditCard);
    }

    @Transactional
    public Transaction processPurchase(UUID creditCardId, BigDecimal amount, String description, Category category, int installments, OffsetDateTime purchaseDate) {
        CreditCard creditCard = creditCardRepository.findById(creditCardId)
                .orElseThrow(() -> new IllegalArgumentException("Credit card not found"));

        if (installments < 1) {
            installments = 1;
        }

        if (purchaseDate == null) {
            purchaseDate = OffsetDateTime.now();
        }

        YearMonth firstInvoiceMonth;
        if (purchaseDate.getDayOfMonth() >= creditCard.getClosingDay()) {
            firstInvoiceMonth = YearMonth.from(purchaseDate.toLocalDate()).plusMonths(1);
        } else {
            firstInvoiceMonth = YearMonth.from(purchaseDate.toLocalDate());
        }

        BigDecimal installmentsBd = BigDecimal.valueOf(installments);
        BigDecimal installmentValue = amount.divide(installmentsBd, 2, RoundingMode.DOWN);
        BigDecimal firstInstallmentValue = amount.subtract(installmentValue.multiply(BigDecimal.valueOf(installments - 1)));

        Transaction firstTx = null;

        for (int i = 1; i <= installments; i++) {
            YearMonth currentYearMonth = firstInvoiceMonth.plusMonths(i - 1);
            String currentMonthStr = currentYearMonth.toString();

            Invoice invoice = invoiceRepository.findByCreditCardIdAndReferenceMonth(creditCard.getId(), currentMonthStr)
                    .orElseGet(() -> {
                        Invoice newInvoice = Invoice.builder()
                                .creditCard(creditCard)
                                .referenceMonth(currentMonthStr)
                                .status(InvoiceStatus.OPEN)
                                .createdAt(LocalDateTime.now())
                                .build();
                        return invoiceRepository.save(newInvoice);
                    });

            BigDecimal valueForInstallment = (i == 1) ? firstInstallmentValue : installmentValue;

            String installmentDescription = installments > 1 ?
                    String.format("%s (%d/%d)", description, i, installments) : description;

            LocalDateTime installmentRefDate = purchaseDate.toLocalDateTime().plusMonths(i - 1);

            Transaction transaction = Transaction.builder()
                    .account(creditCard.getAccount())
                    .amount(valueForInstallment)
                    .type(TransactionType.DEBIT)
                    .description(installmentDescription)
                    .category(category != null ? category : Category.UNCATEGORIZED)
                    .referenceDate(installmentRefDate)
                    .invoice(invoice)
                    .installmentNumber(i)
                    .totalInstallments(installments)
                    .status("CONFIRMED")
                    .build();

            Transaction savedTx = transactionRepository.save(transaction);
            if (i == 1) {
                firstTx = savedTx;
            }
        }

        return firstTx;
    }

    @Transactional
    public Transaction processPurchase(UUID creditCardId, BigDecimal amount, String description, int installments, OffsetDateTime purchaseDate) {
        return processPurchase(creditCardId, amount, description, Category.UNCATEGORIZED, installments, purchaseDate);
    }
}
