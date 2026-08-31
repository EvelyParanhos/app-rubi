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
from auth_manager import set_session, get_client, is_authenticated

logger = logging.getLogger(__name__)

# Estados do Fluxo de Autenticação / Início
AUTH_PHONE, AUTH_PIN, AUTH_NAME = range(3)

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

async def start_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    if is_authenticated(chat_id):
        client = get_client(chat_id)
        msg_text = "💎 **Rubi Financial - Menu Principal**\n\nBem-vindo de volta! Escolha uma opção abaixo:"
        if update.callback_query:
            try:
                await update.callback_query.answer()
                await update.callback_query.edit_message_text(msg_text, reply_markup=get_main_menu_keyboard(), parse_mode="Markdown")
            except Exception:
                pass
        else:
            await update.message.reply_text(msg_text, reply_markup=get_main_menu_keyboard(), parse_mode="Markdown")
        return ConversationHandler.END

    msg_text = (
        "👋 **Bem-vindo ao Rubi Financial!**\n\n"
        "Vamos verificar se você já tem conta ou se é um **novo usuário**.\n"
        "Por favor, informe seu **número de celular com DDD** (ex: `+5571993198981` ou `71993198981`):"
    )

    if update.callback_query:
        try:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(msg_text, parse_mode="Markdown")
        except Exception:
            pass
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
        "Digite seu **PIN de 4 dígitos** para autenticar:",
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

    context.user_data["auth_pin"] = pin
    temp_client = RubiApiClient()

    # 1. Tentar Efetuar Login (Usuário Existente)
    try:
        token = temp_client.login(phone_number, pin)
        if token:
            client = set_session(chat_id, token)
            try:
                client.link_telegram(chat_id)
            except Exception:
                pass

            await update.message.reply_text(
                "✅ **Login efetuado com sucesso!**\n\n"
                "Sua conta foi identificada no **Rubi Financial**.\n"
                "Acesse as funcionalidades abaixo:",
                reply_markup=get_main_menu_keyboard(),
                parse_mode="Markdown"
            )
            return ConversationHandler.END
    except Exception as login_err:
        logger.info(f"[AUTH DETECTAR NOVO USUÁRIO] Usuário {phone_number} não encontrado para login direto ({login_err}). Direcionando para Novo Cadastro + Onboarding...")

    # 2. Usuário Novo -> Solicitar Nome para efetuar Cadastro + Onboarding
    await update.message.reply_text(
        "✨ **Novo Usuário Detectado!**\n\n"
        "Identificamos que esta é a sua primeira vez no Rubi Financial.\n"
        "Por favor, digite seu **nome completo ou apelido** para concluirmos seu cadastro:"
    )
    return AUTH_NAME

async def name_received_and_register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    phone_number = context.user_data.get("auth_phone")
    pin = context.user_data.get("auth_pin")
    chat_id = update.effective_chat.id

    temp_client = RubiApiClient()
    try:
        # Registrar
        reg_res = temp_client.register(name, phone_number, pin)
        token = reg_res.get("token") if isinstance(reg_res, dict) else None
        if not token:
            token = temp_client.login(phone_number, pin)

        client = set_session(chat_id, token)
        try:
            client.link_telegram(chat_id)
        except Exception:
            pass

        await update.message.reply_text(
            f"🎉 **Cadastro concluído com sucesso, {name}!**\n\n"
            "Seu login foi efetuado. Vamos agora iniciar o seu **Onboarding (Linha de Base)**.\n\n"
            "**Passo 1/3: Saldo Inicial**\n"
            "Qual o saldo atual da sua conta corrente principal? (ex: `1500.00` ou `0`):",
            parse_mode="Markdown"
        )

        # Transicionar para o onboarding (criar conta padrao silenciosamente)
        try:
            accs = client.get_accounts()
            if not accs:
                new_acc = client.create_account("Conta Corrente Principal", acc_type="CHECKING", is_joint=False, initial_balance=0.0)
                context.user_data["onboarding_account_id"] = new_acc.get("id")
            else:
                context.user_data["onboarding_account_id"] = accs[0]["id"]
        except Exception:
            pass

        from handlers.onboarding import ONBOARDING_BALANCE
        return ONBOARDING_BALANCE

    except Exception as reg_err:
        logger.error(f"[AUTH CADASTRO ERRO] {reg_err}")
        await update.message.reply_text(f"❌ Erro ao criar cadastro: {reg_err}\n\nTente novamente com /start.")
        return ConversationHandler.END

async def cancel_auth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Operação cancelada. Envie /start quando desejar voltar.")
    return ConversationHandler.END

def get_auth_conversation_handler():
    return ConversationHandler(
        entry_points=[
            CommandHandler("start", start_entry),
            CommandHandler("login", start_entry),
            CallbackQueryHandler(start_entry, pattern="^cmd_login$")
        ],
        states={
            AUTH_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, phone_received)],
            AUTH_PIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, pin_received)],
            AUTH_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, name_received_and_register)],
        },
        fallbacks=[CommandHandler("cancel", cancel_auth)]
    )
