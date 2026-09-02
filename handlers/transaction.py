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

# Estados do Registro e Edição de Transação
TRANS_AMOUNT, TRANS_ACCOUNT, TRANS_CATEGORY, TRANS_CONFIRM, EDIT_TX_VAL, EDIT_TX_CAT = range(6)

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

def get_category_keyboard(prefix="cat_"):
    keyboard = []
    items = list(CATEGORIES.items())
    for i in range(0, len(items), 2):
        row = []
        c1, l1 = items[i]
        row.append(InlineKeyboardButton(l1, callback_data=f"{prefix}{c1}"))
        if i + 1 < len(items):
            c2, l2 = items[i+1]
            row.append(InlineKeyboardButton(l2, callback_data=f"{prefix}{c2}"))
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
        try:
            await update.callback_query.answer()
        except Exception:
            pass
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
    try:
        await query.answer()
    except Exception:
        pass

    acc_id = query.data.replace("acc_", "")
    context.user_data["trans_account_id"] = acc_id

    await query.edit_message_text(
        "Selecione a **categoria** para esta transação:",
        reply_markup=get_category_keyboard()
    )
    return TRANS_CATEGORY

async def category_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except Exception:
        pass

    cat_code = query.data.replace("cat_", "")
    context.user_data["trans_category"] = cat_code

    return await show_confirmation(query, context, edit=True)

