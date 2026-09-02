from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def get_main_menu_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💸 Novo Gasto", callback_data="cmd_gasto"),
            InlineKeyboardButton("📥 Nova Receita", callback_data="cmd_receita")
        ],
        [
            InlineKeyboardButton("📊 Extrato / Saldo", callback_data="cmd_extrato"),
            InlineKeyboardButton("💳 Faturas Cartão", callback_data="cmd_cartoes")
        ],
        [
            InlineKeyboardButton("🔮 Previsão (12 Meses)", callback_data="cmd_previsao")
        ]
    ])
