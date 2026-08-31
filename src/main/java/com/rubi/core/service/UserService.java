package com.rubi.core.service;

import com.rubi.core.domain.User;
import com.rubi.core.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import java.time.LocalDateTime;
import java.util.UUID;

@Service
@RequiredArgsConstructor
public class UserService {

    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;

    public User registerUser(String name, String phoneNumber, String rawPin) {
        if (userRepository.existsByPhoneNumber(phoneNumber)) {
            throw new IllegalArgumentException("Phone number already exists");
        }
        User user = User.builder()
                .name(name)
                .phoneNumber(phoneNumber)
                .pinHash(passwordEncoder.encode(rawPin))
                .createdAt(LocalDateTime.now())
                .build();
        return userRepository.save(user);
    }

    public User linkTelegramChat(UUID userId, String telegramChatId) {
        User user = userRepository.findById(userId)
                .orElseThrow(() -> new IllegalArgumentException("User not found"));
        user.setTelegramChatId(telegramChatId);
        return userRepository.save(user);
    }
}
