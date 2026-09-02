/* JavaScript do Protótipo de Baixa Fidelidade - Rubi Finanças (v1.1.1 - Caixinhas POCKET & Metas por Conta) */

function getApiBase() {
  if (window.location.protocol === 'file:') {
    return 'http://localhost:8080/api';
  }
  return '/api';
}

const CATEGORIES = {
  "PETS": "🐶 Pets / Animais",
  "BARS_AND_RESTAURANTS": "🍹 Bares e Restaurantes",
  "DELIVERY": "🛵 Delivery / Entregas",
  "SHOPPING": "🛍️ Compras / Shopping",
  "HOUSING": "🏠 Moradia / Habitação",
  "DONATIONS": "🤝 Doações",
  "EDUCATION": "📚 Educação",
  "ENTERTAINMENT": "🎬 Entretenimento / Lazer",
  "TAXES_AND_FEES": "🧾 Impostos e Taxas",
  "INVESTMENTS": "📈 Investimentos (Transferências para Caixinhas)",
  "SUPERMARKET": "🛒 Supermercado",
  "UNCATEGORIZED": "📦 Sem Categoria",
  "PAYMENTS": "💳 Pagamentos",
  "SERVICE_PROVIDERS": "🛠️ Prestadores de Serviço",
  "RECEIPTS": "💰 Recebimentos",
  "HEALTH": "🏥 Saúde",
  "DIGITAL_SERVICES": "💻 Serviços Digitais / Assinaturas",
  "TRANSFERS": "🔄 Transferências",
  "TRANSPORT": "🚗 Transporte / Combustível",
  "TRAVEL": "✈️ Viagens"
};

const ACCOUNT_TYPE_MAP = {
  "CHECKING": "Conta Corrente (Líquido)",
  "POCKET": "Caixinha / Reserva / Investimento",
  "SAVINGS": "Caixinha / Reserva",
  "LIABILITY": "Passivo / Cartão de Crédito"
};

let globalAccountsCache = [];
let globalCardsCache = [];
let globalMasterRecurringCache = [];
let globalForecastResponse = null;
let selectedForecastMonth = null;

// --- PHONE NUMBER FORMATTER (E.164) ---
function formatE164Phone(phoneStr) {
  if (!phoneStr) return '';
  let trimmed = phoneStr.trim();
  if (trimmed.startsWith('+')) {
    let digits = trimmed.substring(1).replace(/\D/g, '');
    return '+' + digits;
  }
  let digits = trimmed.replace(/\D/g, '');
  if (digits.length === 10 || digits.length === 11) {
    return '+55' + digits;
  }
  return '+' + digits;
}

// --- LOGGING UTILITIES ---
function log(message, type = 'info') {
  const logContent = document.getElementById('logContent');
  if (!logContent) return;
  const time = new Date().toLocaleTimeString();
  const entry = document.createElement('div');
  entry.className = `log-entry ${type}`;
  entry.textContent = `[${time}] ${message}`;
  logContent.appendChild(entry);
  logContent.scrollTop = logContent.scrollHeight;
}

function clearLogs() {
  const logContent = document.getElementById('logContent');
  if (logContent) logContent.innerHTML = '';
}

// --- TAB NAVIGATION ---
function switchTab(tabName) {
  const buttons = document.querySelectorAll('.tab-btn');
  const panes = document.querySelectorAll('.tab-pane');

  buttons.forEach(btn => btn.classList.remove('active'));
  panes.forEach(pane => pane.classList.remove('active'));

  const activePane = document.getElementById(`tab-${tabName}`);
  if (activePane) activePane.classList.add('active');

  const activeBtn = Array.from(buttons).find(btn => btn.getAttribute('onclick')?.includes(tabName));
  if (activeBtn) activeBtn.classList.add('active');

  // Trigger auto-loads on tab view if logged in
  if (getToken()) {
    if (tabName === 'accounts') loadAccounts();
    if (tabName === 'transactions') { populateAccountSelects(); loadTransactions(); }
    if (tabName === 'cards') { loadAccounts(); loadCreditCards(); populateCategorySelects(); }
    if (tabName === 'forecast') { populateAccountSelects(); loadCreditCards(); populateCategorySelects(); loadForecast(); loadRecurringMasterList(); }
    if (tabName === 'budgets') { populateCategorySelects(); loadCategoryBudgets(); }
  }
}

// --- AUTHENTICATION STATE ---
function getToken() {
  return localStorage.getItem('rubi_jwt_token');
}

function setToken(token) {
  if (token) {
    localStorage.setItem('rubi_jwt_token', token);
  } else {
    localStorage.removeItem('rubi_jwt_token');
  }
  updateAuthUI();
}

function updateAuthUI() {
  const token = getToken();
  const badge = document.getElementById('authStatusBadge');
  const userInfo = document.getElementById('userInfo');
  const logoutBtn = document.getElementById('logoutBtn');

  if (token) {
    badge.textContent = 'Conectado (JWT Ativo)';
    badge.className = 'badge logged-in';
    userInfo.textContent = 'Sessão Ativa';
    logoutBtn.style.display = 'inline-block';
  } else {
    badge.textContent = 'Desconectado';
    badge.className = 'badge logged-out';
    userInfo.textContent = 'Faça login para utilizar as funções.';
    logoutBtn.style.display = 'none';
  }
}

function logout() {
  setToken(null);
  log('Sessão encerrada com sucesso.', 'info');
}

