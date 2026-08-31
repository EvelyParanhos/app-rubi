package com.rubi.core.controller;

import com.rubi.api.CreditCardsApi;
import com.rubi.core.domain.CreditCard;
import com.rubi.core.repository.CreditCardRepository;
import com.rubi.core.service.CreditCardService;
import com.rubi.model.CreditCardCreateRequest;
import com.rubi.model.CreditCardCreateResponse;
import com.rubi.model.CreditCardPurchaseRequest;
import com.rubi.model.CreditCardResponse;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.bind.annotation.RestController;

import java.math.BigDecimal;
import java.util.List;
import java.util.UUID;
import java.util.stream.Collectors;

import com.rubi.core.repository.InvoiceRepository;
import com.rubi.core.repository.TransactionRepository;

import com.rubi.core.service.LedgerService;

@RestController
@RequiredArgsConstructor
public class CreditCardController implements CreditCardsApi {

    private final CreditCardService creditCardService;
    private final CreditCardRepository creditCardRepository;
    private final InvoiceRepository invoiceRepository;
    private final TransactionRepository transactionRepository;
    private final LedgerService ledgerService;

    @Override
    public ResponseEntity<CreditCardCreateResponse> createCreditCard(CreditCardCreateRequest creditCardCreateRequest) {
        CreditCard creditCard = creditCardService.createCreditCard(
                creditCardCreateRequest.getAccountId(),
                creditCardCreateRequest.getName(),
                BigDecimal.valueOf(creditCardCreateRequest.getCreditLimit()),
                creditCardCreateRequest.getClosingDay(),
                creditCardCreateRequest.getDueDay()
        );

        CreditCardCreateResponse response = new CreditCardCreateResponse(creditCard.getId());
        return ResponseEntity.status(HttpStatus.CREATED).body(response);
    }

    @Override
    public ResponseEntity<List<CreditCardResponse>> getCreditCards() {
        UUID ownerId = getCurrentUserId();
        List<CreditCard> cards = creditCardRepository.findByAccountOwnerIdAndIsActiveTrue(ownerId);
        String currentMonthStr = java.time.YearMonth.now().toString();

        List<CreditCardResponse> responseList = cards.stream()
                .map(c -> {
                    BigDecimal rawBal = ledgerService.getAccountBalance(c.getAccount().getId());
                    BigDecimal usedLimit = rawBal != null && rawBal.compareTo(BigDecimal.ZERO) < 0 ? rawBal.abs() : BigDecimal.ZERO;
                    BigDecimal availableLimit = c.getCreditLimit().subtract(usedLimit);
                    if (availableLimit.compareTo(BigDecimal.ZERO) < 0) {
                        availableLimit = BigDecimal.ZERO;
                    }

                    BigDecimal currentInvoiceAmt = invoiceRepository.findByCreditCardIdAndReferenceMonth(c.getId(), currentMonthStr)
                            .map(inv -> transactionRepository.sumAmountByInvoiceId(inv.getId()))
                            .orElse(BigDecimal.ZERO);

                    return new CreditCardResponse()
                            .id(c.getId())
                            .name(c.getName())
                            .creditLimit(c.getCreditLimit().doubleValue())
                            .usedLimit(usedLimit.doubleValue())
                            .availableLimit(availableLimit.doubleValue())
                            .currentInvoiceAmount(currentInvoiceAmt != null ? currentInvoiceAmt.doubleValue() : 0.0)
                            .closingDay(c.getClosingDay())
                            .dueDay(c.getDueDay());
                })
                .collect(Collectors.toList());

        return ResponseEntity.ok(responseList);
    }

    @Override
    public ResponseEntity<Void> recordCreditCardPurchase(UUID id, CreditCardPurchaseRequest creditCardPurchaseRequest) {
        UUID currentUserId = getCurrentUserId();
        CreditCard card = creditCardRepository.findById(id)
                .orElseThrow(() -> new IllegalArgumentException("Credit card not found"));

        if (!card.getAccount().getOwner().getId().equals(currentUserId)) {
            throw new SecurityException("Forbidden: Credit card does not belong to current user");
        }

        creditCardService.processPurchase(
                id,
                BigDecimal.valueOf(creditCardPurchaseRequest.getAmount()),
                creditCardPurchaseRequest.getDescription(),
                creditCardPurchaseRequest.getInstallments(),
                creditCardPurchaseRequest.getPurchaseDate()
        );
        return ResponseEntity.status(HttpStatus.CREATED).build();
    }

    @Override
    public ResponseEntity<List<com.rubi.model.InvoiceResponse>> getCreditCardInvoices(UUID id) {
        UUID currentUserId = getCurrentUserId();
        CreditCard card = creditCardRepository.findById(id)
                .orElseThrow(() -> new IllegalArgumentException("Credit card not found"));

        if (!card.getAccount().getOwner().getId().equals(currentUserId)) {
            throw new SecurityException("Forbidden: Credit card does not belong to current user");
        }

        List<com.rubi.core.domain.Invoice> invoices = invoiceRepository.findByCreditCardIdOrderByReferenceMonthDesc(id);
        List<com.rubi.model.InvoiceResponse> responses = invoices.stream().map(inv -> {
            BigDecimal total = transactionRepository.sumAmountByInvoiceId(inv.getId());
            return new com.rubi.model.InvoiceResponse()
                    .id(inv.getId())
                    .creditCardId(card.getId())
                    .creditCardName(card.getName())
                    .referenceMonth(inv.getReferenceMonth())
                    .totalAmount(total != null ? total.doubleValue() : 0.0)
                    .status(com.rubi.model.InvoiceResponse.StatusEnum.valueOf(inv.getStatus().name()));
        }).collect(Collectors.toList());

        return ResponseEntity.ok(responses);
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
