import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes
from auth_manager import require_auth, get_client
from handlers.auth import get_main_menu_keyboard
from handlers.transaction import CATEGORIES

logger = logging.getLogger(__name__)

@require_auth
async def handle_extrato(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    client = get_client(chat_id)
    month_str = datetime.now().strftime("%Y-%m")

    try:
        transactions = client.get_transactions(month=month_str)
        incomes = [t for t in transactions if t.get("type") == "CREDIT"]
        expenses = [t for t in transactions if t.get("type") == "DEBIT"]

        total_income = sum(t.get("amount", 0.0) for t in incomes)
        total_expense = sum(t.get("amount", 0.0) for t in expenses)
        balance = total_income - total_expense

        cat_summary = {}
        for t in expenses:
            cat = t.get("category", "UNCATEGORIZED")
            cat_label = CATEGORIES.get(cat, cat)
            cat_summary[cat_label] = cat_summary.get(cat_label, 0.0) + t.get("amount", 0.0)

        lines = [
            f"📊 **Extrato Financeiro - Mês {month_str}**\n",
            f"📥 **Total de Receitas**: R$ {total_income:.2f}",
            f"📤 **Total de Despesas**: R$ {total_expense:.2f}",
            f"⚖️ **Resultado do Mês**: R$ {balance:.2f}\n"
        ]

        if cat_summary:
            lines.append("🏷️ **Despesas Agrupadas por Categoria:**")
            for cat_name, val in sorted(cat_summary.items(), key=lambda x: x[1], reverse=True):
                pct = (val / total_expense * 100.0) if total_expense > 0 else 0.0
                lines.append(f"• **{cat_name}**: R$ {val:.2f} ({pct:.1f}%)")
            lines.append("")

        keyboard = []

        if transactions:
            lines.append("📝 **Últimas Transações Registradas:**")
            for t in transactions[:5]:
                t_id = t.get("id")
                desc = t.get("description", "Transação")
                amt = t.get("amount", 0.0)
                ttype = "🟢" if t.get("type") == "CREDIT" else "🔴"
                lines.append(f"{ttype} {desc} - R$ {amt:.2f}")
                
                if t_id:
                    keyboard.append([
                        InlineKeyboardButton(f"✏️ Editar ({desc[:10]})", callback_data=f"edit_tx_{t_id}"),
                        InlineKeyboardButton("🗑️ Excluir", callback_data=f"delete_tx_{t_id}")
                    ])

        keyboard.append([InlineKeyboardButton("🔙 Menu Principal", callback_data="cmd_main_menu")])
        msg_text = "\n".join(lines)

        if update.callback_query:
            try:
                await update.callback_query.answer()
            except Exception:
                pass
            await update.callback_query.edit_message_text(msg_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        else:
            await update.message.reply_text(msg_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    except Exception as e:
        logger.error(f"[EXTRATO ERRO] {e}")
        err_msg = f"❌ Erro ao gerar extrato do mês: {e}"
        if update.callback_query:
            try:
                await update.callback_query.answer()
            except Exception:
                pass
            await update.callback_query.edit_message_text(err_msg, reply_markup=get_main_menu_keyboard())
        else:
            await update.message.reply_text(err_msg, reply_markup=get_main_menu_keyboard())

async def handle_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except Exception:
        pass
    await query.edit_message_text(
        "💎 **Rubi Financial - Menu Principal**\n\nEscolha a operação desejada:",
        reply_markup=get_main_menu_keyboard(),
        parse_mode="Markdown"
    )
