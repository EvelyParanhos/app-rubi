package com.rubi.core.controller;

import com.rubi.api.UsersApi;
import com.rubi.core.domain.User;
import com.rubi.core.service.UserService;
import com.rubi.model.TelegramLinkRequest;
import com.rubi.model.UserRegistrationRequest;
import com.rubi.model.UserRegistrationResponse;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.bind.annotation.RestController;

import java.util.UUID;

import com.rubi.core.service.JwtService;

@RestController
@RequiredArgsConstructor
public class UserController implements UsersApi {

    private final UserService userService;
    private final JwtService jwtService;

    @Override
    public ResponseEntity<UserRegistrationResponse> registerUser(UserRegistrationRequest userRegistrationRequest) {
        try {
            User registeredUser = userService.registerUser(
                    userRegistrationRequest.getName(),
                    userRegistrationRequest.getPhoneNumber(),
                    userRegistrationRequest.getPin()
            );
            String token = jwtService.generateToken(registeredUser.getId());
            UserRegistrationResponse response = new UserRegistrationResponse()
                    .id(registeredUser.getId().toString())
                    .token(token)
                    .name(registeredUser.getName())
                    .phoneNumber(registeredUser.getPhoneNumber());
            return ResponseEntity.status(HttpStatus.CREATED).body(response);
        } catch (IllegalArgumentException e) {
            return ResponseEntity.status(HttpStatus.CONFLICT).build();
        }
    }

    @Override
    public ResponseEntity<Void> linkTelegram(TelegramLinkRequest telegramLinkRequest) {
        UUID currentUserId = getCurrentUserId();
        userService.linkTelegramChat(currentUserId, telegramLinkRequest.getTelegramChatId());
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
