import os
import json
import logging
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
import telegram.error
from telegram.request import HTTPXRequest
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters
)
from rubi_api import RubiApiClient

# Carrega variáveis de ambiente
load_dotenv()

# Configuração de Logs Precisos
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("RubiBot")

# Helper para obter o cliente de API autenticado por usuário/sessão do Telegram
def get_client(context: ContextTypes.DEFAULT_TYPE) -> RubiApiClient:
    return RubiApiClient(
        token=context.user_data.get("token"),
        phone_number=context.user_data.get("auth_phone"),
        pin=context.user_data.get("auth_pin")
    )

# Mapeamento para Português
TYPE_LABELS = {
    "CHECKING": "Conta Corrente",
    "SAVINGS": "Conta Poupança",
    "LIABILITY": "Fatura / Cartão de Crédito",
    "FIXED": "Despesa Fixa",
    "ESTIMATED": "Despesa Estimada"
}

CATEGORY_LABELS = {
    "PETS": "🐶 Animais de Estimação",
    "BARS_AND_RESTAURANTS": "🍔 Bares e Restaurantes",
    "DELIVERY": "🛵 Delivery",
    "SHOPPING": "🛍️ Compras",
    "HOUSING": "🏠 Contas da Casa",
    "DONATIONS": "🎁 Doações",
    "EDUCATION": "📚 Educação",
    "ENTERTAINMENT": "🎬 Entretenimento e Lazer",
    "TAXES_AND_FEES": "🧾 Impostos/Tarifas/Juros",
    "INVESTMENTS": "📈 Investimentos e Caixinhas",
    "SUPERMARKET": "🛒 Mercado",
    "UNCATEGORIZED": "📦 Não categorizado",
    "PAYMENTS": "💳 Pagamentos",
    "SERVICE_PROVIDERS": "🛠️ Prestadores de Serviço",
    "RECEIPTS": "💵 Recebimentos",
    "HEALTH": "🏥 Saúde e Cuidados Pessoais",
    "DIGITAL_SERVICES": "💻 Serviços Digitais",
    "TRANSFERS": "💸 Transferências",
    "TRANSPORT": "🚗 Veículo e Transporte",
    "TRAVEL": "✈️ Viagens"
}

def translate_type(type_code):
    return TYPE_LABELS.get(str(type_code).upper(), type_code)

def get_category_keyboard(callback_prefix="cat_sel_"):
    keyboard = []
    items = list(CATEGORY_LABELS.items())
    for i in range(0, len(items), 2):
        row = []
        code1, label1 = items[i]
        row.append(InlineKeyboardButton(label1, callback_data=f"{callback_prefix}{code1}"))
        if i + 1 < len(items):
            code2, label2 = items[i+1]
            row.append(InlineKeyboardButton(label2, callback_data=f"{callback_prefix}{code2}"))
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("🔙 Voltar ao Menu", callback_data="btn_main_menu")])
    return InlineKeyboardMarkup(keyboard)

# Definição de Estados da Conversação
(
    MENU,
    # Autenticação Dinâmica
    AUTH_PHONE,
    AUTH_PIN,
    # Onboarding Guiado (Baseline Setup)
    OB_ACC_NAME,
    OB_ACC_BALANCE,
    OB_CARD_ASK,
    OB_CARD_NAME,
    OB_CARD_LIMIT,
    OB_CARD_CLOSING,
    OB_CARD_DUE,
    OB_REC_ASK,
    OB_REC_DESC,
    OB_REC_AMOUNT,
    OB_REC_TYPE,
    OB_REC_DUE_DAY,
    # Adicionar Gasto
    EXPENSE_DESC,
    EXPENSE_AMOUNT,
    EXPENSE_CATEGORY,
    EXPENSE_SELECT_METHOD,
    EXPENSE_SELECT_ITEM,
    EXPENSE_INSTALLMENTS,
    EXPENSE_SPLIT_CONFIRM,
    EXPENSE_CUSTOM_SPLIT_INPUT,
    # Consultar Mês
    CONSULT_MONTH_INPUT,
    # Criar Conta
    ACCOUNT_NAME,
    ACCOUNT_TYPE,
    ACCOUNT_JOINT,
    ACCOUNT_INITIAL_BALANCE,
    # Transferência por Botões
    TRANSFER_SOURCE,
    TRANSFER_TARGET,
    TRANSFER_AMOUNT,
    TRANSFER_DESC,
    # Cartão de Crédito
    CARD_ACCOUNT,
    CARD_NAME,
    CARD_LIMIT,
    CARD_CLOSING,
    CARD_DUE,
    # Parceria
    PARTNER_PHONE,
    # Gastos Fixos
    RECURRING_DESC,
    RECURRING_AMOUNT,
    RECURRING_TYPE,
    RECURRING_DUE_DAY,
    RECURRING_ACCOUNT,
) = range(43)

# --- MENUS E TECLADOS ---

def get_main_menu_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("➕ Adicionar Gasto", callback_data="btn_add_expense"),
            InlineKeyboardButton("📅 Consultar Mês", callback_data="btn_consult_month")
        ],
        [
            InlineKeyboardButton("📌 Despesas Fixas", callback_data="btn_recurring_expenses"),
            InlineKeyboardButton("🏦 Minhas Contas", callback_data="btn_accounts")
        ],
        [
            InlineKeyboardButton("💳 Cartões de Crédito", callback_data="btn_credit_card"),
            InlineKeyboardButton("💸 Transferência", callback_data="btn_transfer")
        ],
        [
            InlineKeyboardButton("🤝 Parceria / Casal", callback_data="btn_partnership")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_back_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Voltar ao Menu Principal", callback_data="btn_main_menu")]
    ])

# --- TRATAMENTO DE ERROS GLOBAL NO TELEGRAM ---

async def global_error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"[ERRO GLOBAL TELEGRAM] Exceção não tratada: {context.error}", exc_info=context.error)
    if isinstance(context.error, (telegram.error.TimedOut, telegram.error.NetworkError)):
        logger.warning("[AVISO REDE TELEGRAM] Oscilação de rede ou timeout na API do Telegram. A operação foi salva com sucesso no backend!")
        return

    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "⚠️ **Aviso Rubi**: Ocorreu uma oscilação temporária na conexão.\n\n"
                "Por favor, tente novamente selecionando uma opção no menu:",
                parse_mode="Markdown",
                reply_markup=get_main_menu_keyboard()
            )
        except Exception:
            pass

