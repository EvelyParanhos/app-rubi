package com.rubi.core.service;

import com.rubi.core.domain.User;
import com.rubi.core.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.security.authentication.DisabledException;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;

@Service
@RequiredArgsConstructor
public class AuthService {

    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;
    private final JwtService jwtService;

    public String login(String phoneNumber, String rawPin) {
        User user = userRepository.findByPhoneNumber(phoneNumber)
                .orElseThrow(() -> new IllegalArgumentException("Credentials mismatch"));

        if (!passwordEncoder.matches(rawPin, user.getPinHash())) {
            throw new IllegalArgumentException("Credentials mismatch");
        }

        if (Boolean.FALSE.equals(user.getIsActive())) {
            throw new DisabledException("User account is inactive");
        }

        return jwtService.generateToken(user.getId());
    }
}
