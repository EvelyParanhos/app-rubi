package com.rubi.core.controller;

import com.rubi.api.AuthApi;
import com.rubi.core.service.AuthService;
import com.rubi.model.UserLoginRequest;
import com.rubi.model.UserLoginResponse;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequiredArgsConstructor
public class AuthController implements AuthApi {

    private final AuthService authService;

    @Override
    public ResponseEntity<UserLoginResponse> loginUser(UserLoginRequest userLoginRequest) {
        String token = authService.login(userLoginRequest.getPhoneNumber(), userLoginRequest.getPin());
        UserLoginResponse response = new UserLoginResponse().token(token);
        return ResponseEntity.ok(response);
    }
}
