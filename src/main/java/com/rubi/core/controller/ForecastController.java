package com.rubi.core.controller;

import com.rubi.api.ForecastApi;
import com.rubi.core.service.ForecastService;
import com.rubi.model.MonthlyForecastResponse;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.bind.annotation.RestController;

import java.util.UUID;

@RestController
@RequiredArgsConstructor
public class ForecastController implements ForecastApi {

    private final ForecastService forecastService;

    @Override
    public ResponseEntity<MonthlyForecastResponse> getMonthlyForecast(String startMonth, Integer months) {
        UUID currentUserId = getCurrentUserId();
        int monthsCount = months != null ? months : 12;
        MonthlyForecastResponse response = forecastService.getMonthlyForecast(currentUserId, startMonth, monthsCount);
        return ResponseEntity.ok(response);
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
