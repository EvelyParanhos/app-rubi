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
from auth_manager import require_auth, get_client
from handlers.auth import get_main_menu_keyboard

logger = logging.getLogger(__name__)

# Estados do Registro de Transação
TRANS_AMOUNT, TRANS_ACCOUNT, TRANS_CATEGORY, TRANS_SPLIT, TRANS_CONFIRM = range(5)

CATEGORIES = {
    "SUPERMARKET": "🛒 Mercado",
    "BARS_AND_RESTAURANTS": "🍔 Bares e Restaurantes",
    "DELIVERY": "🛵 Delivery",
    "HOUSING": "🏠 Moradia e Contas",
    "TRANSPORT": "🚗 Transporte e Veículo",
    "HEALTH": "🏥 Saúde",
    "EDUCATION": "📚 Educação",
    "ENTERTAINMENT": "🎬 Entretenimento",
    "SHOPPING": "🛍️ Compras",
    "SERVICES": "🛠️ Serviços",
    "INVESTMENTS": "📈 Investimentos",
    "UNCATEGORIZED": "📦 Não Categorizado"
}

def get_category_keyboard():
    keyboard = []
    items = list(CATEGORIES.items())
    for i in range(0, len(items), 2):
        row = []
        c1, l1 = items[i]
        row.append(InlineKeyboardButton(l1, callback_data=f"cat_{c1}"))
        if i + 1 < len(items):
            c2, l2 = items[i+1]
            row.append(InlineKeyboardButton(l2, callback_data=f"cat_{c2}"))
        keyboard.append(row)
    return InlineKeyboardMarkup(keyboard)

@require_auth
async def start_gasto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["trans_type"] = "DEBIT"
    return await prompt_amount(update, context, "💸 **Novo Gasto (Despesa)**")

@require_auth
async def start_receita(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["trans_type"] = "CREDIT"
    return await prompt_amount(update, context, "📥 **Nova Receita (Entrada)**")

async def prompt_amount(update, context, title):
    msg_text = f"{title}\n\nDigite o **valor** em R$ (ex: `45.50` ou `45,50`):"
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(msg_text, parse_mode="Markdown")
    else:
        await update.message.reply_text(msg_text, parse_mode="Markdown")
    return TRANS_AMOUNT

async def amount_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw_val = update.message.text.strip().replace(",", ".")
    chat_id = update.effective_chat.id
    client = get_client(chat_id)

    try:
        val = float(raw_val)
        if val <= 0:
            raise ValueError()
        context.user_data["trans_amount"] = val
    except ValueError:
        await update.message.reply_text("❌ Valor inválido! Digite um valor numérico positivo (ex: `50.00`):")
        return TRANS_AMOUNT

    # Buscar contas para botões inline dinâmicos
    accounts = client.get_accounts()
    if not accounts:
        await update.message.reply_text("❌ Nenhuma conta cadastrada! Crie uma conta no menu principal antes de registrar despesas.")
        return ConversationHandler.END

    keyboard = []
    for acc in accounts:
        name = acc.get("name", "Conta")
        bal = acc.get("balance", 0.0)
        keyboard.append([InlineKeyboardButton(f"🏦 {name} (R$ {bal:.2f})", callback_data=f"acc_{acc['id']}")])

    t_type = "Gasto" if context.user_data.get("trans_type") == "DEBIT" else "Receita"
    await update.message.reply_text(
        f"{t_type}: **R$ {val:.2f}**\n\nSelecione a **conta** para esta operação:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return TRANS_ACCOUNT

async def account_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    acc_id = query.data.replace("acc_", "")
    context.user_data["trans_account_id"] = acc_id

    await query.edit_message_text(
        "Selecione a **categoria** para esta transação:",
        reply_markup=get_category_keyboard()
    )
    return TRANS_CATEGORY

async def category_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    cat_code = query.data.replace("cat_", "")
    context.user_data["trans_category"] = cat_code

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🤝 Dividir 50/50", callback_data="split_50"),
            InlineKeyboardButton("✏️ Outro Valor", callback_data="split_custom")
        ],
        [InlineKeyboardButton("👤 Apenas Meu", callback_data="split_none")]
    ])

    await query.edit_message_text(
        "Deseja realizar o **rateio de casal** para esta despesa?",
        reply_markup=keyboard
    )
    return TRANS_SPLIT

