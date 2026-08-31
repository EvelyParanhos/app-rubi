import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

from handlers.auth import get_auth_conversation_handler, get_main_menu_keyboard
from handlers.onboarding import get_onboarding_conversation_handler
from handlers.transaction import get_transaction_conversation_handler
from handlers.card import get_card_conversation_handler
from handlers.settlement import handle_acerto, execute_quitar_acerto
from handlers.statement import handle_extrato, handle_main_menu
from auth_manager import is_authenticated

load_dotenv()

# Configuração de Logging Limpo
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("RubiBot")

async def global_error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"[ERRO GLOBAL BOT] Exceção não tratada: {context.error}", exc_info=context.error)

    msg = "❌ Ocorreu um erro ao processar sua solicitação. Por favor, tente novamente em instantes."

    if isinstance(update, Update):
        if update.callback_query:
            try:
                await update.callback_query.answer("Ocorreu um erro no servidor.", show_alert=True)
                await update.callback_query.edit_message_text(msg, reply_markup=get_main_menu_keyboard())
            except Exception:
                pass
        elif update.message:
            await update.message.reply_text(msg, reply_markup=get_main_menu_keyboard())

def main():
    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        logger.error("TELEGRAM_TOKEN não configurado no arquivo .env!")
        return

    logger.info("🤖 Inicializando Bot Rubi Financial (UI Cliente de Apresentação)...")

    app = ApplicationBuilder().token(token).build()

    # 1. Registrar ConversationHandlers de fluxos principais
    app.add_handler(get_auth_conversation_handler())
    app.add_handler(get_onboarding_conversation_handler())
    app.add_handler(get_transaction_conversation_handler())
    app.add_handler(get_card_conversation_handler())

    # 2. Registrar Handlers Diretos e Callbacks
    app.add_handler(CommandHandler("acerto", handle_acerto))
    app.add_handler(CallbackQueryHandler(handle_acerto, pattern="^cmd_acerto$"))
    app.add_handler(CallbackQueryHandler(execute_quitar_acerto, pattern="^pay_settle_"))

    app.add_handler(CommandHandler("extrato", handle_extrato))
    app.add_handler(CallbackQueryHandler(handle_extrato, pattern="^cmd_extrato$"))

    app.add_handler(CallbackQueryHandler(handle_main_menu, pattern="^cmd_main_menu$"))

    # 3. Registrar Error Handler Global
    app.add_error_handler(global_error_handler)

    logger.info("🚀 Bot Rubi rodando em modo Long Polling! Pressione Ctrl+C para encerrar.")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
