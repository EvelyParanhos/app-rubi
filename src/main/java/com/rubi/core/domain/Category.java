package com.rubi.core.domain;

import lombok.Getter;

@Getter
public enum Category {
    PETS("Animais de Estimação"),
    BARS_AND_RESTAURANTS("Bares e Restaurantes"),
    DELIVERY("Delivery"),
    SHOPPING("Compras"),
    HOUSING("Contas da Casa"),
    DONATIONS("Doações"),
    EDUCATION("Educação"),
    ENTERTAINMENT("Entretenimento e Lazer"),
    TAXES_AND_FEES("Impostos, Tarifas e Juros"),
    INVESTMENTS("Investimentos e Caixinhas"),
    SUPERMARKET("Mercado"),
    UNCATEGORIZED("Não categorizado"),
    PAYMENTS("Pagamentos"),
    SERVICE_PROVIDERS("Prestadores de Serviço"),
    RECEIPTS("Recebimentos"),
    HEALTH("Saúde e Cuidados Pessoais"),
    DIGITAL_SERVICES("Serviços Digitais"),
    TRANSFERS("Transferências"),
    TRANSPORT("Veículo e Transporte"),
    TRAVEL("Viagens");

    private final String displayName;

    Category(String displayName) {
        this.displayName = displayName;
    }
}
