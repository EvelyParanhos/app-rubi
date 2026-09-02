import logging
from telegram import Update
from telegram.ext import ContextTypes
from auth_manager import require_auth
from handlers.menu import get_main_menu_keyboard

logger = logging.getLogger(__name__)

@require_auth
async def handle_acerto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg_text = "ℹ️ **Acertos e Parcerias desativados.**\n\nO Rubi está operando em modo de gestão financeira 100% individual."
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(msg_text, reply_markup=get_main_menu_keyboard(), parse_mode="Markdown")
    else:
        await update.message.reply_text(msg_text, reply_markup=get_main_menu_keyboard(), parse_mode="Markdown")

@require_auth
async def execute_quitar_acerto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("ℹ️ A funcionalidade de acertos de contas foi removida.", reply_markup=get_main_menu_keyboard())
