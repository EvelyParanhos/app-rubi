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

# Estados do Pagamento de Fatura
CARD_SELECT, INVOICE_STATUS, PAY_ACCOUNT = range(3)

@require_auth
async def start_fatura(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    client = get_client(chat_id)

    try:
        cards = client.get_credit_cards()
        if not cards:
            msg_text = "💳 **Você não possui nenhum cartão de crédito cadastrado.**\n\nCadastre um cartão no menu onboarding para gerenciar faturas."
            if update.callback_query:
                await update.callback_query.answer()
                await update.callback_query.edit_message_text(msg_text, reply_markup=get_main_menu_keyboard(), parse_mode="Markdown")
            else:
                await update.message.reply_text(msg_text, reply_markup=get_main_menu_keyboard(), parse_mode="Markdown")
            return ConversationHandler.END

        keyboard = []
        for card in cards:
            c_name = card.get("name", "Cartão")
            c_inv = card.get("current_invoice_amount", 0.0)
            keyboard.append([InlineKeyboardButton(f"💳 {c_name} (Fatura: R$ {c_inv:.2f})", callback_data=f"card_{card['id']}")])

        msg_text = "💳 **Pagamento de Fatura de Cartão**\n\nSelecione o cartão de crédito:"
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(msg_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        else:
            await update.message.reply_text(msg_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

        return CARD_SELECT
    except Exception as e:
        logger.error(f"[FATURA LISTAR CARTÕES ERRO] {e}")
        err_msg = f"❌ Erro ao buscar cartões de crédito: {e}"
        if update.callback_query:
            await update.callback_query.edit_message_text(err_msg, reply_markup=get_main_menu_keyboard())
        else:
            await update.message.reply_text(err_msg, reply_markup=get_main_menu_keyboard())
        return ConversationHandler.END

async def card_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    card_id = query.data.replace("card_", "")
    context.user_data["pay_card_id"] = card_id

    chat_id = update.effective_chat.id
    client = get_client(chat_id)

    try:
        invoices = client.get_card_invoices(card_id)
        if not invoices:
            await query.edit_message_text("ℹ️ Não foram encontradas faturas abertas para este cartão.", reply_markup=get_main_menu_keyboard())
            return ConversationHandler.END

        # Fatura atual (primeira da lista)
        current_inv = invoices[0]
        context.user_data["pay_invoice_id"] = current_inv["id"]
        total_amount = current_inv.get("total_amount", 0.0)
        context.user_data["pay_total_amount"] = total_amount

        msg_text = (
            f"📄 **Fatura Atual ({current_inv.get('reference_month', '')})**\n\n"
            f"• **Valor Total da Fatura**: R$ {total_amount:.2f}\n"
            f"• **Status**: {current_inv.get('status', 'OPEN')}\n\n"
            f"Qual o **valor** que você deseja pagar agora em R$? (ex: `{total_amount:.2f}`):"
        )
        await query.edit_message_text(msg_text, parse_mode="Markdown")
        return INVOICE_STATUS
    except Exception as e:
        logger.error(f"[FATURA STATUS ERRO] {e}")
        await query.edit_message_text(f"❌ Não foi possível carregar a fatura: {e}", reply_markup=get_main_menu_keyboard())
        return ConversationHandler.END

async def pay_amount_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw_val = update.message.text.strip().replace(",", ".")
    total_amount = context.user_data.get("pay_total_amount", 0.0)

    try:
        val = float(raw_val)
        if val <= 0:
            raise ValueError()
        context.user_data["pay_amount"] = val
    except ValueError:
        await update.message.reply_text("❌ Valor inválido. Digite um valor numérico positivo:")
        return INVOICE_STATUS

    chat_id = update.effective_chat.id
    client = get_client(chat_id)

    # Buscar contas correntes/poupança para débito do pagamento
    accounts = client.get_accounts()
    liquid_accounts = [a for a in accounts if a.get("type") in ("CHECKING", "SAVINGS")]

    if not liquid_accounts:
        await update.message.reply_text("❌ Nenhuma conta corrente/poupança encontrada para debitar o pagamento.")
        return ConversationHandler.END

    keyboard = []
    for acc in liquid_accounts:
        name = acc.get("name", "Conta")
        bal = acc.get("balance", 0.0)
        keyboard.append([InlineKeyboardButton(f"🏦 {name} (Saldo: R$ {bal:.2f})", callback_data=f"payacc_{acc['id']}")])

    is_partial = val < total_amount
    warning = ""
    if is_partial:
        warning = f"\n⚠️ **Aviso de Pagamento Parcial (RN09)**: O valor restante (R$ {total_amount - val:.2f}) será rolado automaticamente para a próxima fatura com encargos da instituição.\n"

    await update.message.reply_text(
        f"Pagamento de Fatura: **R$ {val:.2f}**{warning}\n"
        f"Selecione a **conta de origem** para o débito:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return PAY_ACCOUNT

async def pay_account_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    source_acc_id = query.data.replace("payacc_", "")
    invoice_id = context.user_data.get("pay_invoice_id")
    pay_amount = context.user_data.get("pay_amount", 0.0)
    total_amount = context.user_data.get("pay_total_amount", 0.0)

    chat_id = update.effective_chat.id
    client = get_client(chat_id)

    try:
        client.pay_invoice(
            invoice_id=invoice_id,
            source_account_id=source_acc_id,
            amount=pay_amount
        )

        res_msg = f"✅ **Pagamento de fatura efetuado com sucesso!**\n\n💰 Valor pago: **R$ {pay_amount:.2f}**"
        if pay_amount < total_amount:
            res_msg += f"\nℹ️ O saldo remanescente de R$ {total_amount - pay_amount:.2f} foi rolado para a próxima fatura."

        await query.edit_message_text(res_msg, reply_markup=get_main_menu_keyboard(), parse_mode="Markdown")
    except Exception as e:
        logger.error(f"[PAGAMENTO FATURA ERRO] {e}")
        await query.edit_message_text(f"❌ Falha ao processar pagamento da fatura: {e}", reply_markup=get_main_menu_keyboard())

    return ConversationHandler.END

def get_card_conversation_handler():
    return ConversationHandler(
        entry_points=[
            CommandHandler("fatura", start_fatura),
            CallbackQueryHandler(start_fatura, pattern="^cmd_fatura$")
        ],
        states={
            CARD_SELECT: [CallbackQueryHandler(card_selected, pattern="^card_")],
            INVOICE_STATUS: [MessageHandler(filters.TEXT & ~filters.COMMAND, pay_amount_received)],
            PAY_ACCOUNT: [CallbackQueryHandler(pay_account_selected, pattern="^payacc_")],
        },
        fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)]
    )
