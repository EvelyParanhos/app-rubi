package com.rubi.core.service;

import com.rubi.core.domain.*;
import com.rubi.core.repository.InvoiceRepository;
import com.rubi.core.repository.TransactionRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.time.YearMonth;
import java.util.UUID;

@Service
@RequiredArgsConstructor
public class InvoiceService {

    private final InvoiceRepository invoiceRepository;
    private final TransactionRepository transactionRepository;
    private final LedgerService ledgerService;

    @Transactional
    public void payInvoice(UUID invoiceId, UUID sourceAccountId, BigDecimal amount) {
        Invoice invoice = invoiceRepository.findById(invoiceId)
                .orElseThrow(() -> new IllegalArgumentException("Invoice not found"));

        if (invoice.getStatus() == InvoiceStatus.PAID) {
            throw new IllegalArgumentException("Invoice is already paid");
        }

        UUID liabilityAccountId = invoice.getCreditCard().getAccount().getId();

        // Transfere o valor pago da conta de origem para a conta de passivo
        ledgerService.transfer(
                sourceAccountId,
                liabilityAccountId,
                amount,
                "Pagamento Fatura " + invoice.getReferenceMonth()
        );

        BigDecimal invoiceTotal = transactionRepository.sumAmountByInvoiceId(invoiceId);

        if (invoiceTotal.compareTo(BigDecimal.ZERO) > 0 && amount.compareTo(invoiceTotal) < 0) {
            // Pagamento parcial com saldo devedor remanescente (RN09)
            invoice.setStatus(InvoiceStatus.PARTIALLY_PAID);
            BigDecimal remaining = invoiceTotal.subtract(amount);

            YearMonth currentYm = YearMonth.parse(invoice.getReferenceMonth());
            String nextMonthStr = currentYm.plusMonths(1).toString();

            Invoice nextInvoice = invoiceRepository.findByCreditCardIdAndReferenceMonth(invoice.getCreditCard().getId(), nextMonthStr)
                    .orElseGet(() -> invoiceRepository.save(Invoice.builder()
                            .creditCard(invoice.getCreditCard())
                            .referenceMonth(nextMonthStr)
                            .status(InvoiceStatus.OPEN)
                            .createdAt(LocalDateTime.now())
                            .build()));

            // Rolagem nasce com status PENDING_ADJUSTMENT para conciliação dos juros do banco (RN09)
            Transaction rollover = Transaction.builder()
                    .account(invoice.getCreditCard().getAccount())
                    .amount(remaining)
                    .type(TransactionType.DEBIT)
                    .description("Saldo remanescente fatura " + invoice.getReferenceMonth())
                    .referenceDate(LocalDateTime.now())
                    .invoice(nextInvoice)
                    .status(TransactionStatus.PENDING)
                    .build();

            transactionRepository.save(rollover);
        } else {
            invoice.setStatus(InvoiceStatus.PAID);
        }

        invoiceRepository.save(invoice);
    }
}
