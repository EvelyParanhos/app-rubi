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
from handlers.menu import get_main_menu_keyboard

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
                try:
                    await update.callback_query.answer()
                except Exception:
                    pass
                await update.callback_query.edit_message_text(msg_text, reply_markup=get_main_menu_keyboard(), parse_mode="Markdown")
            else:
                await update.message.reply_text(msg_text, reply_markup=get_main_menu_keyboard(), parse_mode="Markdown")
            return ConversationHandler.END

        keyboard = []
        for card in cards:
            c_name = card.get("name", "Cartão")
            c_inv = card.get("current_invoice_amount", 0.0)
            keyboard.append([InlineKeyboardButton(f"💳 {c_name} (Fatura: R$ {c_inv:.2f})", callback_data=f"card_{card['id']}")])

        msg_text = "💳 **Pagamento e Detalhamento de Fatura**\n\nSelecione o cartão de crédito:"
        if update.callback_query:
            try:
                await update.callback_query.answer()
            except Exception:
                pass
            await update.callback_query.edit_message_text(msg_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        else:
            await update.message.reply_text(msg_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

        return CARD_SELECT
    except Exception as e:
        logger.error(f"[FATURA LISTAR CARTÕES ERRO] {e}")
        err_msg = f"❌ Erro ao buscar cartões de crédito: {e}"
        if update.callback_query:
            try:
                await update.callback_query.answer()
            except Exception:
                pass
            await update.callback_query.edit_message_text(err_msg, reply_markup=get_main_menu_keyboard())
        else:
            await update.message.reply_text(err_msg, reply_markup=get_main_menu_keyboard())
        return ConversationHandler.END

async def card_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except Exception:
        pass

    card_id = query.data.replace("card_", "")
    context.user_data["pay_card_id"] = card_id

    chat_id = update.effective_chat.id
    client = get_client(chat_id)

    try:
        invoices = client.get_card_invoices(card_id)
        if not invoices:
            await query.edit_message_text("ℹ️ Não foram encontradas faturas abertas para este cartão.", reply_markup=get_main_menu_keyboard())
            return ConversationHandler.END

        # Fatura atual
        current_inv = invoices[0]
        inv_id = current_inv["id"]
        context.user_data["pay_invoice_id"] = inv_id
        total_amount = current_inv.get("total_amount", 0.0)
        context.user_data["pay_total_amount"] = total_amount

        # Detalhar itens da fatura via GET /invoices/{id}
        detailed_inv = client.get_invoice_by_id(inv_id)
        items = detailed_inv.get("items", []) if isinstance(detailed_inv, dict) else []

        lines = [
            f"📄 **Fatura do Cartão: {current_inv.get('credit_card_name', 'Cartão')}** ({current_inv.get('reference_month', '')})\n",
            "🛍️ **Itens que compõem esta fatura:**"
        ]

        if items:
            for item in items:
                desc = item.get("description", "Compra")
                amt = item.get("amount", 0.0)
                inst_num = item.get("installment_number")
                tot_inst = item.get("total_installments")
                inst_info = f" ({inst_num}/{tot_inst})" if inst_num and tot_inst else ""
                lines.append(f"• **{desc}**: R$ {amt:.2f}{inst_info}")
        else:
            lines.append("• Nenhum item individual registrado nesta fatura.")

        lines.append(f"\n📊 **Valor Total da Fatura**: **R$ {total_amount:.2f}**")
        lines.append(f"📌 **Status**: `{current_inv.get('status', 'OPEN')}`\n")
        lines.append("Qual valor você deseja pagar?")

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(f"💳 Pagar Total (R$ {total_amount:.2f})", callback_data=f"pay_full_{total_amount}"),
                InlineKeyboardButton("✏️ Pagar Parcial", callback_data="pay_custom")
            ],
            [InlineKeyboardButton("🔙 Voltar ao Menu", callback_data="cmd_main_menu")]
        ])

        await query.edit_message_text("\n".join(lines), reply_markup=keyboard, parse_mode="Markdown")
        return INVOICE_STATUS
    except Exception as e:
        logger.error(f"[FATURA STATUS ERRO] {e}")
        await query.edit_message_text(f"❌ Não foi possível carregar o detalhamento da fatura: {e}", reply_markup=get_main_menu_keyboard())
        return ConversationHandler.END

async def pay_mode_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except Exception:
        pass

    data = query.data
    total_amount = context.user_data.get("pay_total_amount", 0.0)

    if data.startswith("pay_full_"):
        val = float(data.replace("pay_full_", ""))
        context.user_data["pay_amount"] = val
        return await prompt_account_selection(query, context, edit=True)
    elif data == "pay_custom":
        await query.edit_message_text(f"Digite o **valor em R$** que você deseja pagar nesta fatura (ex: `100.00` de R$ {total_amount:.2f}):")
        return INVOICE_STATUS

async def pay_amount_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw_val = update.message.text.strip().replace(",", ".")
    try:
        val = float(raw_val)
        if val <= 0:
            raise ValueError()
        context.user_data["pay_amount"] = val
    except ValueError:
        await update.message.reply_text("❌ Valor inválido. Digite um valor numérico positivo:")
        return INVOICE_STATUS

    return await prompt_account_selection(update.message, context, edit=False)

async def prompt_account_selection(target, context, edit=False):
    val = context.user_data.get("pay_amount", 0.0)
    total_amount = context.user_data.get("pay_total_amount", 0.0)
    chat_id = context._chat_id if hasattr(context, "_chat_id") else None

    client = get_client(target.chat.id if hasattr(target, "chat") else target.message.chat.id)
    accounts = client.get_accounts()
    liquid_accounts = [a for a in accounts if a.get("type") in ("CHECKING", "SAVINGS")]

    if not liquid_accounts:
        msg = "❌ Nenhuma conta corrente/poupança encontrada para debitar o pagamento."
        if edit:
            await target.edit_message_text(msg, reply_markup=get_main_menu_keyboard())
        else:
            await target.reply_text(msg, reply_markup=get_main_menu_keyboard())
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

    msg_text = (
        f"Pagamento de Fatura: **R$ {val:.2f}**{warning}\n"
        f"Selecione a **conta de origem** para o débito:"
    )

    if edit:
        await target.edit_message_text(msg_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    else:
        await target.reply_text(msg_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    return PAY_ACCOUNT

async def pay_account_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except Exception:
        pass

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
            CommandHandler("cartoes", start_fatura),
            CallbackQueryHandler(start_fatura, pattern="^(cmd_fatura|cmd_cartoes)$")
        ],
        states={
            CARD_SELECT: [CallbackQueryHandler(card_selected, pattern="^card_")],
            INVOICE_STATUS: [
                CallbackQueryHandler(pay_mode_selected, pattern="^pay_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, pay_amount_received)
            ],
            PAY_ACCOUNT: [CallbackQueryHandler(pay_account_selected, pattern="^payacc_")],
        },
        fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)]
    )
