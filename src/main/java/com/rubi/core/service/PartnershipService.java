package com.rubi.core.service;

import com.rubi.core.domain.Partnership;
import com.rubi.core.domain.PartnershipStatus;
import com.rubi.core.domain.User;
import com.rubi.core.repository.PartnershipRepository;
import com.rubi.core.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import java.time.LocalDateTime;
import java.util.UUID;

@Service
@RequiredArgsConstructor
public class PartnershipService {

    private final PartnershipRepository partnershipRepository;
    private final UserRepository userRepository;

    public Partnership sendInvite(UUID inviterId, String targetPhoneNumber) {
        User targetUser = userRepository.findByPhoneNumber(targetPhoneNumber)
                .orElseThrow(() -> new IllegalArgumentException("Target user not found"));

        if (inviterId.equals(targetUser.getId())) {
            throw new IllegalArgumentException("Cannot invite yourself");
        }

        User inviter = userRepository.findById(inviterId)
                .orElseThrow(() -> new IllegalArgumentException("Inviter not found"));

        boolean inviterHasPending = partnershipRepository.existsByUser1IdOrUser2IdAndStatus(inviterId, inviterId, PartnershipStatus.PENDING);
        boolean inviterHasActive = partnershipRepository.existsByUser1IdOrUser2IdAndStatus(inviterId, inviterId, PartnershipStatus.ACTIVE);
        boolean targetHasPending = partnershipRepository.existsByUser1IdOrUser2IdAndStatus(targetUser.getId(), targetUser.getId(), PartnershipStatus.PENDING);
        boolean targetHasActive = partnershipRepository.existsByUser1IdOrUser2IdAndStatus(targetUser.getId(), targetUser.getId(), PartnershipStatus.ACTIVE);

        if (inviterHasPending || inviterHasActive || targetHasPending || targetHasActive) {
            throw new IllegalArgumentException("One of the users already has an active or pending partnership");
        }

        Partnership partnership = Partnership.builder()
                .user1(inviter)
                .user2(targetUser)
                .status(PartnershipStatus.PENDING)
                .createdAt(LocalDateTime.now())
                .build();

        return partnershipRepository.save(partnership);
    }

    public Partnership acceptInvite(UUID partnershipId, UUID acceptorId) {
        Partnership partnership = partnershipRepository.findById(partnershipId)
                .orElseThrow(() -> new IllegalArgumentException("Partnership not found"));

        if (partnership.getStatus() != PartnershipStatus.PENDING) {
            throw new IllegalArgumentException("Partnership is not pending");
        }

        if (!partnership.getUser2().getId().equals(acceptorId)) {
            throw new SecurityException("Only the invited user can accept this partnership invite");
        }

        boolean inviterHasActive = partnershipRepository.existsByUser1IdOrUser2IdAndStatus(partnership.getUser1().getId(), partnership.getUser1().getId(), PartnershipStatus.ACTIVE);
        boolean acceptorHasActive = partnershipRepository.existsByUser1IdOrUser2IdAndStatus(acceptorId, acceptorId, PartnershipStatus.ACTIVE);

        if (inviterHasActive || acceptorHasActive) {
            throw new IllegalArgumentException("One of the users already has an active partnership");
        }

        partnership.setStatus(PartnershipStatus.ACTIVE);
        return partnershipRepository.save(partnership);
    }

    public Partnership rejectInvite(UUID partnershipId) {
        Partnership partnership = partnershipRepository.findById(partnershipId)
                .orElseThrow(() -> new IllegalArgumentException("Partnership not found"));

        partnership.setStatus(PartnershipStatus.BROKEN);
        return partnershipRepository.save(partnership);
    }

    public UUID getActivePartnerId(UUID userId) {
        Partnership active = partnershipRepository.findActivePartnership(userId, PartnershipStatus.ACTIVE)
                .orElseThrow(() -> new IllegalArgumentException("No active partnership found"));
        return active.getUser1().getId().equals(userId) ? active.getUser2().getId() : active.getUser1().getId();
    }
}