// --- HTTP FETCH HELPER ---
async function apiCall(endpoint, method = 'GET', body = null) {
  const headers = {
    'Content-Type': 'application/json'
  };
  const token = getToken();
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const options = { method, headers };
  if (body) {
    options.body = JSON.stringify(body);
  }

  const baseUrl = getApiBase();
  log(`HttpRequest: ${method} ${baseUrl}${endpoint}`, 'info');

  try {
    const res = await fetch(`${baseUrl}${endpoint}`, options);
    
    let resData = null;
    const contentType = res.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
      resData = await res.json();
    } else {
      resData = await res.text();
    }

    if (res.ok) {
      log(`HttpResponse [${res.status}]: ${typeof resData === 'object' ? JSON.stringify(resData) : resData}`, 'success');
      return { ok: true, status: res.status, data: resData };
    } else {
      log(`HttpError [${res.status}]: ${typeof resData === 'object' ? JSON.stringify(resData) : resData}`, 'error');
      return { ok: false, status: res.status, data: resData };
    }
  } catch (err) {
    log(`Network/Client Error: ${err.message}`, 'error');
    return { ok: false, status: 0, data: err.message };
  }
}

// --- AUTH HANDLERS ---
async function handleLogin(e) {
  e.preventDefault();
  const rawPhone = document.getElementById('loginPhone').value;
  const pin = document.getElementById('loginPin').value.trim();
  const formattedPhone = formatE164Phone(rawPhone);

  if (!formattedPhone || formattedPhone.length < 8) {
    alert('Por favor, informe um número de telefone válido (ex: 11999999999 ou +5511999999999).');
    return;
  }

  log(`Tentando login com telefone formatado: ${formattedPhone}`);
  const res = await apiCall('/auth/login', 'POST', { phone_number: formattedPhone, pin: pin });
  if (res.ok && res.data.token) {
    setToken(res.data.token);
    alert('Login realizado com sucesso!');
    switchTab('accounts');
  } else {
    const errorDetail = res.data && res.data.error ? res.data.error : (res.status === 400 ? 'Telefone ou PIN incorretos.' : 'Falha no login');
    alert(`Erro no login (${res.status}): ${errorDetail}`);
  }
}

async function handleRegister(e) {
  e.preventDefault();
  const name = document.getElementById('regName').value.trim();
  const rawPhone = document.getElementById('regPhone').value;
  const pin = document.getElementById('regPin').value.trim();
  const formattedPhone = formatE164Phone(rawPhone);

  if (!formattedPhone || formattedPhone.length < 8) {
    alert('Por favor, informe um número de telefone válido (ex: 11988888888 ou +5511988888888).');
    return;
  }

  log(`Cadastrando usuário: ${name}, ${formattedPhone}`);
  const res = await apiCall('/users/register', 'POST', { name, phone_number: formattedPhone, pin });
  if (res.ok) {
    alert('Usuário cadastrado com sucesso!');
    if (res.data && res.data.token) {
      setToken(res.data.token);
      switchTab('accounts');
    }
  } else if (res.status === 409) {
    alert('Conflito: Este número de telefone já está cadastrado. Tente realizar o login.');
  } else {
    const errorDetail = res.data && res.data.error ? res.data.error : 'Verifique os dados informados.';
    alert(`Erro ao cadastrar (${res.status}): ${errorDetail}`);
  }
}

async function handleTelegramLink(e) {
  e.preventDefault();
  const chatId = document.getElementById('telegramChatId').value.trim();
  const res = await apiCall('/users/telegram-link', 'POST', { telegram_chat_id: chatId });
  if (res.ok) {
    alert('Telegram vinculado com sucesso! Agora você pode interagir com a IA pelo Telegram.');
  } else {
    alert('Erro ao vincular Telegram. Certifique-se de estar conectado.');
  }
}

// --- ACCOUNTS & CAIXINHAS HANDLERS ---
function toggleAccountGoalInput() {
  const type = document.getElementById('accType').value;
  const goalGroup = document.getElementById('accGoalGroup');
  if (type === 'POCKET') {
    goalGroup.style.display = 'block';
  } else {
    goalGroup.style.display = 'none';
  }
}

async function loadAccounts() {
  const res = await apiCall('/accounts', 'GET');
  const tbody = document.getElementById('accountsTableBody');
  tbody.innerHTML = '';

  if (res.ok && Array.isArray(res.data)) {
    globalAccountsCache = res.data;
    populateAccountSelects();

    if (res.data.length === 0) {
      tbody.innerHTML = '<tr><td colspan="5">Nenhuma conta ou Caixinha cadastrada.</td></tr>';
      return;
    }

    res.data.forEach(acc => {
      const tr = document.createElement('tr');
      const typeLabel = ACCOUNT_TYPE_MAP[acc.type] || acc.type;
      const isPocket = acc.type === 'POCKET' || acc.type === 'SAVINGS';

      let goalHtml = 'N/A';
      if (isPocket && acc.goal_amount) {
        const prog = acc.current_month_progress || 0.0;
        const pct = Math.min((prog / acc.goal_amount) * 100.0, 100.0);
        goalHtml = `
          <div><strong>${formatCurrency(acc.goal_amount)}</strong>/mês</div>
          <div style="width: 100%; background-color: #e9ecef; border-radius: 4px; overflow: hidden; height: 12px; margin-top: 4px;">
            <div style="width: ${pct}%; background-color: var(--success-color); height: 100%;"></div>
          </div>
          <small>${formatCurrency(prog)} guardados (${pct.toFixed(0)}%)</small>
        `;
      } else if (isPocket) {
        goalHtml = '<small style="color:#666;">Sem meta configurada</small>';
      }

      tr.innerHTML = `
        <td><strong>${escapeHtml(acc.name)}</strong> ${isPocket ? '<span class="badge" style="background:#eef6fc; color:#0366d6; border:1px solid #b6d4fe;">📦 Caixinha</span>' : ''}</td>
        <td>${typeLabel}</td>
        <td><strong>${formatCurrency(acc.balance)}</strong></td>
        <td style="min-width: 160px;">${goalHtml}</td>
        <td>
          <button onclick="editAccount('${acc.id}')" class="btn-sm">Editar</button>
          <button onclick="deleteAccount('${acc.id}')" class="btn-sm btn-danger">Excluir</button>
        </td>
      `;
      tbody.appendChild(tr);
    });
  } else {
    tbody.innerHTML = `<tr><td colspan="5" class="text-error">Erro ao carregar contas (${res.status}).</td></tr>`;
  }
}

