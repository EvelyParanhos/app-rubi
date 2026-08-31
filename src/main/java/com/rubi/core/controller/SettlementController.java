package com.rubi.core.controller;

import com.rubi.api.SettlementsApi;
import com.rubi.core.domain.User;
import com.rubi.core.repository.UserRepository;
import com.rubi.core.service.PartnershipService;
import com.rubi.core.service.SettlementService;
import com.rubi.core.service.SettlementService.NetBalanceResult;
import com.rubi.model.NetBalanceResponse;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.bind.annotation.RestController;

import java.util.UUID;

@RestController
@RequiredArgsConstructor
public class SettlementController implements SettlementsApi {

    private final SettlementService settlementService;
    private final PartnershipService partnershipService;
    private final UserRepository userRepository;

    @Override
    public ResponseEntity<NetBalanceResponse> getNetBalance(String month) {
        UUID currentUserId = getCurrentUserId();
        UUID partnerId = partnershipService.getActivePartnerId(currentUserId);

        NetBalanceResult result = settlementService.getNetBalance(currentUserId, partnerId, month);

        String creditorName = userRepository.findById(result.creditorId())
                .map(User::getName).orElse("Credor");
        String debtorName = userRepository.findById(result.debtorId())
                .map(User::getName).orElse("Devedor");

        NetBalanceResponse response = new NetBalanceResponse()
                .creditorId(result.creditorId())
                .creditorName(creditorName)
                .debtorId(result.debtorId())
                .debtorName(debtorName)
                .netAmount(result.netAmount().doubleValue());

        return ResponseEntity.ok(response);
    }

    @Override
    public ResponseEntity<Void> payNetBalance(com.rubi.model.SettlementPayRequest request) {
        UUID currentUserId = getCurrentUserId();
        settlementService.payNetBalance(
                currentUserId,
                request.getMonth(),
                request.getSourceAccountId(),
                java.math.BigDecimal.valueOf(request.getAmount())
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