async def split_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    choice = query.data
    amount = context.user_data.get("trans_amount", 0.0)

    if choice == "split_50":
        context.user_data["trans_split_amount"] = amount / 2.0
    elif choice == "split_none":
        context.user_data["trans_split_amount"] = 0.0
    elif choice == "split_custom":
        await query.edit_message_text(f"Digite o **valor em R$** que cabe ao seu parceiro(a) (de R$ 0.00 até R$ {amount:.2f}):")
        return TRANS_SPLIT

    return await show_confirmation(query, context, edit=True)

async def custom_split_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw_val = update.message.text.strip().replace(",", ".")
    amount = context.user_data.get("trans_amount", 0.0)

    try:
        val = float(raw_val)
        if val < 0 or val > amount:
            raise ValueError()
        context.user_data["trans_split_amount"] = val
    except ValueError:
        await update.message.reply_text(f"❌ Valor inválido. Digite um valor entre 0 e {amount:.2f}:")
        return TRANS_SPLIT

    return await show_confirmation(update.message, context, edit=False)

async def show_confirmation(target, context, edit=False):
    t_type = "Gasto (Débito)" if context.user_data.get("trans_type") == "DEBIT" else "Receita (Crédito)"
    val = context.user_data.get("trans_amount", 0.0)
    cat = context.user_data.get("trans_category", "UNCATEGORIZED")
    cat_name = CATEGORIES.get(cat, cat)
    split_amt = context.user_data.get("trans_split_amount", 0.0)

    msg_text = (
        f"📋 **Confirmação de Registro**\n\n"
        f"• **Tipo**: {t_type}\n"
        f"• **Valor Total**: R$ {val:.2f}\n"
        f"• **Categoria**: {cat_name}\n"
        f"• **Rateio Parceiro(a)**: R$ {split_amt:.2f}\n\n"
        f"Deseja efetivar o registro?"
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Confirmar", callback_data="confirm_trans_yes"),
            InlineKeyboardButton("❌ Cancelar", callback_data="confirm_trans_no")
        ]
    ])

    if edit:
        await target.edit_message_text(msg_text, reply_markup=keyboard, parse_mode="Markdown")
    else:
        await target.reply_text(msg_text, reply_markup=keyboard, parse_mode="Markdown")

    return TRANS_CONFIRM

async def confirm_decision(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "confirm_trans_no":
        await query.edit_message_text("❌ Transação cancelada.", reply_markup=get_main_menu_keyboard())
        return ConversationHandler.END

    chat_id = update.effective_chat.id
    client = get_client(chat_id)

    acc_id = context.user_data.get("trans_account_id")
    amount = context.user_data.get("trans_amount")
    trans_type = context.user_data.get("trans_type")
    category = context.user_data.get("trans_category")
    split_amt = context.user_data.get("trans_split_amount", 0.0)

    try:
        desc = "Gasto Registrado via Telegram" if trans_type == "DEBIT" else "Receita Registrada via Telegram"
        res = client.create_transaction(
            account_id=acc_id,
            amount=amount,
            trans_type=trans_type,
            description=desc,
            category=category
        )

        res_text = f"✅ **Transação registrada com sucesso!**\n\n💰 R$ {amount:.2f} ({CATEGORIES.get(category, category)})"
        if split_amt > 0:
            res_text += f"\n🤝 Rateio flexível de R$ {split_amt:.2f} computado no acerto do casal."

        await query.edit_message_text(res_text, reply_markup=get_main_menu_keyboard(), parse_mode="Markdown")
    except Exception as e:
        logger.error(f"[REGISTRO TRANSAÇÃO ERRO] {e}")
        await query.edit_message_text(f"❌ Não foi possível registrar a transação: {e}", reply_markup=get_main_menu_keyboard())

    return ConversationHandler.END

def get_transaction_conversation_handler():
    return ConversationHandler(
        entry_points=[
            CommandHandler("gasto", start_gasto),
            CommandHandler("receita", start_receita),
            CallbackQueryHandler(start_gasto, pattern="^cmd_gasto$"),
            CallbackQueryHandler(start_receita, pattern="^cmd_receita$")
        ],
        states={
            TRANS_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, amount_received)],
            TRANS_ACCOUNT: [CallbackQueryHandler(account_selected, pattern="^acc_")],
            TRANS_CATEGORY: [CallbackQueryHandler(category_selected, pattern="^cat_")],
            TRANS_SPLIT: [
                CallbackQueryHandler(split_selected, pattern="^split_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, custom_split_received)
            ],
            TRANS_CONFIRM: [CallbackQueryHandler(confirm_decision, pattern="^confirm_trans_")],
        },
        fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)]
    )