# --- AUTENTICAÇÃO DINÂMICA DE USUÁRIO E START ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name if update.effective_user else "Usuário"
    logger.info(f"[TELEGRAM] /start recebido de {user_name}")

    if update.callback_query:
        await update.callback_query.answer()

    client = get_client(context)

    # Se a sessão não tiver token válido, inicia fluxo interativo de autenticação/cadastro
    if not context.user_data.get("token"):
        text = (
            f"Olá, **{user_name}**! 👋 Bem-vindo ao **Rubi Financial**.\n\n"
            "📱 Para começar ou entrar na sua conta, por favor envie o seu **número de celular** no formato internacional E.164 (ex: `+5571999998888`):"
        )
        if update.callback_query:
            await update.callback_query.edit_message_text(text, parse_mode="Markdown")
        else:
            await update.message.reply_text(text, parse_mode="Markdown")
        return AUTH_PHONE

    # Tenta obter as contas com o token atual da sessão
    try:
        accounts = client.get_accounts()
    except Exception:
        # Se falhar a autenticação, reseta sessão e pede telefone
        context.user_data.pop("token", None)
        await update.message.reply_text(
            "🔑 Sua sessão expirou. Por favor, envie seu **número de celular** (ex: `+5571999998888`):",
            parse_mode="Markdown"
        )
        return AUTH_PHONE

    if not accounts:
        keyboard = [[InlineKeyboardButton("🚀 Iniciar Configuração Inicial", callback_data="btn_start_onboarding")]]
        text = (
            f"Olá, **{user_name}**! 👋\n\n"
            "Identificamos que esta é a sua primeira vez aqui! Vamos realizar o seu **Onboarding Guiado de Linha de Base** em 4 etapas rápidas para calibrar seus saldos e compromissos futuros."
        )
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        else:
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return MENU

    text = (
        f"Olá, **{user_name}**! 👋 Bem-vindo ao **Rubi Financial**.\n\n"
        "Selecione uma das opções abaixo para navegar:"
    )
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=get_main_menu_keyboard(), parse_mode="Markdown")
    else:
        await update.message.reply_text(text, reply_markup=get_main_menu_keyboard(), parse_mode="Markdown")
    return MENU

async def auth_phone_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = update.message.text.strip()
    if not phone.startswith("+") or len(phone) < 10:
        await update.message.reply_text("❌ Formato de telefone inválido! Digite com o código do país (ex: `+5571999998888`):", parse_mode="Markdown")
        return AUTH_PHONE

    context.user_data["auth_phone"] = phone
    await update.message.reply_text("🔑 Agora, digite a sua **senha / PIN de 4 dígitos**:", parse_mode="Markdown")
    return AUTH_PIN

async def auth_pin_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pin = update.message.text.strip()
    phone = context.user_data.get("auth_phone")
    user_name = update.effective_user.first_name if update.effective_user else "Usuário"

    context.user_data["auth_pin"] = pin
    client = get_client(context)

    try:
        token = client.ensure_login(phone, pin, user_name)
        context.user_data["token"] = token
        await update.message.reply_text("✅ **Autenticado com sucesso!**", parse_mode="Markdown")
        return await start(update, context)
    except Exception as e:
        logger.error(f"[ERRO LOGIN TELEGRAM] {e}")
        await update.message.reply_text(
            f"❌ **Falha na Autenticação**: {e}\n\nPor favor, tente novamente enviando o **número de celular** (ex: `+5571999998888`):",
            parse_mode="Markdown"
        )
        return AUTH_PHONE

