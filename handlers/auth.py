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
from handlers.menu import get_main_menu_keyboard

logger = logging.getLogger(__name__)

# Estados Unificados (Auth + Onboarding)
(
    AUTH_PHONE,
    AUTH_PIN,
    AUTH_NAME,
    ONBOARDING_BALANCE,
    ONBOARDING_CARD_NAME,
    ONBOARDING_CARD_LIMIT,
    ONBOARDING_CARD_DUE,
    ONBOARDING_REC_DESC,
    ONBOARDING_REC_AMOUNT,
    ONBOARDING_REC_DUE,
) = range(10)

async def start_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    if is_authenticated(chat_id):
        client = get_client(chat_id)
        try:
            profile = client.get_user_profile()
            onboarding_completed = profile.get("onboarding_completed", False) if isinstance(profile, dict) else True
        except Exception:
            onboarding_completed = True

        if not onboarding_completed:
            return await trigger_onboarding_start(update, context, client)

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

async def trigger_onboarding_start(update: Update, context: ContextTypes.DEFAULT_TYPE, client):
    try:
        accounts = client.get_accounts()
        if not accounts:
            new_acc = client.create_account("Conta Corrente Principal", acc_type="CHECKING", initial_balance=0.0)
            context.user_data["onboarding_account_id"] = new_acc.get("id")
        else:
            context.user_data["onboarding_account_id"] = accounts[0]["id"]
    except Exception as e:
        logger.error(f"[ONBOARDING CONTA] {e}")

    msg_text = (
        "🚀 **Bem-vindo ao Onboarding do Rubi Financial!**\n\n"
        "Vamos configurar sua linha de base em 3 passos simples:\n\n"
        "**Passo 1/3: Saldo Inicial**\n"
        "Qual o saldo atual estimado da sua conta corrente principal? (ex: `1500.00` ou `0`):"
    )

    if update.callback_query:
        try:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(msg_text, parse_mode="Markdown")
        except Exception:
            pass
    else:
        await update.message.reply_text(msg_text, parse_mode="Markdown")

    return ONBOARDING_BALANCE

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

            # Checar onboardingCompletedAt via GET /users/me
            try:
                profile = client.get_user_profile()
                onboarding_completed = profile.get("onboarding_completed", False) if isinstance(profile, dict) else True
            except Exception:
                onboarding_completed = True

            if not onboarding_completed:
                return await trigger_onboarding_start(update, context, client)

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

    # 2. Usuário Novo -> Solicitar Nome
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
            "Seu login foi efetuado. Vamos agora iniciar o seu **Onboarding (Linha de Base)**."
        )

        return await trigger_onboarding_start(update, context, client)

    except Exception as reg_err:
        logger.error(f"[AUTH CADASTRO ERRO] {reg_err}")
        await update.message.reply_text(f"❌ Erro ao criar cadastro: {reg_err}\n\nTente novamente com /start.")
        return ConversationHandler.END

