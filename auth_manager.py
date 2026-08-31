import logging
from functools import wraps
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from rubi_api import RubiApiClient

logger = logging.getLogger(__name__)

# Cache de sessões em memória: { chat_id (int): { "token": str, "client": RubiApiClient } }
_SESSIONS: dict[int, dict] = {}

def get_client(chat_id: int) -> RubiApiClient | None:
    session = _SESSIONS.get(chat_id)
    if session and session.get("token"):
        client = RubiApiClient(token=session["token"])
        return client
    return None

def set_session(chat_id: int, token: str) -> RubiApiClient:
    client = RubiApiClient(token=token)
    _SESSIONS[chat_id] = {
        "token": token,
        "client": client
    }
    logger.info(f"[AUTH MANAGER] Sessão ativada para chat_id {chat_id}")
    return client

def clear_session(chat_id: int):
    if chat_id in _SESSIONS:
        del _SESSIONS[chat_id]
        logger.info(f"[AUTH MANAGER] Sessão removida para chat_id {chat_id}")

def is_authenticated(chat_id: int) -> bool:
    return chat_id in _SESSIONS and bool(_SESSIONS[chat_id].get("token"))

def require_auth(func):
    """
    Decorador interceptador que verifica se o usuário possui um token JWT ativo no cache.
    Caso contrário, interrompe a execução e orienta o usuário a efetuar o /login.
    """
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        chat_id = update.effective_chat.id if update.effective_chat else None
        
        if not chat_id or not is_authenticated(chat_id):
            msg_text = (
                "🔒 **Acesso Não Autenticado**\n\n"
                "Você precisa estar logado para acessar os recursos do **Rubi Financial**.\n"
                "Utilize o comando abaixo para realizar o login:"
            )
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔑 Fazer Login", callback_data="cmd_login")]
            ])

            if update.callback_query:
                await update.callback_query.answer("Sessão não encontrada. Faça o /login.", show_alert=True)
                try:
                    await update.callback_query.edit_message_text(msg_text, reply_markup=keyboard, parse_mode="Markdown")
                except Exception:
                    await context.bot.send_message(chat_id=chat_id, text=msg_text, reply_markup=keyboard, parse_mode="Markdown")
            elif update.message:
                await update.message.reply_text(msg_text, reply_markup=keyboard, parse_mode="Markdown")
                
            return ConversationHandler.END

        return await func(update, context, *args, **kwargs)
    return wrapper
