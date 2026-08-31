import logging
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from rubi_api import RubiApiClient
from auth_manager import set_session, get_client

logger = logging.getLogger(__name__)

# Estados do Fluxo de Autenticação
AUTH_PHONE, AUTH_PIN = range(2)

def get_main_menu_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💸 Registrar Gasto", callback_data="cmd_gasto"),
            InlineKeyboardButton("📥 Registrar Receita", callback_data="cmd_receita"),
        ],
        [
            InlineKeyboardButton("💳 Fatura do Cartão", callback_data="cmd_fatura"),
            InlineKeyboardButton("🤝 Acerto do Casal", callback_data="cmd_acerto"),
        ],
        [
            InlineKeyboardButton("📊 Extrato do Mês", callback_data="cmd_extrato"),
            InlineKeyboardButton("🚀 Iniciar Onboarding", callback_data="cmd_onboarding"),
        ]
    ])

async def start_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg_text = (
        "🔑 **Autenticação Rubi Financial**\n\n"
        "Por favor, informe seu número de **celular com DDD** (exemplo: `+5571993198981` ou `71993198981`):"
    )
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(msg_text, parse_mode="Markdown")
    else:
        await update.message.reply_text(msg_text, parse_mode="Markdown")
    return AUTH_PHONE

async def phone_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw_phone = update.message.text.strip()
    digits = re.sub(r"\D", "", raw_phone)

    if len(digits) < 10 or len(digits) > 15:
        await update.message.reply_text("❌ Número de telefone inválido. Informe o DDD e o número completo (ex: `71993198981`):", parse_mode="Markdown")
        return AUTH_PHONE

    if not raw_phone.startswith("+"):
        if digits.startswith("55"):
            phone_number = f"+{digits}"
        else:
            phone_number = f"+55{digits}"
    else:
        phone_number = raw_phone

    context.user_data["auth_phone"] = phone_number

    await update.message.reply_text(
        f"📱 Telefone informado: **{phone_number}**\n\n"
        "Agora, digite o seu **PIN de 4 dígitos**:",
        parse_mode="Markdown"
    )
    return AUTH_PIN

async def pin_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pin = update.message.text.strip()
    phone_number = context.user_data.get("auth_phone")
    chat_id = update.effective_chat.id

    if not pin.isdigit() or len(pin) != 4:
        await update.message.reply_text("❌ O PIN deve conter exatamente 4 números. Digite novamente:")
        return AUTH_PIN

    temp_client = RubiApiClient()
    try:
        token = temp_client.ensure_login(phone_number=phone_number, pin=pin)
        if token:
            client = set_session(chat_id, token)
            try:
                client.link_telegram(chat_id)
                logger.info(f"[AUTH LOGIN] Conta do Telegram vinculada para chat_id {chat_id}")
            except Exception as link_err:
                logger.warning(f"[AUTH LOGIN] Aviso ao vincular Telegram: {link_err}")

            await update.message.reply_text(
                "✅ **Autenticação efetuada com sucesso!**\n\n"
                "Sua conta do Telegram está conectada ao ecossistema **Rubi Financial**.\n"
                "Escolha uma opção no menu abaixo para começar:",
                reply_markup=get_main_menu_keyboard(),
                parse_mode="Markdown"
            )
            return ConversationHandler.END
        else:
            await update.message.reply_text("❌ Falha na autenticação. Verifique seu telefone e PIN e tente novamente com /login.")
            return ConversationHandler.END
    except Exception as e:
        logger.error(f"[AUTH LOGIN ERRO] {e}")
        await update.message.reply_text(f"❌ Não foi possível realizar o login: {e}\n\nTente novamente com /login.")
        return ConversationHandler.END

async def cancel_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Operação de login cancelada. Envie /login quando quiser entrar.")
    return ConversationHandler.END

def get_auth_conversation_handler():
    return ConversationHandler(
        entry_points=[
            CommandHandler("login", start_login),
            CallbackQueryHandler(start_login, pattern="^cmd_login$")
        ],
        states={
            AUTH_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, phone_received)],
            AUTH_PIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, pin_received)],
        },
        fallbacks=[CommandHandler("cancel", cancel_login)]
    )