# --- PASSOS DE ONBOARDING ---
async def balance_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    client = get_client(chat_id)
    raw_val = update.message.text.strip().replace(",", ".")

    try:
        val = float(raw_val)
        acc_id = context.user_data.get("onboarding_account_id")
        if val > 0 and acc_id:
            client.create_transaction(
                account_id=acc_id,
                amount=val,
                trans_type="CREDIT",
                description="Saldo Inicial",
                category="UNCATEGORIZED"
            )
    except ValueError:
        await update.message.reply_text("❌ Valor inválido! Digite apenas números (ex: `2500.00`):", parse_mode="Markdown")
        return ONBOARDING_BALANCE
    except Exception as e:
        logger.error(f"[ONBOARDING TRANSAÇÃO INICIAL] {e}")

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⏩ Pular Configuração de Cartão", callback_data="skip_card")]
    ])

    await update.message.reply_text(
        "✅ Saldo inicial registrado!\n\n"
        "**Passo 2/3: Cartão de Crédito Principal**\n"
        "Digite o **nome/apelido** do seu cartão de crédito (ex: `Nubank`, `XP`):",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    return ONBOARDING_CARD_NAME

async def skip_card_clicked(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    return await ask_recurring_step(query, context, edit_message=True)

async def card_name_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    card_name = update.message.text.strip()
    context.user_data["onboarding_card_name"] = card_name

    await update.message.reply_text(
        f"Cartão: **{card_name}**\n\n"
        "Informe o **limite total** do cartão em R$ (ex: `5000.00`):",
        parse_mode="Markdown"
    )
    return ONBOARDING_CARD_LIMIT

async def card_limit_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw_val = update.message.text.strip().replace(",", ".")
    try:
        limit = float(raw_val)
        context.user_data["onboarding_card_limit"] = limit
    except ValueError:
        await update.message.reply_text("❌ Limite inválido. Digite um número positivo (ex: `5000.00`):")
        return ONBOARDING_CARD_LIMIT

    await update.message.reply_text(
        "Qual o **dia de vencimento** da fatura deste cartão? (digite um dia de 1 a 31):"
    )
    return ONBOARDING_CARD_DUE

async def card_due_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    client = get_client(chat_id)
    raw_day = update.message.text.strip()

    try:
        due_day = int(raw_day)
        if due_day < 1 or due_day > 31:
            raise ValueError()
        closing_day = max(1, due_day - 7)

        acc_id = context.user_data.get("onboarding_account_id")
        card_name = context.user_data.get("onboarding_card_name", "Cartão Principal")
        limit = context.user_data.get("onboarding_card_limit", 1000.0)

        client.create_credit_card(
            account_id=acc_id,
            name=card_name,
            credit_limit=limit,
            closing_day=closing_day,
            due_day=due_day
        )
        await update.message.reply_text("✅ Cartão de crédito cadastrado com sucesso!")
    except ValueError:
        await update.message.reply_text("❌ Dia inválido. Digite um número entre 1 e 31:")
        return ONBOARDING_CARD_DUE
    except Exception as e:
        logger.error(f"[ONBOARDING CRIAR CARTÃO] {e}")

    return await ask_recurring_step(update.message, context, edit_message=False)

async def ask_recurring_step(target, context, edit_message=False):
    msg_text = (
        "**Passo 3/3: Gastos Fixos Recorrentes**\n\n"
        "Cadastre seus compromissos mensais (Aluguel, Luz, Internet, etc).\n\n"
        "Digite a **descrição** do primeiro gasto fixo (ou clique em **Finalizar** caso não tenha mais nenhum):"
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Finalizar Onboarding", callback_data="finish_onboarding")]
    ])

    if edit_message:
        await target.edit_message_text(msg_text, reply_markup=keyboard, parse_mode="Markdown")
    else:
        await target.reply_text(msg_text, reply_markup=keyboard, parse_mode="Markdown")

    return ONBOARDING_REC_DESC

async def rec_desc_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    desc = update.message.text.strip()
    context.user_data["onboarding_rec_desc"] = desc

    await update.message.reply_text(
        f"Gasto Fixo: **{desc}**\n\n"
        "Qual o **valor mensal** em R$? (ex: `1200.00`):",
        parse_mode="Markdown"
    )
    return ONBOARDING_REC_AMOUNT

async def rec_amount_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw_val = update.message.text.strip().replace(",", ".")
    try:
        amount = float(raw_val)
        context.user_data["onboarding_rec_amount"] = amount
    except ValueError:
        await update.message.reply_text("❌ Valor inválido! Digite um número (ex: `150.00`):")
        return ONBOARDING_REC_AMOUNT

    await update.message.reply_text(
        "Qual o **dia de vencimento** mensal deste gasto? (1 a 31):"
    )
    return ONBOARDING_REC_DUE

async def rec_due_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    client = get_client(chat_id)
    raw_day = update.message.text.strip()

    try:
        due_day = int(raw_day)
        if due_day < 1 or due_day > 31:
            raise ValueError()

        acc_id = context.user_data.get("onboarding_account_id")
        desc = context.user_data.get("onboarding_rec_desc")
        amount = context.user_data.get("onboarding_rec_amount")

        client.create_recurring_transaction(
            account_id=acc_id,
            description=desc,
            amount=amount,
            rec_type="EXPENSE",
            due_day=due_day,
            category="HOUSING"
        )
        await update.message.reply_text(f"✅ Gasto fixo **{desc}** (R$ {amount:.2f}) cadastrado!")
    except ValueError:
        await update.message.reply_text("❌ Dia inválido. Informe um número entre 1 e 31:")
        return ONBOARDING_REC_DUE
    except Exception as e:
        logger.error(f"[ONBOARDING CRIAR RECORRÊNCIA] {e}")

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Adicionar Outro Gasto Fixo", callback_data="add_another_rec")],
        [InlineKeyboardButton("✅ Finalizar Onboarding", callback_data="finish_onboarding")]
    ])
    await update.message.reply_text("Deseja cadastrar mais algum gasto fixo?", reply_markup=keyboard)
    return ONBOARDING_REC_DESC

async def onboarding_loop_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "add_another_rec":
        await query.edit_message_text("Digite a **descrição** do próximo gasto fixo:", parse_mode="Markdown")
        return ONBOARDING_REC_DESC
    elif query.data == "finish_onboarding":
        chat_id = update.effective_chat.id
        client = get_client(chat_id)
        try:
            client.complete_onboarding()
        except Exception as e:
            logger.error(f"[COMPLETE ONBOARDING ERROR] {e}")

        await query.edit_message_text(
            "🎉 **Onboarding Concluído com Sucesso!**\n\n"
            "Seu perfil financeiro foi configurado no **Rubi Financial**.\n"
            "Acesse o menu principal abaixo para usar os comandos do sistema:",
            reply_markup=get_main_menu_keyboard(),
            parse_mode="Markdown"
        )
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
            ONBOARDING_BALANCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, balance_received)],
            ONBOARDING_CARD_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, card_name_received),
                CallbackQueryHandler(skip_card_clicked, pattern="^skip_card$")
            ],
            ONBOARDING_CARD_LIMIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, card_limit_received)],
            ONBOARDING_CARD_DUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, card_due_received)],
            ONBOARDING_REC_DESC: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, rec_desc_received),
                CallbackQueryHandler(onboarding_loop_callback, pattern="^(add_another_rec|finish_onboarding)$")
            ],
            ONBOARDING_REC_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, rec_amount_received)],
            ONBOARDING_REC_DUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, rec_due_received)],
        },
        fallbacks=[CommandHandler("cancel", cancel_auth)]
    )