function resetAccountForm() {
  document.getElementById('accountId').value = '';
  document.getElementById('accName').value = '';
  document.getElementById('accType').value = 'CHECKING';
  document.getElementById('accBalance').value = '0.00';
  document.getElementById('accGoal').value = '';
  toggleAccountGoalInput();

  document.getElementById('accountFormTitle').textContent = 'Nova Conta / Caixinha';
  document.getElementById('accSubmitBtn').textContent = 'Salvar Conta / Caixinha';
  document.getElementById('accCancelBtn').style.display = 'none';
}

function editAccount(id) {
  const acc = globalAccountsCache.find(a => a.id === id);
  if (!acc) return;
  document.getElementById('accountId').value = acc.id;
  document.getElementById('accName').value = acc.name;
  document.getElementById('accType').value = acc.type === 'SAVINGS' ? 'POCKET' : acc.type;
  document.getElementById('accBalance').value = acc.balance;
  document.getElementById('accGoal').value = acc.goal_amount || '';
  toggleAccountGoalInput();

  document.getElementById('accountFormTitle').textContent = 'Editar Conta / Caixinha';
  document.getElementById('accSubmitBtn').textContent = 'Atualizar Conta / Caixinha';
  document.getElementById('accCancelBtn').style.display = 'inline-block';
}

async function handleAccountSubmit(e) {
  e.preventDefault();
  const id = document.getElementById('accountId').value;
  const goalVal = document.getElementById('accGoal').value;

  const body = {
    name: document.getElementById('accName').value.trim(),
    type: document.getElementById('accType').value,
    initial_balance: parseFloat(document.getElementById('accBalance').value),
    goal_amount: goalVal ? parseFloat(goalVal) : null
  };

  let res;
  if (id) {
    res = await apiCall(`/accounts/${id}`, 'PUT', body);
  } else {
    res = await apiCall('/accounts', 'POST', body);
  }

  if (res.ok) {
    alert(id ? 'Conta/Caixinha atualizada com sucesso!' : 'Conta/Caixinha criada com sucesso!');
    resetAccountForm();
    loadAccounts();
  } else {
    const detail = res.data && res.data.error ? res.data.error : '';
    alert(`Erro ao salvar conta (${res.status}): ${detail}`);
  }
}

async function deleteAccount(id) {
  if (!confirm('Deseja realmente desativar/excluir esta conta?')) return;
  const res = await apiCall(`/accounts/${id}`, 'DELETE');
  if (res.ok) {
    alert('Conta excluída com sucesso.');
    loadAccounts();
  } else {
    alert('Erro ao excluir conta.');
  }
}

function populateAccountSelects() {
  const selectIds = ['filterAccount', 'txAccount', 'trFromAccount', 'trToAccount', 'recAccount', 'cardAccount'];
  selectIds.forEach(selectId => {
    const el = document.getElementById(selectId);
    if (!el) return;
    const currentVal = el.value;
    el.innerHTML = selectId === 'filterAccount' ? '<option value="">Todas as Contas</option>' : (selectId === 'cardAccount' ? '<option value="">-- Selecione a Conta (Preferencialmente LIABILITY) --</option>' : '');
    
    globalAccountsCache.forEach(acc => {
      const typeLabel = ACCOUNT_TYPE_MAP[acc.type] || acc.type;
      const isPocket = acc.type === 'POCKET' || acc.type === 'SAVINGS';
      const isLiability = acc.type === 'LIABILITY';
      const opt = document.createElement('option');
      opt.value = acc.id;
      opt.textContent = `${acc.name} (${typeLabel}) - ${formatCurrency(acc.balance)}${isPocket ? ' [📦 Caixinha]' : ''}${isLiability ? ' [Passivo/Cartão]' : ''}`;
      el.appendChild(opt);
    });

    if (currentVal) el.value = currentVal;
  });
}

function populateCardSelects() {
  const selectIds = ['recCard', 'cpCard', 'selectCardInvoice'];
  selectIds.forEach(selectId => {
    const el = document.getElementById(selectId);
    if (!el) return;
    const currentVal = el.value;
    el.innerHTML = selectId === 'selectCardInvoice' || selectId === 'cpCard' ? '<option value="">-- Selecione o Cartão --</option>' : '';

    globalCardsCache.forEach(card => {
      const opt = document.createElement('option');
      opt.value = card.id;
      opt.textContent = `${card.name} (Dia fech. ${card.closing_day} / dia venc. ${card.due_day})`;
      el.appendChild(opt);
    });

    if (currentVal) el.value = currentVal;
  });
}

function toggleRecTargetSelects() {
  const targetType = document.getElementById('recTargetType').value;
  const accGroup = document.getElementById('recAccountGroup');
  const cardGroup = document.getElementById('recCardGroup');

  if (targetType === 'CARD') {
    accGroup.style.display = 'none';
    cardGroup.style.display = 'block';
  } else {
    accGroup.style.display = 'block';
    cardGroup.style.display = 'none';
  }
}

