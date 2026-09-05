import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.request import HTTPXRequest
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)
from telegram.error import TimedOut, NetworkError

from handlers.menu import get_main_menu_keyboard
from handlers.auth import get_auth_conversation_handler
from handlers.transaction import get_transaction_conversation_handler, handle_delete_tx, execute_delete_tx
from handlers.card import get_card_conversation_handler
from handlers.settlement import handle_acerto, execute_quitar_acerto
from handlers.statement import handle_extrato, handle_main_menu, handle_previsao

load_dotenv()

# Configuração de Logging Limpo
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("RubiBot")

async def global_error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"[ERRO BOT] Exceção capturada: {context.error}")

    msg = "❌ Ocorreu um erro temporário na comunicação. Por favor, tente novamente em instantes."

    if isinstance(update, Update):
        chat_id = update.effective_chat.id if update.effective_chat else None
        
        if update.callback_query:
            try:
                await update.callback_query.answer("Ocorreu uma instabilidade. Tente novamente.", show_alert=True)
            except Exception:
                pass
            try:
                await update.callback_query.edit_message_text(msg, reply_markup=get_main_menu_keyboard())
            except Exception:
                if chat_id:
                    try:
                        await context.bot.send_message(chat_id=chat_id, text=msg, reply_markup=get_main_menu_keyboard())
                    except Exception:
                        pass
        elif update.message:
            try:
                await update.message.reply_text(msg, reply_markup=get_main_menu_keyboard())
            except Exception:
                pass

def main():
    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        logger.error("TELEGRAM_TOKEN não configurado no arquivo .env!")
        return

    logger.info("🤖 Inicializando Bot Rubi Financial (UI Cliente de Apresentação)...")

    # Requisição HTTPX resiliente com pool de conexões otimizado
    custom_request = HTTPXRequest(
        connect_timeout=15.0,
        read_timeout=20.0,
        write_timeout=15.0,
        pool_timeout=15.0
    )

    app = ApplicationBuilder().token(token).request(custom_request).build()

    # 1. Registrar ConversationHandlers de fluxos principais (Auth + Onboarding Unificados)
    app.add_handler(get_auth_conversation_handler())
    app.add_handler(get_transaction_conversation_handler())
    app.add_handler(get_card_conversation_handler())

    # 2. Registrar Handlers Diretos e Callbacks
    app.add_handler(CommandHandler("acerto", handle_acerto))
    app.add_handler(CallbackQueryHandler(handle_acerto, pattern="^cmd_acerto$"))
    app.add_handler(CallbackQueryHandler(execute_quitar_acerto, pattern="^pay_settle_"))

    app.add_handler(CommandHandler("extrato", handle_extrato))
    app.add_handler(CallbackQueryHandler(handle_extrato, pattern="^cmd_extrato$"))

    app.add_handler(CommandHandler("previsao", handle_previsao))
    app.add_handler(CallbackQueryHandler(handle_previsao, pattern="^cmd_previsao$"))

    app.add_handler(CallbackQueryHandler(handle_delete_tx, pattern="^delete_tx_"))
    app.add_handler(CallbackQueryHandler(execute_delete_tx, pattern="^confirm_del_"))

    app.add_handler(CallbackQueryHandler(handle_main_menu, pattern="^cmd_main_menu$"))

    # 3. Registrar Error Handler Global
    app.add_error_handler(global_error_handler)

    logger.info("🚀 Bot Rubi rodando em modo Long Polling! Pressione Ctrl+C para encerrar.")
    app.run_polling(drop_pending_updates=True, bootstrap_retries=10)

if __name__ == "__main__":
    main()