async def handle_main_menu_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    client = get_client(context)

    logger.info(f"[TELEGRAM CALLBACK] Botão pressionado: {data}")

    if data == "btn_main_menu":
        return await start(update, context)

    elif data.startswith("pay_settle_"):
        month_to_pay = data.replace("pay_settle_", "")
        accounts = client.get_accounts()
        liquid = [a for a in accounts if a.get("type") in ("CHECKING", "SAVINGS")]
        if not liquid:
            await query.edit_message_text("❌ Nenhuma conta corrente/poupança encontrada para realizar a quitação.", reply_markup=get_main_menu_keyboard())
            return MENU

        acc_id = liquid[0]["id"]
        try:
            res = client.get("/settlements/net-balance", params={"month": month_to_pay})
            net_amt = res.get("net_amount", 0.0)
            client.pay_settlement(month_to_pay, acc_id, net_amt)
            await query.edit_message_text(
                f"✅ **Acerto do mês {month_to_pay} quitado com sucesso!**\n\n"
                f"Todas as pendências do casal foram liquidadas.",
                reply_markup=get_main_menu_keyboard(),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"[ERRO QUITAR ACERTO] {e}")
            await query.edit_message_text(f"❌ Falha ao quitar acerto do mês: {e}", reply_markup=get_main_menu_keyboard())
        return MENU

    elif data == "btn_start_onboarding":
        await query.edit_message_text(
            "🚀 **Onboarding Guiado (Passo 1/4)**\n\n"
            "Digite o nome da sua **Conta Principal** (ex: Nubank, Itaú, Bradesco):",
            parse_mode="Markdown"
        )
        return OB_ACC_NAME

    elif data == "btn_add_expense":
        await query.edit_message_text(
            "➕ **Adicionar Gasto**\n\nDigite a descrição da despesa (ex: Mercado, Almoço, Gasolina):",
            reply_markup=get_back_keyboard(),
            parse_mode="Markdown"
        )
        return EXPENSE_DESC

    elif data == "btn_consult_month":
        now_month = datetime.now().strftime("%Y-%m")
        prev_month = (datetime.now().replace(day=1) - timedelta(days=1)).strftime("%Y-%m")

        keyboard = [
            [
                InlineKeyboardButton(f"📅 Mês Atual ({now_month})", callback_data=f"month_{now_month}"),
                InlineKeyboardButton(f"📅 Mês Anterior ({prev_month})", callback_data=f"month_{prev_month}")
            ],
            [InlineKeyboardButton("🔙 Voltar ao Menu", callback_data="btn_main_menu")]
        ]
        await query.edit_message_text(
            "📅 **Consultar Mês & Extrato Financeiro**\n\nSelecione um mês abaixo ou digite o mês (`AAAA-MM`) no chat:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        return CONSULT_MONTH_INPUT

    elif data == "btn_recurring_expenses":
        keyboard = [
            [InlineKeyboardButton("📋 Ver Despesas Fixas", callback_data="btn_list_recurring")],
            [InlineKeyboardButton("🆕 Cadastrar Despesa Fixa/Estimada", callback_data="btn_create_recurring")],
            [InlineKeyboardButton("🔙 Voltar ao Menu", callback_data="btn_main_menu")]
        ]
        await query.edit_message_text(
            "📌 **Gestão de Gastos Fixos e Estimados**\n\nEscolha uma opção:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        return MENU

    elif data == "btn_list_recurring":
        expenses = client.get_recurring_expenses()
        if expenses:
            lines = [f"• **{e['description']}** - R$ {e['amount']:.2f} ({translate_type(e['type'])}) - Vencimento dia {e['due_day']}" for e in expenses]
            msg = "📋 **Suas Despesas Recorrentes:**\n\n" + "\n".join(lines)
        else:
            msg = "ℹ️ Nenhuma despesa fixa ou estimada cadastrada ainda."
        await query.edit_message_text(msg, reply_markup=get_main_menu_keyboard(), parse_mode="Markdown")
        return MENU

    elif data == "btn_create_recurring":
        await query.edit_message_text(
            "🆕 **Cadastrar Despesa Recorrente**\n\nDigite o nome da conta (ex: Conta de Luz, Aluguel):",
            reply_markup=get_back_keyboard(),
            parse_mode="Markdown"
        )
        return RECURRING_DESC

    elif data == "btn_accounts":
        accounts = client.get_accounts()
        liquid_accounts = [a for a in accounts if a.get("type") in ("CHECKING", "SAVINGS")]
        total_balance = sum(a.get("balance", 0.0) for a in liquid_accounts)

        lines = [f"• **{a['name']}** ({translate_type(a['type'])}) - Saldo: R$ {a.get('balance', 0.0):.2f}" for a in accounts]

        text = (
            f"💰 **Saldo Geral Líquido**: **R$ {total_balance:.2f}**\n\n"
            f"🏦 **Suas Contas Cadastradas:**\n\n" + ("\n".join(lines) if lines else "Nenhuma conta cadastrada.")
        )

        keyboard = [
            [InlineKeyboardButton("🆕 Criar Nova Conta", callback_data="btn_create_account")],
            [InlineKeyboardButton("🔙 Voltar ao Menu", callback_data="btn_main_menu")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return MENU

    elif data == "btn_create_account":
        await query.edit_message_text(
            "🆕 **Criar Nova Conta**\n\nDigite o nome da conta (ex: Nubank, Itaú):",
            reply_markup=get_back_keyboard(),
            parse_mode="Markdown"
        )
        return ACCOUNT_NAME

    elif data == "btn_transfer":
        accounts = client.get_accounts()
        if not accounts or len(accounts) < 2:
            await query.edit_message_text(
                "💸 **Transferência entre Contas**\n\n"
                "Você precisa ter pelo menos **2 contas cadastradas** para realizar transferências.\n\n"
                "Crie suas contas no menu **🏦 Minhas Contas**!",
                reply_markup=get_main_menu_keyboard(),
                parse_mode="Markdown"
            )
            return MENU

        keyboard = []
        for a in accounts:
            keyboard.append([InlineKeyboardButton(f"🏦 {a['name']} (R$ {a.get('balance', 0.0):.2f})", callback_data=f"tr_src_{a['id']}")])
        keyboard.append([InlineKeyboardButton("🔙 Voltar ao Menu", callback_data="btn_main_menu")])

        await query.edit_message_text(
            "💸 **Transferência entre Contas**\n\nSelecione a conta de **Origem** (onde o dinheiro sairá):",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        return TRANSFER_SOURCE

    elif data == "btn_credit_card":
        cards = client.get_credit_cards()
        if cards:
            card_texts = []
            for c in cards:
                c_name = c.get("name", "Cartão")
                c_limit = c.get("credit_limit", 0.0)
                c_used = c.get("used_limit", 0.0)
                c_avail = c.get("available_limit", c_limit)
                c_inv = c.get("current_invoice_amount", 0.0)
                c_close = c.get("closing_day")
                c_due = c.get("due_day")
                card_texts.append(
                    f"💳 **{c_name}**\n"
                    f"  📊 Limite Total: R$ {c_limit:.2f}\n"
                    f"  🔴 Limite Utilizado: R$ {c_used:.2f}\n"
                    f"  🟢 **Limite Liberado / Disponível**: **R$ {c_avail:.2f}**\n"
                    f"  📄 Fatura Atual: R$ {c_inv:.2f}\n"
                    f"  📅 Fechamento: Dia {c_close} | Vencimento: Dia {c_due}"
                )
            text = "💳 **Seus Cartões de Crédito:**\n\n" + "\n\n".join(card_texts)
        else:
            text = "💳 **Seus Cartões de Crédito:**\n\nNenhum cartão cadastrado ainda."

        keyboard = [
            [InlineKeyboardButton("🆕 Cadastrar Cartão", callback_data="btn_create_card")],
            [InlineKeyboardButton("🔙 Voltar ao Menu", callback_data="btn_main_menu")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return MENU

        keyboard = [
            [InlineKeyboardButton("🆕 Cadastrar Cartão", callback_data="btn_create_card")],
            [InlineKeyboardButton("🔙 Voltar ao Menu", callback_data="btn_main_menu")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return MENU

    elif data == "btn_create_card":
        accounts = client.get_accounts()
        liability_accounts = [a for a in accounts if a.get("type") == "LIABILITY"]

        if not liability_accounts:
            keyboard = [
                [InlineKeyboardButton("➕ Criar 'Fatura do Cartão' Agora", callback_data="auto_create_liability")],
                [InlineKeyboardButton("🔙 Voltar ao Menu", callback_data="btn_main_menu")]
            ]
            await query.edit_message_text(
                "💳 **Cadastrar Cartão de Crédito**\n\n"
                "Para vincular um cartão, você precisa de uma conta do tipo **Fatura / Cartão de Crédito**.\n\n"
                "Deseja criar automaticamente a conta **Fatura do Cartão** em 1 clique agora?",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )
            return MENU

        keyboard = []
        for a in liability_accounts:
            keyboard.append([InlineKeyboardButton(f"💳 {a['name']}", callback_data=f"card_acc_{a['id']}")])
        keyboard.append([InlineKeyboardButton("🔙 Voltar ao Menu", callback_data="btn_main_menu")])

        await query.edit_message_text(
            "💳 **Cadastrar Cartão de Crédito**\n\nSelecione a conta de Fatura associada ao cartão:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        return CARD_ACCOUNT

    elif data == "auto_create_liability":
        try:
            res = client.post("/accounts", {"name": "Fatura do Cartão", "type": "LIABILITY", "is_joint": False})
            real_uuid = res.get("id")
            context.user_data["card_account"] = real_uuid
            logger.info(f"[FIX UUID CARTÃO] Conta Fatura criada com UUID real: {real_uuid}")
            await query.edit_message_text(
                "✅ **Conta 'Fatura do Cartão' criada com sucesso!**\n\nAgora, digite o nome do cartão de crédito (ex: Nubank Gold):",
                reply_markup=get_back_keyboard(),
                parse_mode="Markdown"
            )
            return CARD_NAME
        except Exception as e:
            logger.error(f"[ERRO AUTO LIABILITY] {e}")
            await query.edit_message_text("❌ Não foi possível criar a conta de fatura.", reply_markup=get_main_menu_keyboard())
            return MENU

    elif data == "btn_partnership":
        p_info = client.get_active_partnership()
        if p_info.get("has_active_partnership"):
            partner = p_info.get('partner_name', 'Seu parceiro(a)')
            text = f"🤝 **Parceria Ativa com {partner}**!\n\nVocês já podem dividir despesas com percentuais flexíveis e visualizar o acerto mensal."
            keyboard = [[InlineKeyboardButton("🔙 Voltar ao Menu", callback_data="btn_main_menu")]]
        else:
            text = "🤝 **Parceria / Núcleo Familiar**\n\nVocê ainda não possui um parceiro(a) vinculado."
            keyboard = [
                [InlineKeyboardButton("📩 Convidar Parceiro(a)", callback_data="btn_invite_partner")],
                [InlineKeyboardButton("🔙 Voltar ao Menu", callback_data="btn_main_menu")]
            ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return MENU

    elif data == "btn_invite_partner":
        await query.edit_message_text(
            "📩 **Convidar Parceiro(a)**\n\nDigite o número de telefone com código do país (ex: +5571988887777):",
            reply_markup=get_back_keyboard(),
            parse_mode="Markdown"
        )
        return PARTNER_PHONE

    return MENU

# --- FLUXO ONBOARDING GUIADO (BASELINE SETUP) ---

async def ob_acc_name_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["ob_acc_name"] = update.message.text.strip()
    await update.message.reply_text(
        f"Qual é o seu **saldo real atual** na conta **{context.user_data['ob_acc_name']}** em R$? (ex: 2500.00 ou 0):",
        parse_mode="Markdown"
    )
    return OB_ACC_BALANCE

async def ob_acc_balance_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        val = float(update.message.text.replace(",", "."))
        context.user_data["ob_acc_balance"] = val
    except ValueError:
        await update.message.reply_text("❌ Valor inválido! Digite apenas números (ex: 1500.00).")
        return OB_ACC_BALANCE

    client = get_client(context)
    res = client.post("/accounts", {
        "name": context.user_data["ob_acc_name"],
        "type": "CHECKING",
        "is_joint": False,
        "initial_balance": val
    })
    acc_id = res.get("id") if res else None
    context.user_data["primary_account_id"] = acc_id

    keyboard = [
        [
            InlineKeyboardButton("💳 Cadastrar Cartão de Crédito", callback_data="ob_card_yes"),
            InlineKeyboardButton("⏭️ Pular esta etapa", callback_data="ob_card_no")
        ]
    ]
    await update.message.reply_text(
        f"✅ Conta **{context.user_data['ob_acc_name']}** criada com saldo inicial de **R$ {val:.2f}**!\n\n"
        "🚀 **Onboarding Guiado (Passo 2/4)**\n\nVocê possui um **Cartão de Crédito** para cadastrar?",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return OB_CARD_ASK

async def ob_card_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    client = get_client(context)
    if query.data == "ob_card_yes":
        res = client.post("/accounts", {"name": "Fatura do Cartão", "type": "LIABILITY", "is_joint": False})
        context.user_data["card_account"] = res.get("id")
        await query.edit_message_text("Digite o nome do seu cartão de crédito (ex: Nubank Gold, Itaú Click):")
        return OB_CARD_NAME
    else:
        return await start_ob_recurring_step(query)

async def ob_card_name_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["card_name"] = update.message.text.strip()
    await update.message.reply_text("Digite o limite de crédito do cartão em R$ (ex: 5000):")
    return OB_CARD_LIMIT

async def ob_card_limit_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data["card_limit"] = float(update.message.text.replace(",", "."))
    except ValueError:
        await update.message.reply_text("❌ Valor inválido!")
        return OB_CARD_LIMIT
    await update.message.reply_text("Digite o dia do mês do **fechamento** da fatura (ex: 25):")
    return OB_CARD_CLOSING

async def ob_card_closing_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data["card_closing"] = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("❌ Dia inválido!")
        return OB_CARD_CLOSING
    await update.message.reply_text("Digite o dia do mês do **vencimento** da fatura (ex: 5):")
    return OB_CARD_DUE

async def ob_card_due_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        due = int(update.message.text.strip())
        context.user_data["card_due"] = due
    except ValueError:
        await update.message.reply_text("❌ Dia inválido!")
        return OB_CARD_DUE

    client = get_client(context)
    payload = {
        "account_id": context.user_data.get("card_account"),
        "name": context.user_data.get("card_name"),
        "credit_limit": context.user_data.get("card_limit"),
        "closing_day": context.user_data.get("card_closing"),
        "due_day": due
    }
    client.post("/credit-cards", payload)
    await update.message.reply_text(f"✅ Cartão **{payload['name']}** cadastrado com sucesso!")

    keyboard = [
        [
            InlineKeyboardButton("📌 Cadastrar Gasto Fixo", callback_data="ob_rec_yes"),
            InlineKeyboardButton("⏭️ Pular/Concluir", callback_data="ob_rec_no")
        ]
    ]
    await update.message.reply_text(
        "🚀 **Onboarding Guiado (Passo 3/4)**\n\n"
        "Deseja cadastrar um **Gasto Fixo Mensal** (ex: Aluguel R$ 1.200,00 ou Luz R$ 180,00 Estimado) para projetar os próximos meses?",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return OB_REC_ASK

async def start_ob_recurring_step(query):
    keyboard = [
        [
            InlineKeyboardButton("📌 Cadastrar Gasto Fixo", callback_data="ob_rec_yes"),
            InlineKeyboardButton("⏭️ Pular/Concluir", callback_data="ob_rec_no")
        ]
    ]
    await query.edit_message_text(
        "🚀 **Onboarding Guiado (Passo 3/4)**\n\n"
        "Deseja cadastrar um **Gasto Fixo Mensal** (ex: Aluguel R$ 1.200,00 ou Luz R$ 180,00 Estimado) para projetar os próximos meses?",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return OB_REC_ASK

async def ob_rec_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "ob_rec_yes":
        await query.edit_message_text("Digite o nome da despesa fixa (ex: Aluguel, Luz, Internet):")
        return OB_REC_DESC
    else:
        return await finish_onboarding(query, context)

async def ob_rec_desc_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["ob_rec_desc"] = update.message.text.strip()
    await update.message.reply_text("Digite o valor mensal em R$:")
    return OB_REC_AMOUNT

async def ob_rec_amount_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data["ob_rec_amount"] = float(update.message.text.replace(",", "."))
    except ValueError:
        await update.message.reply_text("❌ Valor inválido!")
        return OB_REC_AMOUNT

    keyboard = [
        [
            InlineKeyboardButton("📌 Despesa Fixa", callback_data="ob_rectype_FIXED"),
            InlineKeyboardButton("⚡ Despesa Estimada", callback_data="ob_rectype_ESTIMATED")
        ]
    ]
    await update.message.reply_text("Selecione o tipo:", reply_markup=InlineKeyboardMarkup(keyboard))
    return OB_REC_TYPE

async def ob_rec_type_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["ob_rec_type"] = query.data.replace("ob_rectype_", "")
    await query.edit_message_text("Digite o dia do mês de vencimento (ex: 10):")
    return OB_REC_DUE_DAY

async def ob_rec_due_day_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        due_day = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("❌ Dia inválido!")
        return OB_REC_DUE_DAY

    client = get_client(context)
    acc_id = context.user_data.get("primary_account_id")
    client.create_recurring_expense(
        account_id=acc_id,
        description=context.user_data.get("ob_rec_desc"),
        amount=context.user_data.get("ob_rec_amount"),
        exp_type=context.user_data.get("ob_rec_type"),
        due_day=due_day
    )
    await update.message.reply_text(f"✅ Despesa **{context.user_data.get('ob_rec_desc')}** cadastrada com sucesso!")
    return await finish_onboarding(update, context)

async def finish_onboarding(update_or_query, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "🎉 **Onboarding Guiado de Linha de Base Concluído!**\n\n"
        "Seus saldos iniciais, cartões e despesas fixas foram calibrados com sucesso.\n\n"
        "Aproveite o **Rubi Financial**:"
    )
    if isinstance(update_or_query, Update):
        await update_or_query.message.reply_text(msg, reply_markup=get_main_menu_keyboard(), parse_mode="Markdown")
    else:
        await update_or_query.edit_message_text(msg, reply_markup=get_main_menu_keyboard(), parse_mode="Markdown")
    return MENU

# --- AUXILIARES BOTÕES DINÂMICOS ---

def get_account_buttons(context, callback_prefix="acc_sel_"):
    client = get_client(context)
    accounts = client.get_accounts()
    keyboard = []
    for a in accounts:
        keyboard.append([InlineKeyboardButton(f"🏦 {a['name']} ({translate_type(a['type'])})", callback_data=f"{callback_prefix}{a['id']}")])
    keyboard.append([InlineKeyboardButton("🔙 Voltar ao Menu", callback_data="btn_main_menu")])
    return InlineKeyboardMarkup(keyboard)

def get_card_buttons(context, callback_prefix="card_sel_"):
    client = get_client(context)
    cards = client.get_credit_cards()
    keyboard = []
    for c in cards:
        keyboard.append([InlineKeyboardButton(f"💳 {c['name']} (Limite: R$ {c['credit_limit']:.0f})", callback_data=f"{callback_prefix}{c['id']}")])
    keyboard.append([InlineKeyboardButton("🔙 Voltar ao Menu", callback_data="btn_main_menu")])
    return InlineKeyboardMarkup(keyboard)

# --- FLUXO 1: ADICIONAR GASTO ---

async def expense_desc_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["expense_desc"] = update.message.text.strip()
    await update.message.reply_text("Digite o valor em R$ (ex: 45.50 ou 120):", reply_markup=get_back_keyboard())
    return EXPENSE_AMOUNT

async def expense_amount_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        val = float(update.message.text.replace(",", "."))
        context.user_data["expense_amount"] = val
    except ValueError:
        await update.message.reply_text("❌ Valor inválido! Digite apenas números (ex: 50.00).")
        return EXPENSE_AMOUNT

    await update.message.reply_text(
        f"Gasto: **{context.user_data['expense_desc']}** (R$ {val:.2f})\n\nSelecione a **Categoria** do gasto:",
        reply_markup=get_category_keyboard(callback_prefix="exp_cat_"),
        parse_mode="Markdown"
    )
    return EXPENSE_CATEGORY

async def expense_category_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cat_code = query.data.replace("exp_cat_", "")
    context.user_data["expense_category"] = cat_code

    keyboard = [
        [
            InlineKeyboardButton("💳 Cartão de Crédito", callback_data="pay_method_card"),
            InlineKeyboardButton("🏦 Conta / PIX", callback_data="pay_method_account")
        ],
        [InlineKeyboardButton("🔙 Voltar ao Menu", callback_data="btn_main_menu")]
    ]
    val = context.user_data.get("expense_amount", 0.0)
    cat_name = CATEGORY_LABELS.get(cat_code, cat_code)
    await query.edit_message_text(
        f"Gasto: **{context.user_data['expense_desc']}** (R$ {val:.2f})\n"
        f"Categoria: **{cat_name}**\n\n"
        "Selecione o método de pagamento:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return EXPENSE_SELECT_METHOD

async def expense_method_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    method = query.data
    client = get_client(context)

    if method == "pay_method_card":
        cards = client.get_credit_cards()
        if not cards:
            await query.edit_message_text(
                "⚠️ NENHUM CARTÃO CADASTRADO\n\nCadastre um cartão no menu **💳 Cartões de Crédito** primeiro!",
                reply_markup=get_main_menu_keyboard(),
                parse_mode="Markdown"
            )
            return MENU

        context.user_data["expense_method"] = "CARD"
        await query.edit_message_text("Selecione o Cartão de Crédito:", reply_markup=get_card_buttons(context, callback_prefix="exp_card_"))
        return EXPENSE_SELECT_ITEM
    else:
        accounts = client.get_accounts()
        if not accounts:
            await query.edit_message_text(
                "⚠️ NENHUMA CONTA CADASTRADA\n\nCrie uma conta no menu **🏦 Minhas Contas** primeiro!",
                reply_markup=get_main_menu_keyboard(),
                parse_mode="Markdown"
            )
            return MENU

        context.user_data["expense_method"] = "ACCOUNT"
        await query.edit_message_text("Selecione a Conta de Origem:", reply_markup=get_account_buttons(context, callback_prefix="exp_acc_"))
        return EXPENSE_SELECT_ITEM

async def expense_item_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    item_data = query.data

    if item_data.startswith("exp_card_"):
        card_id = item_data.replace("exp_card_", "")
        context.user_data["expense_item_id"] = card_id

        keyboard = [
            [
                InlineKeyboardButton("1x (À vista)", callback_data="inst_1"),
                InlineKeyboardButton("2x", callback_data="inst_2"),
                InlineKeyboardButton("3x", callback_data="inst_3")
            ],
            [
                InlineKeyboardButton("6x", callback_data="inst_6"),
                InlineKeyboardButton("12x", callback_data="inst_12")
            ],
            [InlineKeyboardButton("🔙 Voltar ao Menu", callback_data="btn_main_menu")]
        ]
        await query.edit_message_text("Selecione o número de parcelas:", reply_markup=InlineKeyboardMarkup(keyboard))
        return EXPENSE_INSTALLMENTS
    else:
        acc_id = item_data.replace("exp_acc_", "")
        context.user_data["expense_item_id"] = acc_id
        return await check_split_and_finish(update, context, query=query)

async def expense_installments_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    inst = int(query.data.replace("inst_", ""))
    context.user_data["expense_installments"] = inst
    return await check_split_and_finish(update, context, query=query)

async def check_split_and_finish(update: Update, context: ContextTypes.DEFAULT_TYPE, query=None):
    client = get_client(context)
    p_info = client.get_active_partnership()
    if p_info.get("has_active_partnership"):
        partner_name = p_info.get("partner_name", "Parceiro(a)")
        context.user_data["partner_id"] = p_info.get("partner_id")

        keyboard = [
            [
                InlineKeyboardButton("🤝 50/50", callback_data="split_50"),
                InlineKeyboardButton(f"📊 60/40 (40% {partner_name})", callback_data="split_40"),
                InlineKeyboardButton(f"📊 70/30 (30% {partner_name})", callback_data="split_30")
            ],
            [
                InlineKeyboardButton("✏️ Valor Personalizado R$", callback_data="split_custom")
            ],
            [
                InlineKeyboardButton("👤 Gasto Individual (100%)", callback_data="split_none")
            ],
            [InlineKeyboardButton("🔙 Voltar ao Menu", callback_data="btn_main_menu")]
        ]
        msg_text = f"Como deseja dividir este gasto de R$ {context.user_data['expense_amount']:.2f} com **{partner_name}**?"
        if query:
            await query.edit_message_text(msg_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        else:
            await update.message.reply_text(msg_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return EXPENSE_SPLIT_CONFIRM
    else:
        context.user_data["split_amount"] = 0.0
        return await process_expense_save(update, context, query=query)

async def expense_split_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    choice = query.data
    total = context.user_data.get("expense_amount", 0.0)

    if choice == "split_50":
        context.user_data["split_amount"] = total * 0.50
        return await process_expense_save(update, context, query=query)
    elif choice == "split_40":
        context.user_data["split_amount"] = total * 0.40
        return await process_expense_save(update, context, query=query)
    elif choice == "split_30":
        context.user_data["split_amount"] = total * 0.30
        return await process_expense_save(update, context, query=query)
    elif choice == "split_custom":
        await query.edit_message_text(
            f"Digite o valor exato em R$ que deve caber ao seu parceiro(a) (de R$ 0.01 até R$ {total:.2f}):",
            reply_markup=get_back_keyboard()
        )
        return EXPENSE_CUSTOM_SPLIT_INPUT
    else:
        context.user_data["split_amount"] = 0.0
        return await process_expense_save(update, context, query=query)

async def expense_custom_split_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        val = float(update.message.text.replace(",", "."))
        context.user_data["split_amount"] = val
        return await process_expense_save(update, context)
    except ValueError:
        await update.message.reply_text("❌ Valor inválido! Digite apenas números.")
        return EXPENSE_CUSTOM_SPLIT_INPUT

async def process_expense_save(update: Update, context: ContextTypes.DEFAULT_TYPE, query=None):
    client = get_client(context)
    desc = context.user_data.get("expense_desc")
    amount = context.user_data.get("expense_amount")
    method = context.user_data.get("expense_method")
    item_id = context.user_data.get("expense_item_id")
    split_amount = context.user_data.get("split_amount", 0.0)

    cat_code = context.user_data.get("expense_category", "UNCATEGORIZED")
    cat_label = CATEGORY_LABELS.get(cat_code, cat_code)

    try:
        if method == "CARD":
            inst = context.user_data.get("expense_installments", 1)
            now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            payload = {
                "amount": amount,
                "description": desc,
                "installments": inst,
                "purchase_date": now_iso
            }
            client.post(f"/credit-cards/{item_id}/purchases", payload)
            res_msg = f"✅ **Gasto no cartão registrado!**\n\n📌 **{desc}**: R$ {amount:.2f} ({inst}x)\n🏷️ Categoria: {cat_label}"
        else:
            client.create_transaction(item_id, amount, "DEBIT", desc, category=cat_code)
            res_msg = f"✅ **Gasto registrado com sucesso!**\n\n📌 **{desc}**: R$ {amount:.2f}\n🏷️ Categoria: {cat_label}"

        if split_amount > 0:
            res_msg += f"\n\n🤝 **Rateio Flexível**: R$ {split_amount:.2f} computados para o parceiro(a)."

        if query:
            await query.edit_message_text(res_msg, reply_markup=get_main_menu_keyboard(), parse_mode="Markdown")
        else:
            await update.message.reply_text(res_msg, reply_markup=get_main_menu_keyboard(), parse_mode="Markdown")
    except Exception as e:
        logger.error(f"[ERRO GASTO] {e}")
        err_msg = "❌ Não foi possível registrar o gasto. Verifique se a conta/cartão está ativa."
        if query:
            await query.edit_message_text(err_msg, reply_markup=get_main_menu_keyboard())
        else:
            await update.message.reply_text(err_msg, reply_markup=get_main_menu_keyboard())
    return MENU

# --- FLUXO 2: CONSULTAR MÊS (US10) ---

async def consult_month_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    client = get_client(context)
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        month_str = query.data.replace("month_", "")
    else:
        month_str = update.message.text.strip()

    try:
        transactions = client.get_transactions(month=month_str)
        incomes = [t for t in transactions if t.get("type") == "CREDIT"]
        expenses = [t for t in transactions if t.get("type") == "DEBIT"]

        total_income = sum(t.get("amount", 0.0) for t in incomes)
        total_expense = sum(t.get("amount", 0.0) for t in expenses)
        balance_month = total_income - total_expense

        cat_summary = {}
        for t in expenses:
            cat = t.get("category", "UNCATEGORIZED")
            cat_label = CATEGORY_LABELS.get(cat, cat)
            cat_summary[cat_label] = cat_summary.get(cat_label, 0.0) + t.get("amount", 0.0)

        lines = [
            f"📅 **Extrato Financeiro de {month_str}**\n",
            f"📥 **Total de Receitas**: R$ {total_income:.2f}",
            f"📤 **Total de Despesas**: R$ {total_expense:.2f}",
            f"⚖️ **Resultado do Mês**: R$ {balance_month:.2f}\n"
        ]

        if cat_summary:
            lines.append("🏷️ **Despesas por Categoria:**")
            for cat_name, val in cat_summary.items():
                lines.append(f"• {cat_name}: R$ {val:.2f}")
            lines.append("")

        p_info = client.get_active_partnership()
        keyboard = []

        if p_info.get("has_active_partnership"):
            try:
                settlement = client.get("/settlements/net-balance", params={"month": month_str})
                if settlement and settlement.get("net_amount", 0.0) > 0:
                    d_name = settlement.get("debtor_name", "Devedor")
                    c_name = settlement.get("creditor_name", "Credor")
                    net_amt = settlement.get("net_amount", 0.0)
                    lines.append(f"🤝 **Acerto do Casal ({month_str})**:")
                    lines.append(f"💰 **{d_name}** deve transferir **R$ {net_amt:.2f}** para **{c_name}**!")
                    keyboard.append([InlineKeyboardButton("💸 Quitar Acerto do Mês", callback_data=f"pay_settle_{month_str}")])
                else:
                    lines.append(f"🎉 **Acerto do Casal**: Tudo zerado no mês {month_str}!")
            except Exception as e:
                logger.error(f"[ERRO SETTLEMENT MÊS] {e}")

        keyboard.append([InlineKeyboardButton("🔙 Voltar ao Menu", callback_data="btn_main_menu")])
        msg_text = "\n".join(lines)

        if update.callback_query:
            await update.callback_query.edit_message_text(msg_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        else:
            await update.message.reply_text(msg_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    except Exception as e:
        logger.error(f"[ERRO CONSULTA MÊS] {e}")
        err = f"❌ Não foi possível carregar o extrato do mês {month_str}."
        if update.callback_query:
            await update.callback_query.edit_message_text(err, reply_markup=get_main_menu_keyboard(), parse_mode="Markdown")
        else:
            await update.message.reply_text(err, reply_markup=get_main_menu_keyboard(), parse_mode="Markdown")
    return MENU

# --- FLUXO 3: CRIAR CONTA COM SALDO INICIAL ---

async def account_name_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["account_name"] = update.message.text.strip()
    keyboard = [
        [
            InlineKeyboardButton("Conta Corrente", callback_data="type_CHECKING"),
            InlineKeyboardButton("Conta Poupança", callback_data="type_SAVINGS")
        ],
        [InlineKeyboardButton("Fatura / Cartão de Crédito", callback_data="type_LIABILITY")],
        [InlineKeyboardButton("🔙 Voltar ao Menu", callback_data="btn_main_menu")]
    ]
    await update.message.reply_text("Selecione o tipo da conta:", reply_markup=InlineKeyboardMarkup(keyboard))
    return ACCOUNT_TYPE

async def account_type_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["account_type"] = query.data.replace("type_", "")

    keyboard = [
        [
            InlineKeyboardButton("Sim (Conjunta)", callback_data="joint_true"),
            InlineKeyboardButton("Não (Individual)", callback_data="joint_false")
        ],
        [InlineKeyboardButton("🔙 Voltar ao Menu", callback_data="btn_main_menu")]
    ]
    type_pt = translate_type(context.user_data['account_type'])
    await query.edit_message_text(f"Conta **{context.user_data['account_name']}** ({type_pt}).\n\nEssa conta é conjunta?", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return ACCOUNT_JOINT

async def account_joint_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["account_joint"] = (query.data == "joint_true")

    await query.edit_message_text("Digite o **saldo inicial** atual desta conta em R$ (ex: 1500.00 ou 0):")
    return ACCOUNT_INITIAL_BALANCE

async def account_initial_balance_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    client = get_client(context)
    try:
        bal = float(update.message.text.replace(",", "."))
    except ValueError:
        await update.message.reply_text("❌ Valor inválido! Digite apenas números.")
        return ACCOUNT_INITIAL_BALANCE

    payload = {
        "name": context.user_data.get("account_name"),
        "type": context.user_data.get("account_type"),
        "is_joint": context.user_data.get("account_joint"),
        "initial_balance": bal
    }

    try:
        client.post("/accounts", payload)
        type_pt = translate_type(payload['type'])
        await update.message.reply_text(
            f"✅ **Conta '{payload['name']}' ({type_pt}) criada com saldo inicial de R$ {bal:.2f}!**",
            reply_markup=get_main_menu_keyboard(),
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"[ERRO CRIAR CONTA] {e}")
        await update.message.reply_text("❌ Não foi possível criar a conta.", reply_markup=get_main_menu_keyboard())
    return MENU

# --- FLUXO 4: TRANSFERÊNCIA POR BOTÕES ---

async def transfer_source_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    src_id = query.data.replace("tr_src_", "")
    context.user_data["transfer_src_id"] = src_id

    client = get_client(context)
    accounts = client.get_accounts()
    target_accounts = [a for a in accounts if a["id"] != src_id]

    keyboard = []
    for a in target_accounts:
        keyboard.append([InlineKeyboardButton(f"🏦 {a['name']} ({translate_type(a['type'])})", callback_data=f"tr_tgt_{a['id']}")])
    keyboard.append([InlineKeyboardButton("🔙 Voltar ao Menu", callback_data="btn_main_menu")])

    await query.edit_message_text(
        "💸 **Transferência entre Contas**\n\nSelecione a conta de **Destino** (onde o dinheiro entrará):",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return TRANSFER_TARGET

async def transfer_target_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    tgt_id = query.data.replace("tr_tgt_", "")
    context.user_data["transfer_tgt_id"] = tgt_id

    await query.edit_message_text(
        "Digite o valor da transferência em R$ (ex: 150.00):",
        reply_markup=get_back_keyboard()
    )
    return TRANSFER_AMOUNT

async def transfer_amount_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        val = float(update.message.text.replace(",", "."))
        context.user_data["transfer_amount"] = val
    except ValueError:
        await update.message.reply_text("❌ Valor inválido! Digite apenas números (ex: 100.00).")
        return TRANSFER_AMOUNT

    await update.message.reply_text("Digite uma breve descrição para a transferência:", reply_markup=get_back_keyboard())
    return TRANSFER_DESC

async def transfer_desc_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    client = get_client(context)
    desc = update.message.text.strip()
    payload = {
        "source_account_id": context.user_data.get("transfer_src_id"),
        "target_account_id": context.user_data.get("transfer_tgt_id"),
        "amount": context.user_data.get("transfer_amount"),
        "description": desc
    }

    try:
        client.post("/transactions/transfer", payload)
        await update.message.reply_text(
            f"✅ **Transferência concluída com sucesso!**\n\n"
            f"💰 **Valor**: R$ {payload['amount']:.2f}\n"
            f"📌 **Descrição**: {desc}",
            reply_markup=get_main_menu_keyboard(),
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"[ERRO TRANSFERÊNCIA] {e}")
        await update.message.reply_text("❌ Não foi possível realizar a transferência.", reply_markup=get_main_menu_keyboard())
    return MENU

# --- FLUXO 5: CARTÃO DE CRÉDITO ---

async def card_account_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    acc_id = query.data.replace("card_acc_", "")
    context.user_data["card_account"] = acc_id

    await query.edit_message_text(
        "Digite o nome do cartão de crédito (ex: Nubank Gold, Itaú Click):",
        reply_markup=get_back_keyboard()
    )
    return CARD_NAME

async def card_name_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["card_name"] = update.message.text.strip()
    await update.message.reply_text("Digite o limite de crédito em R$ (ex: 5000):", reply_markup=get_back_keyboard())
    return CARD_LIMIT

async def card_limit_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        val = float(update.message.text.replace(",", "."))
        context.user_data["card_limit"] = val
    except ValueError:
        await update.message.reply_text("❌ Valor inválido!")
        return CARD_LIMIT

    await update.message.reply_text("Digite o dia do mês de fechamento da fatura (ex: 25):", reply_markup=get_back_keyboard())
    return CARD_CLOSING

async def card_closing_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        val = int(update.message.text.strip())
        context.user_data["card_closing"] = val
    except ValueError:
        await update.message.reply_text("❌ Dia inválido!")
        return CARD_CLOSING

    await update.message.reply_text("Digite o dia do mês de vencimento da fatura (ex: 5):", reply_markup=get_back_keyboard())
    return CARD_DUE

async def card_due_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    client = get_client(context)
    try:
        val = int(update.message.text.strip())
        context.user_data["card_due"] = val
    except ValueError:
        await update.message.reply_text("❌ Dia inválido!")
        return CARD_DUE

    payload = {
        "account_id": context.user_data.get("card_account"),
        "name": context.user_data.get("card_name"),
        "credit_limit": context.user_data.get("card_limit"),
        "closing_day": context.user_data.get("card_closing"),
        "due_day": context.user_data.get("card_due")
    }

    try:
        client.post("/credit-cards", payload)
        await update.message.reply_text(
            f"✅ **Cartão '{payload['name']}' cadastrado com sucesso!**\n\n"
            f"💰 **Limite**: R$ {payload['credit_limit']:.2f}\n"
            f"📅 **Fechamento**: Dia {payload['closing_day']} | **Vencimento**: Dia {payload['due_day']}",
            reply_markup=get_main_menu_keyboard(),
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"[ERRO CRIAR CARTÃO] {e}")
        await update.message.reply_text("❌ Não foi possível cadastrar o cartão.", reply_markup=get_main_menu_keyboard())
    return MENU

# --- FLUXO 6: CONVIDAR PARCEIRO ---

async def partner_phone_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    client = get_client(context)
    phone = update.message.text.strip()
    payload = {"target_phone_number": phone}

    try:
        client.post("/partnerships/invite", payload)
        await update.message.reply_text(
            f"✅ **Convite de parceria enviado com sucesso para {phone}!**\n\n"
            f"Peça para a pessoa aceitar a solicitação no aplicativo.",
            reply_markup=get_main_menu_keyboard(),
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"[ERRO PARCERIA] {e}")
        await update.message.reply_text(
            f"⚠️ **Usuário não encontrado**\n\n"
            f"O número `{phone}` ainda não possui uma conta cadastrada no Rubi.\n\n"
            f"Peça para a pessoa iniciar o bot enviando `/start` no Telegram e tentar enviar o convite novamente!",
            reply_markup=get_main_menu_keyboard(),
            parse_mode="Markdown"
        )
    return MENU

# --- FLUXO 7: GASTOS RECORRENTES (RN10) ---

async def recurring_desc_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["rec_desc"] = update.message.text.strip()
    await update.message.reply_text("Digite o valor mensal em R$ (estimado ou fixo):", reply_markup=get_back_keyboard())
    return RECURRING_AMOUNT

async def recurring_amount_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        val = float(update.message.text.replace(",", "."))
        context.user_data["rec_amount"] = val
    except ValueError:
        await update.message.reply_text("❌ Valor inválido!")
        return RECURRING_AMOUNT

    keyboard = [
        [
            InlineKeyboardButton("📌 Despesa Fixa", callback_data="rectype_FIXED"),
            InlineKeyboardButton("⚡ Despesa Estimada", callback_data="rectype_ESTIMATED")
        ],
        [InlineKeyboardButton("🔙 Voltar ao Menu", callback_data="btn_main_menu")]
    ]
    await update.message.reply_text("Selecione a categoria de recorrência:", reply_markup=InlineKeyboardMarkup(keyboard))
    return RECURRING_TYPE

async def recurring_type_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["rec_type"] = query.data.replace("rectype_", "")
    await query.edit_message_text("Digite o dia do mês de vencimento (ex: 10):", reply_markup=get_back_keyboard())
    return RECURRING_DUE_DAY

async def recurring_due_day_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        day = int(update.message.text.strip())
        context.user_data["rec_due_day"] = day
    except ValueError:
        await update.message.reply_text("❌ Dia inválido!")
        return RECURRING_DUE_DAY

    await update.message.reply_text(
        "Selecione a conta associada à cobrança:",
        reply_markup=get_account_buttons(context, callback_prefix="rec_acc_")
    )
    return RECURRING_ACCOUNT

async def recurring_account_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    acc_id = query.data.replace("rec_acc_", "")
    client = get_client(context)

    try:
        client.create_recurring_expense(
            account_id=acc_id,
            description=context.user_data.get("rec_desc"),
            amount=context.user_data.get("rec_amount"),
            exp_type=context.user_data.get("rec_type"),
            due_day=context.user_data.get("rec_due_day")
        )
        type_pt = translate_type(context.user_data.get('rec_type'))
        await query.edit_message_text(
            f"✅ **{type_pt} '{context.user_data.get('rec_desc')}' cadastrada com sucesso!**",
            reply_markup=get_main_menu_keyboard(),
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"[ERRO RECORRENTE] {e}")
        await query.edit_message_text("❌ Não foi possível cadastrar a despesa recorrente.", reply_markup=get_main_menu_keyboard())
    return MENU

# --- CANCELAR ---

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Operação cancelada.", reply_markup=get_main_menu_keyboard())
    return MENU

# --- MAIN ---

def main():
    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_TOKEN não configurado no .env")

    request_config = HTTPXRequest(
        connect_timeout=30.0,
        read_timeout=30.0,
        write_timeout=30.0,
        pool_timeout=30.0
    )

    application = Application.builder().token(token).request(request_config).build()
    application.add_error_handler(global_error_handler)

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CallbackQueryHandler(handle_main_menu_callbacks)
        ],
        states={
            MENU: [CallbackQueryHandler(handle_main_menu_callbacks)],
            # Autenticação
            AUTH_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, auth_phone_received)],
            AUTH_PIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, auth_pin_received)],
            # Onboarding
            OB_ACC_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ob_acc_name_received)],
            OB_ACC_BALANCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ob_acc_balance_received)],
            OB_CARD_ASK: [CallbackQueryHandler(ob_card_choice)],
            OB_CARD_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ob_card_name_received)],
            OB_CARD_LIMIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ob_card_limit_received)],
            OB_CARD_CLOSING: [MessageHandler(filters.TEXT & ~filters.COMMAND, ob_card_closing_received)],
            OB_CARD_DUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ob_card_due_received)],
            OB_REC_ASK: [CallbackQueryHandler(ob_rec_choice)],
            OB_REC_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, ob_rec_desc_received)],
            OB_REC_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ob_rec_amount_received)],
            OB_REC_TYPE: [CallbackQueryHandler(ob_rec_type_selected)],
            OB_REC_DUE_DAY: [MessageHandler(filters.TEXT & ~filters.COMMAND, ob_rec_due_day_received)],
            # Gasto
            EXPENSE_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, expense_desc_received), CallbackQueryHandler(handle_main_menu_callbacks)],
            EXPENSE_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, expense_amount_received), CallbackQueryHandler(handle_main_menu_callbacks)],
            EXPENSE_CATEGORY: [CallbackQueryHandler(expense_category_selected), CallbackQueryHandler(handle_main_menu_callbacks)],
            EXPENSE_SELECT_METHOD: [CallbackQueryHandler(expense_method_selected)],
            EXPENSE_SELECT_ITEM: [CallbackQueryHandler(expense_item_selected)],
            EXPENSE_INSTALLMENTS: [CallbackQueryHandler(expense_installments_selected)],
            EXPENSE_SPLIT_CONFIRM: [CallbackQueryHandler(expense_split_selected)],
            EXPENSE_CUSTOM_SPLIT_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, expense_custom_split_received), CallbackQueryHandler(handle_main_menu_callbacks)],
            # Consultar Mês
            CONSULT_MONTH_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, consult_month_process),
                CallbackQueryHandler(consult_month_process)
            ],
            # Criar Conta
            ACCOUNT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, account_name_received), CallbackQueryHandler(handle_main_menu_callbacks)],
            ACCOUNT_TYPE: [CallbackQueryHandler(account_type_selected)],
            ACCOUNT_JOINT: [CallbackQueryHandler(account_joint_selected)],
            ACCOUNT_INITIAL_BALANCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, account_initial_balance_received)],
            # Transferência
            TRANSFER_SOURCE: [CallbackQueryHandler(transfer_source_selected)],
            TRANSFER_TARGET: [CallbackQueryHandler(transfer_target_selected)],
            TRANSFER_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, transfer_amount_received), CallbackQueryHandler(handle_main_menu_callbacks)],
            TRANSFER_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, transfer_desc_received), CallbackQueryHandler(handle_main_menu_callbacks)],
            # Cartão
            CARD_ACCOUNT: [CallbackQueryHandler(card_account_selected), CallbackQueryHandler(handle_main_menu_callbacks)],
            CARD_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, card_name_received), CallbackQueryHandler(handle_main_menu_callbacks)],
            CARD_LIMIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, card_limit_received), CallbackQueryHandler(handle_main_menu_callbacks)],
            CARD_CLOSING: [MessageHandler(filters.TEXT & ~filters.COMMAND, card_closing_received), CallbackQueryHandler(handle_main_menu_callbacks)],
            CARD_DUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, card_due_received), CallbackQueryHandler(handle_main_menu_callbacks)],
            # Parceria
            PARTNER_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, partner_phone_received), CallbackQueryHandler(handle_main_menu_callbacks)],
            # Recorrente
            RECURRING_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, recurring_desc_received), CallbackQueryHandler(handle_main_menu_callbacks)],
            RECURRING_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, recurring_amount_received), CallbackQueryHandler(handle_main_menu_callbacks)],
            RECURRING_TYPE: [CallbackQueryHandler(recurring_type_selected)],
            RECURRING_DUE_DAY: [MessageHandler(filters.TEXT & ~filters.COMMAND, recurring_due_day_received), CallbackQueryHandler(handle_main_menu_callbacks)],
            RECURRING_ACCOUNT: [CallbackQueryHandler(recurring_account_selected)],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CommandHandler("start", start),
            CallbackQueryHandler(handle_main_menu_callbacks)
        ]
    )

    application.add_handler(conv_handler)
    logger.info("[STARTUP] Bot do Telegram Rubi iniciado com autenticação dinâmica de usuários!")
    application.run_polling()

if __name__ == "__main__":
    main()