// --- TRANSACTIONS HANDLERS ---
async function loadTransactions() {
  const month = document.getElementById('filterMonth').value;
  const accountId = document.getElementById('filterAccount').value;
  const category = document.getElementById('filterCategory').value;

  let query = [];
  if (month) query.push(`month=${month}`);
  if (accountId) query.push(`account_id=${accountId}`);
  if (category) query.push(`category=${category}`);

  const queryString = query.length > 0 ? `?${query.join('&')}` : '';
  const res = await apiCall(`/transactions${queryString}`, 'GET');
  const tbody = document.getElementById('transactionsTableBody');
  tbody.innerHTML = '';

  if (res.ok && Array.isArray(res.data)) {
    if (res.data.length === 0) {
      tbody.innerHTML = '<tr><td colspan="7">Nenhuma transação encontrada no período.</td></tr>';
      return;
    }

    res.data.forEach(tx => {
      const tr = document.createElement('tr');
      const isDebit = tx.type === 'DEBIT' || tx.type === 'EXPENSE';
      const amountColor = isDebit ? 'color: var(--error-color);' : 'color: var(--success-color);';
      const sign = isDebit ? '-' : '+';
      const typeLabel = isDebit ? 'Despesa (Débito)' : 'Receita (Crédito)';
      const formattedDate = tx.date ? new Date(tx.date).toLocaleString('pt-BR') : (tx.reference_date ? new Date(tx.reference_date).toLocaleString('pt-BR') : '');

      tr.innerHTML = `
        <td>${formattedDate}</td>
        <td><strong>${escapeHtml(tx.description)}</strong></td>
        <td>${typeLabel}</td>
        <td style="${amountColor}"><strong>${sign} ${formatCurrency(tx.amount)}</strong></td>
        <td>${formatCategory(tx.category)}</td>
        <td>${getAccountName(tx.account_id)}</td>
        <td>
          <button onclick="deleteTransaction('${tx.id}')" class="btn-sm btn-danger">Excluir</button>
        </td>
      `;
      tbody.appendChild(tr);
    });
  } else {
    tbody.innerHTML = `<tr><td colspan="7">Erro ao carregar extrato de transações (${res.status}).</td></tr>`;
  }
}

async function handleTransactionSubmit(e) {
  e.preventDefault();
  const body = {
    account_id: document.getElementById('txAccount').value,
    amount: parseFloat(document.getElementById('txAmount').value),
    type: document.getElementById('txType').value,
    description: document.getElementById('txDescription').value.trim(),
    category: document.getElementById('txCategory').value,
    reference_date: document.getElementById('txDate').value ? new Date(document.getElementById('txDate').value).toISOString() : new Date().toISOString()
  };

  const res = await apiCall('/transactions', 'POST', body);
  if (res.ok) {
    alert('Transação registrada com sucesso!');
    document.getElementById('txDescription').value = '';
    document.getElementById('txAmount').value = '';
    loadTransactions();
    loadAccounts();
  } else {
    const detail = res.data && res.data.error ? res.data.error : '';
    alert(`Erro ao registrar transação (${res.status}): ${detail}`);
  }
}

async function handleTransferSubmit(e) {
  e.preventDefault();
  const fromAcc = document.getElementById('trFromAccount').value;
  const toAcc = document.getElementById('trToAccount').value;
  if (fromAcc === toAcc) {
    alert('A conta de origem e destino devem ser diferentes!');
    return;
  }

  const body = {
    source_account_id: fromAcc,
    target_account_id: toAcc,
    amount: parseFloat(document.getElementById('trAmount').value),
    description: document.getElementById('trDescription').value.trim(),
    date: document.getElementById('trDate').value
  };

  const res = await apiCall('/transactions/transfer', 'POST', body);
  if (res.ok) {
    alert('Transferência / Aporte realizado com sucesso!');
    document.getElementById('trAmount').value = '';
    loadTransactions();
    loadAccounts();
  } else {
    alert('Erro ao realizar transferência.');
  }
}

async function deleteTransaction(id) {
  if (!confirm('Deseja realmente estornar/excluir esta transação?')) return;
  const res = await apiCall(`/transactions/${id}`, 'DELETE');
  if (res.ok) {
    alert('Transação excluída com sucesso.');
    loadTransactions();
    loadAccounts();
  } else {
    alert('Erro ao excluir transação.');
  }
}

