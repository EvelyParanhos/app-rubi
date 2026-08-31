import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from auth_manager import require_auth, get_client, is_authenticated
from handlers.auth import get_main_menu_keyboard

logger = logging.getLogger(__name__)

# Estados do Onboarding
ONBOARDING_BALANCE, ONBOARDING_CARD_NAME, ONBOARDING_CARD_LIMIT, ONBOARDING_CARD_DUE, ONBOARDING_REC_DESC, ONBOARDING_REC_AMOUNT, ONBOARDING_REC_DUE = range(7)

CATEGORY_LABELS = {
    "PETS": "🐶 Animais de Estimação",
    "BARS_AND_RESTAURANTS": "🍔 Bares e Restaurantes",
    "DELIVERY": "🛵 Delivery",
    "SHOPPING": "🛍️ Compras",
    "HOUSING": "🏠 Contas da Casa",
    "DONATIONS": "🎁 Doações",
    "EDUCATION": "📚 Educação",
    "ENTERTAINMENT": "🎬 Entretenimento",
    "TAXES_AND_FEES": "🧾 Impostos/Tarifas",
    "INVESTMENTS": "📈 Investimentos",
    "SUPERMARKET": "🛒 Mercado",
    "UNCATEGORIZED": "📦 Não categorizado",
    "HEALTH": "🏥 Saúde",
    "SERVICES": "💻 Serviços",
    "TRANSPORT": "🚗 Transporte"
}

@require_auth
async def start_onboarding(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    client = get_client(chat_id)

    # Ação silenciosa: garantir que existe pelo menos 1 conta cadastrada
    try:
        accounts = client.get_accounts()
        if not accounts:
            new_acc = client.create_account("Conta Corrente Principal", acc_type="CHECKING", is_joint=False, initial_balance=0.0)
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
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(msg_text, parse_mode="Markdown")
    else:
        await update.message.reply_text(msg_text, parse_mode="Markdown")

    return ONBOARDING_BALANCE

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

    # Oferece adicionar outro ou finalizar
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
        await query.edit_message_text(
            "🎉 **Onboarding Concluído com Sucesso!**\n\n"
            "Seu perfil financeiro foi configurado no **Rubi Financial**.\n"
            "Acesse o menu principal abaixo para usar os comandos do sistema:",
            reply_markup=get_main_menu_keyboard(),
            parse_mode="Markdown"
        )
        return ConversationHandler.END

def get_onboarding_conversation_handler():
    return ConversationHandler(
        entry_points=[
            CommandHandler("start", start_onboarding),
            CommandHandler("onboarding", start_onboarding),
            CallbackQueryHandler(start_onboarding, pattern="^cmd_onboarding$")
        ],
        states={
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
        fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)]
    )
