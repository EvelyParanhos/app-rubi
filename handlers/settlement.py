import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)
from auth_manager import require_auth, get_client
from handlers.auth import get_main_menu_keyboard

logger = logging.getLogger(__name__)

@require_auth
async def handle_acerto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    client = get_client(chat_id)

    try:
        res = client.get_net_balance()
        net_amt = res.get("net_amount", 0.0)
        c_name = res.get("creditor_name", "Credor")
        d_name = res.get("debtor_name", "Devedor")
        month = res.get("month", "mês atual")

        if net_amt > 0:
            msg_text = (
                f"🤝 **Acerto de Contas do Casal ({month})**\n\n"
                f"💰 **{d_name}** deve transferir **R$ {net_amt:.2f}** para **{c_name}**!\n\n"
                "Para liquidar esta pendência e zerar o saldo do casal, clique no botão abaixo:"
            )
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("💸 Quitar Acerto do Mês", callback_data=f"pay_settle_{month}")],
                [InlineKeyboardButton("🔙 Menu Principal", callback_data="cmd_main_menu")]
            ])
        else:
            msg_text = (
                f"🎉 **Tudo em dia no mês ({month})!**\n\n"
                "Não existem pendências financeiras acumuladas entre o casal no momento."
            )
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Menu Principal", callback_data="cmd_main_menu")]
            ])

        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(msg_text, reply_markup=keyboard, parse_mode="Markdown")
        else:
            await update.message.reply_text(msg_text, reply_markup=keyboard, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"[ACERTO NET BALANCE ERRO] {e}")
        err_msg = f"❌ Não foi possível calcular o acerto de contas: {e}"
        if update.callback_query:
            await update.callback_query.edit_message_text(err_msg, reply_markup=get_main_menu_keyboard())
        else:
            await update.message.reply_text(err_msg, reply_markup=get_main_menu_keyboard())

@require_auth
async def execute_quitar_acerto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    month = query.data.replace("pay_settle_", "")
    chat_id = update.effective_chat.id
    client = get_client(chat_id)

    try:
        accounts = client.get_accounts()
        liquid_accounts = [a for a in accounts if a.get("type") in ("CHECKING", "SAVINGS")]

        if not liquid_accounts:
            await query.edit_message_text("❌ Nenhuma conta corrente/poupança disponível para realizar a quitação.")
            return

        source_acc_id = liquid_accounts[0]["id"]
        res = client.get_net_balance(month)
        net_amt = res.get("net_amount", 0.0)

        client.pay_settlement(month, source_acc_id, net_amt)

        await query.edit_message_text(
            f"✅ **Acerto do mês {month} quitado com sucesso!**\n\n"
            f"Todas as pendências do casal foram liquidadas e reconciliadas no banco de dados.",
            reply_markup=get_main_menu_keyboard(),
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"[QUITAR ACERTO ERRO] {e}")
        await query.edit_message_text(f"❌ Falha ao quitar acerto: {e}", reply_markup=get_main_menu_keyboard())