// --- CREDIT CARDS & INVOICES HANDLERS ---
async function loadCreditCards() {
  const res = await apiCall('/credit-cards', 'GET');
  const tbody = document.getElementById('cardsTableBody');

  tbody.innerHTML = '';

  if (res.ok && Array.isArray(res.data)) {
    globalCardsCache = res.data;
    populateCardSelects();

    if (res.data.length === 0) {
      tbody.innerHTML = '<tr><td colspan="5">Nenhum cartão de crédito cadastrado.</td></tr>';
      return;
    }

    res.data.forEach(card => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td><strong>${escapeHtml(card.name)}</strong></td>
        <td>Dia ${card.closing_day}</td>
        <td>Dia ${card.due_day}</td>
        <td>${formatCurrency(card.credit_limit)}</td>
        <td>
          <button onclick="selectCardForInvoices('${card.id}')" class="btn-sm">Ver Faturas</button>
        </td>
      `;
      tbody.appendChild(tr);
    });
  } else {
    tbody.innerHTML = '<tr><td colspan="5">Erro ao carregar cartões de crédito.</td></tr>';
  }
}

async function handleCardSubmit(e) {
  e.preventDefault();
  const accId = document.getElementById('cardAccount').value;
  if (!accId) {
    alert('Selecione a conta vinculada ao cartão!');
    return;
  }

  const body = {
    account_id: accId,
    name: document.getElementById('cardName').value.trim(),
    closing_day: parseInt(document.getElementById('cardClosingDay').value),
    due_day: parseInt(document.getElementById('cardDueDay').value),
    credit_limit: parseFloat(document.getElementById('cardLimit').value)
  };

  const res = await apiCall('/credit-cards', 'POST', body);
  if (res.ok) {
    alert('Cartão de crédito cadastrado com sucesso!');
    document.getElementById('cardName').value = '';
    loadCreditCards();
  } else {
    const detail = res.data && res.data.error ? res.data.error : 'A conta selecionada deve ser do tipo LIABILITY (Passivo)!';
    alert(`Erro ao cadastrar cartão (${res.status}): ${detail}`);
  }
}

async function handleCardPurchaseSubmit(e) {
  e.preventDefault();
  const cardId = document.getElementById('cpCard').value;
  if (!cardId) {
    alert('Selecione o cartão de crédito!');
    return;
  }

  const cpDateVal = document.getElementById('cpDate').value;
  const purchaseDateIso = cpDateVal ? new Date(cpDateVal + 'T12:00:00').toISOString() : new Date().toISOString();

  const body = {
    amount: parseFloat(document.getElementById('cpAmount').value),
    description: document.getElementById('cpDescription').value.trim(),
    category: document.getElementById('cpCategory').value,
    installments: parseInt(document.getElementById('cpInstallments').value),
    purchase_date: purchaseDateIso
  };

  const res = await apiCall(`/credit-cards/${cardId}/purchases`, 'POST', body);
  if (res.ok) {
    alert('Compra gravada com sucesso!');
    document.getElementById('cpAmount').value = '';
    document.getElementById('cpDescription').value = '';
    loadCardInvoices();
  } else {
    const detail = res.data && res.data.error ? res.data.error : '';
    alert(`Erro ao gravar compra no cartão (${res.status}): ${detail}`);
  }
}

function selectCardForInvoices(cardId) {
  document.getElementById('selectCardInvoice').value = cardId;
  loadCardInvoices();
}

async function loadCardInvoices() {
  const cardId = document.getElementById('selectCardInvoice').value;
  const tbody = document.getElementById('invoicesTableBody');
  if (!cardId) {
    tbody.innerHTML = '<tr><td colspan="4">Selecione um cartão para visualizar as faturas.</td></tr>';
    return;
  }

  const res = await apiCall(`/credit-cards/${cardId}/invoices`, 'GET');
  tbody.innerHTML = '';

  if (res.ok && Array.isArray(res.data)) {
    if (res.data.length === 0) {
      tbody.innerHTML = '<tr><td colspan="4">Nenhuma fatura encontrada para este cartão.</td></tr>';
      return;
    }

    res.data.forEach(inv => {
      const tr = document.createElement('tr');
      const isPaid = inv.status === 'PAID';
      const statusBadge = isPaid 
        ? '<span class="badge logged-in">PAGA</span>' 
        : '<span class="badge logged-out">ABERTA / PENDENTE</span>';

      tr.innerHTML = `
        <td><strong>${inv.reference_month || inv.month || 'N/A'}</strong></td>
        <td>${formatCurrency(inv.total_amount || inv.amount)}</td>
        <td>${statusBadge}</td>
        <td>
          ${!isPaid ? `<button onclick="payInvoicePrompt('${inv.id}', ${inv.total_amount || inv.amount})" class="btn-sm btn-success">Pagar Fatura</button>` : 'N/A'}
        </td>
      `;
      tbody.appendChild(tr);
    });
  } else {
    tbody.innerHTML = '<tr><td colspan="4">Erro ao carregar faturas do cartão.</td></tr>';
  }
}

async function payInvoicePrompt(invoiceId, amount) {
  const accId = prompt(`Selecione a conta para pagar a fatura de ${formatCurrency(amount)}:\nCopie e cole o ID de uma das suas contas.`);
  if (!accId) return;
  const res = await apiCall(`/invoices/${invoiceId}/pay`, 'POST', { source_account_id: accId, amount: amount });
  if (res.ok) {
    alert('Fatura paga com sucesso!');
    loadCardInvoices();
    loadAccounts();
  } else {
    alert('Erro ao pagar fatura.');
  }
}

// --- 🔮 FORECAST 12 MESES & CHECKLIST HANDLERS ---
async function loadForecast(startMonth = '') {
  let endpoint = '/forecast/monthly?months=12';
  if (startMonth) endpoint += `&start_month=${startMonth}`;

  const res = await apiCall(endpoint, 'GET');
  if (res.ok && res.data && Array.isArray(res.data.months)) {
    globalForecastResponse = res.data;
    if (!selectedForecastMonth || !res.data.months.some(m => m.month === selectedForecastMonth)) {
      selectedForecastMonth = res.data.months[0].month;
    }
    renderForecastUI();
  } else {
    document.getElementById('forecastTableBody').innerHTML = '<tr><td colspan="8">Erro ao carregar previsão de 12 meses.</td></tr>';
  }
}

function renderForecastUI() {
  if (!globalForecastResponse || !globalForecastResponse.months) return;

  // Render Month Buttons
  const container = document.getElementById('monthSelectorContainer');
  container.innerHTML = '';

  globalForecastResponse.months.forEach(mItem => {
    const btn = document.createElement('button');
    const isSelected = mItem.month === selectedForecastMonth;
    btn.className = `btn-sm ${isSelected ? 'btn-success' : ''}`;
    btn.style.padding = '6px 12px';
    btn.style.fontWeight = isSelected ? 'bold' : 'normal';
    btn.textContent = mItem.month;
    btn.onclick = () => {
      selectedForecastMonth = mItem.month;
      renderForecastUI();
    };
    container.appendChild(btn);
  });

  // Find selected month item
  const mData = globalForecastResponse.months.find(m => m.month === selectedForecastMonth);
  if (!mData) return;

  // Render Metrics
  document.getElementById('fcTotalIncome').textContent = formatCurrency(mData.total_income);
  document.getElementById('fcTotalExpense').textContent = formatCurrency(mData.total_expense);
  document.getElementById('fcTotalCard').textContent = formatCurrency(mData.credit_card_invoices_total);

  const netBalEl = document.getElementById('fcNetBalance');
  netBalEl.textContent = formatCurrency(mData.net_balance);
  netBalEl.style.color = mData.net_balance >= 0 ? 'var(--success-color)' : 'var(--error-color)';

  document.getElementById('checklistTitle').textContent = `📋 Checklist do Mês: ${mData.month}`;

  // Render Checklist Table
  const tbody = document.getElementById('forecastTableBody');
  tbody.innerHTML = '';

  if (!mData.checklist_items || mData.checklist_items.length === 0) {
    tbody.innerHTML = '<tr><td colspan="8">Nenhuma transação recorrente prevista para este mês. Cadastre novas regras abaixo!</td></tr>';
    return;
  }

  mData.checklist_items.forEach(item => {
    const tr = document.createElement('tr');
    const isIncome = item.type === 'INCOME';
    const typeLabel = isIncome ? 'Receita (Entrada)' : 'Despesa (Saída)';
    const amountColor = isIncome ? 'color: var(--success-color);' : 'color: var(--error-color);';
    const isFulfilled = item.status === 'REALIZADO';

    const statusBadge = isFulfilled
      ? '<span class="badge logged-in">✅ REALIZADO</span>'
      : '<span class="badge logged-out" style="background:#fff3cd; color:#856404; border:1px solid #ffeeba;">⏳ PREVISTO</span>';

    const targetBadge = item.credit_card_id 
      ? `<span class="badge" style="background:#eef6fc; color:#0366d6; border:1px solid #b6d4fe;">💳 Cartão: ${escapeHtml(item.credit_card_name || 'Cartão')}</span>`
      : `<span class="badge" style="background:#f6f8fa; color:#24292e; border:1px solid #d1d5da;">🏦 Conta: ${getAccountName(item.account_id)}</span>`;

    const overrideNotice = item.is_overridden ? ' <small style="color:#d9534f;">(Valor alterado no mês)</small>' : '';

    let actionButtons = '';
    if (isFulfilled) {
      actionButtons = `<small style="color:#28a745;">Quitado</small>`;
    } else {
      actionButtons = `
        <button onclick="fulfillChecklistItem('${item.recurring_transaction_id}', '${mData.month}')" class="btn-sm btn-success">✅ Dar Baixa</button>
        <button onclick="overrideChecklistItem('${item.recurring_transaction_id}', '${mData.month}', ${item.amount})" class="btn-sm">✏️ Editar no Mês</button>
      `;
    }

    tr.innerHTML = `
      <td><strong>${escapeHtml(item.description)}</strong>${overrideNotice}</td>
      <td>${typeLabel}</td>
      <td>Dia ${item.due_day}</td>
      <td style="${amountColor}"><strong>${formatCurrency(item.amount)}</strong></td>
      <td>${targetBadge}</td>
      <td>${formatCategory(item.category)}</td>
      <td>${statusBadge}</td>
      <td>${actionButtons}</td>
    `;
    tbody.appendChild(tr);
  });
}

async function fulfillChecklistItem(recId, month) {
  if (!confirm(`Deseja confirmar o pagamento/recebimento deste item para o mês ${month}? Se for no cartão de crédito, uma compra será lançada na fatura.`)) return;

  const res = await apiCall(`/recurring-transactions/${recId}/fulfill`, 'POST', { reference_month: month });
  if (res.ok) {
    alert('Item baixado com sucesso!');
    loadForecast(globalForecastResponse ? globalForecastResponse.start_month : '');
    loadAccounts();
  } else {
    alert('Erro ao dar baixa no item.');
  }
}

async function overrideChecklistItem(recId, currentMonth, currentAmount) {
  const newAmountStr = prompt(`Informe o novo valor específico para o mês ${currentMonth}:`, currentAmount);
  if (!newAmountStr) return;
  const newAmount = parseFloat(newAmountStr);
  if (isNaN(newAmount) || newAmount <= 0) {
    alert('Valor inválido!');
    return;
  }

  const res = await apiCall(`/recurring-transactions/${recId}/override`, 'PUT', { reference_month: currentMonth, override_amount: newAmount });
  if (res.ok) {
    alert(`Valor do mês ${currentMonth} atualizado para ${formatCurrency(newAmount)}!`);
    loadForecast(globalForecastResponse ? globalForecastResponse.start_month : '');
  } else {
    alert('Erro ao atualizar valor do mês.');
  }
}

async function loadRecurringMasterList() {
  const res = await apiCall('/recurring-transactions', 'GET');
  const tbody = document.getElementById('recurringMasterTableBody');
  tbody.innerHTML = '';

  if (res.ok && Array.isArray(res.data)) {
    globalMasterRecurringCache = res.data;
    if (res.data.length === 0) {
      tbody.innerHTML = '<tr><td colspan="7">Nenhuma regra recorrente cadastrada.</td></tr>';
      return;
    }

    res.data.forEach(rec => {
      const tr = document.createElement('tr');
      const isExpense = rec.type === 'EXPENSE';
      const typeLabel = isExpense ? 'Despesa Fixa' : 'Salário / Receita';

      const targetLabel = rec.credit_card_id
        ? `💳 Cartão: ${escapeHtml(rec.credit_card_name || 'Cartão')}`
        : `🏦 Conta: ${getAccountName(rec.account_id)}`;

      tr.innerHTML = `
        <td><strong>${escapeHtml(rec.description)}</strong></td>
        <td>${typeLabel}</td>
        <td>${formatCurrency(rec.amount)}</td>
        <td>Dia ${rec.due_day}</td>
        <td>${targetLabel}</td>
        <td>${formatCategory(rec.category)}</td>
        <td>
          <button onclick="editRecurringMaster('${rec.id}')" class="btn-sm">✏️ Editar Mestre</button>
          <button onclick="deleteRecurringTransaction('${rec.id}')" class="btn-sm btn-danger">Excluir</button>
        </td>
      `;
      tbody.appendChild(tr);
    });
  } else {
    tbody.innerHTML = '<tr><td colspan="7">Erro ao carregar regras recorrentes.</td></tr>';
  }
}

function resetRecurringForm() {
  document.getElementById('recMasterId').value = '';
  document.getElementById('recDescription').value = '';
  document.getElementById('recAmount').value = '';
  document.getElementById('recDueDay').value = '5';
  document.getElementById('recType').value = 'INCOME';
  document.getElementById('recTargetType').value = 'ACCOUNT';
  toggleRecTargetSelects();

  document.getElementById('recFormTitle').textContent = '➕ Cadastrar Regra Recorrente (Conta Bancária ou Assinatura de Cartão)';
  document.getElementById('recSubmitBtn').textContent = 'Cadastrar Recorrente';
  document.getElementById('recCancelBtn').style.display = 'none';
}

function editRecurringMaster(id) {
  const rec = globalMasterRecurringCache.find(r => r.id === id);
  if (!rec) return;

  document.getElementById('recMasterId').value = rec.id;
  document.getElementById('recDescription').value = rec.description;
  document.getElementById('recAmount').value = rec.amount;
  document.getElementById('recDueDay').value = rec.due_day;
  document.getElementById('recType').value = rec.type;
  document.getElementById('recCategory').value = rec.category || 'UNCATEGORIZED';

  if (rec.credit_card_id) {
    document.getElementById('recTargetType').value = 'CARD';
    toggleRecTargetSelects();
    document.getElementById('recCard').value = rec.credit_card_id;
  } else {
    document.getElementById('recTargetType').value = 'ACCOUNT';
    toggleRecTargetSelects();
    document.getElementById('recAccount').value = rec.account_id;
  }

  document.getElementById('recFormTitle').textContent = '✏️ Editar Regra Recorrente MESTRE (Atualiza todos os meses futuros)';
  document.getElementById('recSubmitBtn').textContent = 'Salvar Alterações Mestre';
  document.getElementById('recCancelBtn').style.display = 'inline-block';
}

async function handleRecurringSubmit(e) {
  e.preventDefault();
  const masterId = document.getElementById('recMasterId').value;
  const targetType = document.getElementById('recTargetType').value;

  const body = {
    description: document.getElementById('recDescription').value.trim(),
    amount: parseFloat(document.getElementById('recAmount').value),
    type: document.getElementById('recType').value,
    due_day: parseInt(document.getElementById('recDueDay').value),
    category: document.getElementById('recCategory').value
  };

  if (targetType === 'CARD') {
    const cardId = document.getElementById('recCard').value;
    if (!cardId) {
      alert('Selecione o cartão de crédito!');
      return;
    }
    body.credit_card_id = cardId;
  } else {
    const accId = document.getElementById('recAccount').value;
    if (!accId) {
      alert('Selecione a conta bancária!');
      return;
    }
    body.account_id = accId;
  }

  let res;
  if (masterId) {
    res = await apiCall(`/recurring-transactions/${masterId}`, 'PUT', body);
  } else {
    res = await apiCall('/recurring-transactions', 'POST', body);
  }

  if (res.ok) {
    alert(masterId ? 'Regra Mestre atualizada com sucesso para todos os meses futuros!' : 'Regra recorrente cadastrada com sucesso!');
    resetRecurringForm();
    loadForecast();
    loadRecurringMasterList();
  } else {
    alert('Erro ao salvar regra recorrente.');
  }
}

async function deleteRecurringTransaction(id) {
  if (!confirm('Deseja cancelar esta regra recorrente para todos os meses futuros?')) return;
  const res = await apiCall(`/recurring-transactions/${id}`, 'DELETE');
  if (res.ok) {
    alert('Regra recorrente desativada.');
    loadForecast();
    loadRecurringMasterList();
  } else {
    alert('Erro ao remover regra recorrente.');
  }
}

// --- 🎯 CATEGORY BUDGETS HANDLERS ---
async function loadCategoryBudgets() {
  const res = await apiCall('/category-budgets', 'GET');
  const tbody = document.getElementById('budgetsTableBody');
  tbody.innerHTML = '';

  if (res.ok && Array.isArray(res.data)) {
    if (res.data.length === 0) {
      tbody.innerHTML = '<tr><td colspan="6">Nenhum teto de gastos configurado. Defina no formulário ao lado!</td></tr>';
      return;
    }

    res.data.forEach(bg => {
      const tr = document.createElement('tr');
      const spent = bg.current_month_spent || 0.0;
      const limit = bg.monthly_limit;
      const pct = bg.progress_percentage || 0.0;
      const status = bg.status;

      let barColor = '#28a745'; // Green
      let statusBadge = '<span class="badge logged-in">🟩 OK</span>';

      if (status === 'WARNING') {
        barColor = '#ffc107'; // Yellow
        statusBadge = '<span class="badge" style="background:#fff3cd; color:#856404; border:1px solid #ffeeba;">🟨 ALERTA (80%+)</span>';
      } else if (status === 'EXCEEDED') {
        barColor = '#dc3545'; // Red
        statusBadge = '<span class="badge logged-out">🟥 TETO EXCEDIDO</span>';
      }

      const progressHtml = limit ? `
        <div style="width: 100%; background-color: #e9ecef; border-radius: 4px; overflow: hidden; height: 16px;">
          <div style="width: ${Math.min(pct, 100)}%; background-color: ${barColor}; height: 100%;"></div>
        </div>
        <small>${pct.toFixed(1)}% consumido</small>
      ` : '<small style="color:#666;">Sem teto definido</small>';

      tr.innerHTML = `
        <td><strong>${formatCategory(bg.category)}</strong></td>
        <td><strong style="color: ${spent > (limit || 0) && limit ? '#dc3545' : 'inherit'}">${formatCurrency(spent)}</strong></td>
        <td>${limit ? formatCurrency(limit) : 'N/A'}</td>
        <td style="min-width: 130px;">${progressHtml}</td>
        <td>${statusBadge}</td>
        <td>
          <button onclick="deleteCategoryBudget('${bg.category}')" class="btn-sm btn-danger">Excluir</button>
        </td>
      `;
      tbody.appendChild(tr);
    });
  } else {
    tbody.innerHTML = '<tr><td colspan="6">Erro ao carregar tetos de gastos por categoria.</td></tr>';
  }
}

async function handleCategoryBudgetSubmit(e) {
  e.preventDefault();
  const category = document.getElementById('bgCategory').value;
  const limitVal = document.getElementById('bgLimit').value;

  if (!limitVal) {
    alert('Preencha o Teto de Gastos (R$)!');
    return;
  }

  const body = {
    category: category,
    monthly_limit: parseFloat(limitVal)
  };

  const res = await apiCall('/category-budgets', 'POST', body);
  if (res.ok) {
    alert('Teto de gastos por categoria salvo com sucesso!');
    document.getElementById('bgLimit').value = '';
    loadCategoryBudgets();
  } else {
    alert('Erro ao salvar teto de gastos por categoria.');
  }
}

async function deleteCategoryBudget(category) {
  if (!confirm(`Deseja remover o teto da categoria ${formatCategory(category)}?`)) return;

  const res = await apiCall(`/category-budgets/${category}`, 'DELETE');
  if (res.ok) {
    alert('Regra da categoria removida.');
    loadCategoryBudgets();
  } else {
    alert('Erro ao remover regra da categoria.');
  }
}

// --- UTILITY HELPERS ---
function populateCategorySelects() {
  const catSelects = ['filterCategory', 'txCategory', 'cpCategory', 'recCategory', 'bgCategory'];
  catSelects.forEach(id => {
    const el = document.getElementById(id);
    if (!el) return;
    const currentVal = el.value;
    el.innerHTML = id === 'filterCategory' ? '<option value="">Todas as Categorias</option>' : '';
    Object.keys(CATEGORIES).forEach(catKey => {
      // For budget category limit, skip INVESTMENTS as goals are per POCKET account
      if (id === 'bgCategory' && catKey === 'INVESTMENTS') return;

      const opt = document.createElement('option');
      opt.value = catKey;
      opt.textContent = CATEGORIES[catKey];
      el.appendChild(opt);
    });
    if (currentVal) el.value = currentVal;
  });
}

function formatCategory(catKey) {
  if (!catKey) return 'Sem Categoria';
  return CATEGORIES[catKey] || catKey;
}

function getAccountName(accId) {
  const acc = globalAccountsCache.find(a => a.id === accId);
  return acc ? acc.name : (accId ? accId.substring(0, 8) + '...' : 'N/A');
}

function formatCurrency(amount, currency = 'BRL') {
  if (amount === undefined || amount === null) return 'R$ 0,00';
  return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: currency || 'BRL' }).format(amount);
}

function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/[&<>"']/g, function(m) {
    return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' }[m];
  });
}

// --- INITIALIZATION ---
document.addEventListener('DOMContentLoaded', () => {
  updateAuthUI();
  populateCategorySelects();

  // Auto-format phone input fields on blur/change
  const phoneInputs = ['loginPhone', 'regPhone'];
  phoneInputs.forEach(id => {
    const el = document.getElementById(id);
    if (el) {
      el.addEventListener('blur', () => {
        if (el.value) el.value = formatE164Phone(el.value);
      });
    }
  });

  // Set default current month (YYYY-MM) in month inputs
  const now = new Date();
  const monthStr = now.toISOString().slice(0, 7);
  if (document.getElementById('filterMonth')) document.getElementById('filterMonth').value = monthStr;
  if (document.getElementById('txDate')) {
    const localNow = new Date(now.getTime() - (now.getTimezoneOffset() * 60000)).toISOString().slice(0, 16);
    document.getElementById('txDate').value = localNow;
  }
  if (document.getElementById('trDate')) {
    const localNow = new Date(now.getTime() - (now.getTimezoneOffset() * 60000)).toISOString().slice(0, 16);
    document.getElementById('trDate').value = localNow;
  }
  if (document.getElementById('cpDate')) {
    document.getElementById('cpDate').value = now.toISOString().slice(0, 10);
  }

  // Load initial accounts if token exists
  if (getToken()) {
    loadAccounts();
    loadCreditCards();
  }
});