async def show_confirmation(target, context, edit=False):
    t_type = "Gasto (Débito)" if context.user_data.get("trans_type") == "DEBIT" else "Receita (Crédito)"
    val = context.user_data.get("trans_amount", 0.0)
    cat = context.user_data.get("trans_category", "UNCATEGORIZED")
    cat_name = CATEGORIES.get(cat, cat)

    msg_text = (
        f"📋 **Confirmação de Registro**\n\n"
        f"• **Tipo**: {t_type}\n"
        f"• **Valor Total**: R$ {val:.2f}\n"
        f"• **Categoria**: {cat_name}\n\n"
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
    try:
        await query.answer()
    except Exception:
        pass

    if query.data == "confirm_trans_no":
        await query.edit_message_text("❌ Transação cancelada.", reply_markup=get_main_menu_keyboard())
        return ConversationHandler.END

    chat_id = update.effective_chat.id
    client = get_client(chat_id)

    acc_id = context.user_data.get("trans_account_id")
    amount = context.user_data.get("trans_amount")
    trans_type = context.user_data.get("trans_type")
    category = context.user_data.get("trans_category")

    try:
        desc = "Gasto Registrado via Telegram" if trans_type == "DEBIT" else "Receita Registrada via Telegram"
        client.create_transaction(
            account_id=acc_id,
            amount=amount,
            trans_type=trans_type,
            description=desc,
            category=category
        )

        res_text = f"✅ **Transação registrada com sucesso!**\n\n💰 R$ {amount:.2f} ({CATEGORIES.get(category, category)})"

        await query.edit_message_text(res_text, reply_markup=get_main_menu_keyboard(), parse_mode="Markdown")
    except Exception as e:
        logger.error(f"[REGISTRO TRANSAÇÃO ERRO] {e}")
        await query.edit_message_text(f"❌ Não foi possível registrar a transação: {e}", reply_markup=get_main_menu_keyboard())

    return ConversationHandler.END

# --- EXCLUSÃO E EDIÇÃO DE TRANSAÇÕES ---

@require_auth
async def handle_delete_tx(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except Exception:
        pass

    tx_id = query.data.replace("delete_tx_", "")
    context.user_data["delete_tx_id"] = tx_id

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⚠️ Sim, Excluir", callback_data=f"confirm_del_{tx_id}"),
            InlineKeyboardButton("❌ Cancelar", callback_data="cmd_main_menu")
        ]
    ])

    await query.edit_message_text(
        f"⚠️ **Confirmação de Exclusão**\n\n"
        f"Tem certeza de que deseja **excluir permanentemente** a transação abaixo?\n`{tx_id}`",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

@require_auth
async def execute_delete_tx(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except Exception:
        pass

    tx_id = query.data.replace("confirm_del_", "")
    chat_id = update.effective_chat.id
    client = get_client(chat_id)

    try:
        client.delete_transaction(tx_id)
        await query.edit_message_text("✅ **Transação excluída com sucesso!**", reply_markup=get_main_menu_keyboard(), parse_mode="Markdown")
    except Exception as e:
        logger.error(f"[EXCLUSÃO TRANSAÇÃO ERRO] {e}")
        await query.edit_message_text(f"❌ Erro ao excluir transação: {e}", reply_markup=get_main_menu_keyboard())

@require_auth
async def start_edit_tx(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except Exception:
        pass

    tx_id = query.data.replace("edit_tx_", "")
    context.user_data["edit_tx_id"] = tx_id

    await query.edit_message_text(
        f"✏️ **Edição de Transação** (`{tx_id}`)\n\n"
        "Digite o **novo valor** em R$ (ex: `75.00`):",
        parse_mode="Markdown"
    )
    return EDIT_TX_VAL

async def edit_tx_val_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw_val = update.message.text.strip().replace(",", ".")
    try:
        val = float(raw_val)
        if val <= 0:
            raise ValueError()
        context.user_data["edit_tx_amount"] = val
    except ValueError:
        await update.message.reply_text("❌ Valor inválido! Digite um valor numérico positivo:")
        return EDIT_TX_VAL

    await update.message.reply_text(
        f"Novo valor: **R$ {val:.2f}**\n\nSelecione a nova **categoria**:",
        reply_markup=get_category_keyboard(prefix="editcat_"),
        parse_mode="Markdown"
    )
    return EDIT_TX_CAT

async def edit_tx_cat_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except Exception:
        pass

    cat_code = query.data.replace("editcat_", "")
    tx_id = context.user_data.get("edit_tx_id")
    new_amount = context.user_data.get("edit_tx_amount")

    chat_id = update.effective_chat.id
    client = get_client(chat_id)

    try:
        accounts = client.get_accounts()
        acc_id = accounts[0]["id"] if accounts else None

        client.update_transaction(
            transaction_id=tx_id,
            account_id=acc_id,
            amount=new_amount,
            trans_type="DEBIT",
            description="Transação Atualizada via Telegram",
            category=cat_code
        )

        cat_name = CATEGORIES.get(cat_code, cat_code)
        await query.edit_message_text(
            f"✅ **Transação atualizada com sucesso!**\n\n"
            f"• **Novo Valor**: R$ {new_amount:.2f}\n"
            f"• **Nova Categoria**: {cat_name}",
            reply_markup=get_main_menu_keyboard(),
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"[EDIÇÃO TRANSAÇÃO ERRO] {e}")
        await query.edit_message_text(f"❌ Falha ao atualizar transação: {e}", reply_markup=get_main_menu_keyboard())

    return ConversationHandler.END

def get_transaction_conversation_handler():
    return ConversationHandler(
        entry_points=[
            CommandHandler("gasto", start_gasto),
            CommandHandler("receita", start_receita),
            CallbackQueryHandler(start_gasto, pattern="^cmd_gasto$"),
            CallbackQueryHandler(start_receita, pattern="^cmd_receita$"),
            CallbackQueryHandler(start_edit_tx, pattern="^edit_tx_")
        ],
        states={
            TRANS_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, amount_received)],
            TRANS_ACCOUNT: [CallbackQueryHandler(account_selected, pattern="^acc_")],
            TRANS_CATEGORY: [CallbackQueryHandler(category_selected, pattern="^cat_")],
            TRANS_CONFIRM: [CallbackQueryHandler(confirm_decision, pattern="^confirm_trans_")],
            EDIT_TX_VAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_tx_val_received)],
            EDIT_TX_CAT: [CallbackQueryHandler(edit_tx_cat_selected, pattern="^editcat_")],
        },
        fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)]
    )
