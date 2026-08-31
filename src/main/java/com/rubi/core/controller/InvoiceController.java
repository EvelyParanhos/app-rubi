package com.rubi.core.controller;

import com.rubi.api.InvoicesApi;
import com.rubi.core.domain.Invoice;
import com.rubi.core.repository.InvoiceRepository;
import com.rubi.core.service.InvoiceService;
import com.rubi.model.InvoicePaymentRequest;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.bind.annotation.RestController;

import java.math.BigDecimal;
import java.util.UUID;

import com.rubi.core.domain.Transaction;
import com.rubi.core.repository.TransactionRepository;
import com.rubi.model.InvoiceItemResponse;
import com.rubi.model.InvoiceResponse;

import java.time.ZoneOffset;
import java.util.List;
import java.util.stream.Collectors;

@RestController
@RequiredArgsConstructor
public class InvoiceController implements InvoicesApi {

    private final InvoiceService invoiceService;
    private final InvoiceRepository invoiceRepository;
    private final TransactionRepository transactionRepository;

    @Override
    public ResponseEntity<InvoiceResponse> getInvoiceById(UUID id) {
        UUID currentUserId = getCurrentUserId();
        Invoice invoice = invoiceRepository.findById(id)
                .orElseThrow(() -> new IllegalArgumentException("Invoice not found"));

        if (!invoice.getCreditCard().getAccount().getOwner().getId().equals(currentUserId)) {
            throw new SecurityException("Forbidden: Invoice does not belong to current user");
        }

        BigDecimal total = transactionRepository.sumAmountByInvoiceId(id);
        List<Transaction> items = transactionRepository.findByInvoiceIdOrderByReferenceDateDesc(id);

        List<InvoiceItemResponse> itemResponses = items.stream().map(t -> new InvoiceItemResponse()
                .id(t.getId())
                .description(t.getDescription())
                .amount(t.getAmount().doubleValue())
                .purchaseDate(t.getReferenceDate() != null ? t.getReferenceDate().atOffset(ZoneOffset.UTC) : null)
                .installmentNumber(t.getInstallmentNumber())
                .totalInstallments(t.getTotalInstallments())
        ).collect(Collectors.toList());

        InvoiceResponse response = new InvoiceResponse()
                .id(invoice.getId())
                .creditCardId(invoice.getCreditCard().getId())
                .creditCardName(invoice.getCreditCard().getName())
                .referenceMonth(invoice.getReferenceMonth())
                .totalAmount(total != null ? total.doubleValue() : 0.0)
                .status(InvoiceResponse.StatusEnum.valueOf(invoice.getStatus().name()))
                .items(itemResponses);

        return ResponseEntity.ok(response);
    }

    @Override
    public ResponseEntity<Void> payInvoice(UUID id, InvoicePaymentRequest invoicePaymentRequest) {
        UUID currentUserId = getCurrentUserId();
        Invoice invoice = invoiceRepository.findById(id)
                .orElseThrow(() -> new IllegalArgumentException("Invoice not found"));

        if (!invoice.getCreditCard().getAccount().getOwner().getId().equals(currentUserId)) {
            throw new SecurityException("Forbidden: Invoice does not belong to current user");
        }

        invoiceService.payInvoice(
                id,
                invoicePaymentRequest.getSourceAccountId(),
                BigDecimal.valueOf(invoicePaymentRequest.getAmount())
        );
        return ResponseEntity.ok().build();
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
