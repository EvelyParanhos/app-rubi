package com.rubi.core.controller;

import com.rubi.api.PartnershipsApi;
import com.rubi.core.domain.Partnership;
import com.rubi.core.domain.PartnershipStatus;
import com.rubi.core.domain.User;
import com.rubi.core.repository.PartnershipRepository;
import com.rubi.core.service.PartnershipService;
import com.rubi.model.PartnershipActiveResponse;
import com.rubi.model.PartnershipInviteRequest;
import com.rubi.model.PartnershipInviteResponse;
import com.rubi.model.PartnershipStatusUpdateRequest;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.bind.annotation.RestController;

import java.util.Optional;
import java.util.UUID;

@RestController
@RequiredArgsConstructor
public class PartnershipController implements PartnershipsApi {

    private final PartnershipService partnershipService;
    private final PartnershipRepository partnershipRepository;

    @Override
    public ResponseEntity<PartnershipActiveResponse> getActivePartnership() {
        UUID currentUserId = getCurrentUserId();
        Optional<Partnership> activeOpt = partnershipRepository.findActivePartnership(currentUserId, PartnershipStatus.ACTIVE);
        if (activeOpt.isEmpty()) {
            activeOpt = partnershipRepository.findActivePartnership(currentUserId, PartnershipStatus.PENDING);
        }

        if (activeOpt.isPresent()) {
            Partnership partnership = activeOpt.get();
            User partner = partnership.getUser1().getId().equals(currentUserId) ? partnership.getUser2() : partnership.getUser1();
            boolean isActive = partnership.getStatus() == PartnershipStatus.ACTIVE;
            PartnershipActiveResponse response = new PartnershipActiveResponse()
                    .hasActivePartnership(isActive)
                    .id(partnership.getId())
                    .status(partnership.getStatus().name())
                    .partnerId(partner.getId())
                    .partnerName(partner.getName());
            return ResponseEntity.ok(response);
        } else {
            PartnershipActiveResponse response = new PartnershipActiveResponse()
                    .hasActivePartnership(false);
            return ResponseEntity.ok(response);
        }
    }

    @Override
    public ResponseEntity<PartnershipInviteResponse> invitePartnership(PartnershipInviteRequest partnershipInviteRequest) {
        try {
            UUID inviterId = getCurrentUserId();
            Partnership partnership = partnershipService.sendInvite(inviterId, partnershipInviteRequest.getTargetPhoneNumber());
            PartnershipInviteResponse.StatusEnum statusEnum;
            try {
                statusEnum = PartnershipInviteResponse.StatusEnum.valueOf(partnership.getStatus().name());
            } catch (IllegalArgumentException e) {
                statusEnum = PartnershipInviteResponse.StatusEnum.TERMINATED;
            }
            PartnershipInviteResponse response = new PartnershipInviteResponse()
                    .id(partnership.getId().toString())
                    .status(statusEnum);
            return ResponseEntity.status(HttpStatus.CREATED).body(response);
        } catch (IllegalArgumentException e) {
            return ResponseEntity.status(HttpStatus.BAD_REQUEST).build();
        }
    }

    @Override
    public ResponseEntity<Void> updatePartnershipStatus(UUID id, PartnershipStatusUpdateRequest partnershipStatusUpdateRequest) {
        UUID currentUserId = getCurrentUserId();
        if (partnershipStatusUpdateRequest.getStatus() == PartnershipStatusUpdateRequest.StatusEnum.ACTIVE) {
            partnershipService.acceptInvite(id, currentUserId);
        } else {
            partnershipService.rejectInvite(id);
        }
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
