/* JavaScript do Protótipo de Baixa Fidelidade - Rubi Finanças (v1.0.8 - Forecast 12 Meses) */

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
  "INVESTMENTS": "📈 Investimentos",
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
  "CHECKING": "Conta Corrente",
  "SAVINGS": "Conta Poupança",
  "LIABILITY": "Passivo / Cartão de Crédito"
};

let globalAccountsCache = [];
let globalCardsCache = [];
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
    if (tabName === 'forecast') { populateAccountSelects(); populateCategorySelects(); loadForecast(); loadRecurringMasterList(); }
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

// --- ACCOUNTS HANDLERS ---
async function loadAccounts() {
  const res = await apiCall('/accounts', 'GET');
  const tbody = document.getElementById('accountsTableBody');
  tbody.innerHTML = '';

  if (res.ok && Array.isArray(res.data)) {
    globalAccountsCache = res.data;
    populateAccountSelects();

    if (res.data.length === 0) {
      tbody.innerHTML = '<tr><td colspan="5">Nenhuma conta cadastrada.</td></tr>';
      return;
    }

    res.data.forEach(acc => {
      const tr = document.createElement('tr');
      const typeLabel = ACCOUNT_TYPE_MAP[acc.type] || acc.type;
      tr.innerHTML = `
        <td><strong>${escapeHtml(acc.name)}</strong></td>
        <td>${typeLabel}</td>
        <td>${formatCurrency(acc.balance, acc.currency)}</td>
        <td>${acc.currency || 'BRL'}</td>
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
  document.getElementById('accCurrency').value = 'BRL';
  document.getElementById('accountFormTitle').textContent = 'Nova Conta';
  document.getElementById('accSubmitBtn').textContent = 'Salvar Conta';
  document.getElementById('accCancelBtn').style.display = 'none';
}

function editAccount(id) {
  const acc = globalAccountsCache.find(a => a.id === id);
  if (!acc) return;
  document.getElementById('accountId').value = acc.id;
  document.getElementById('accName').value = acc.name;
  document.getElementById('accType').value = acc.type;
  document.getElementById('accBalance').value = acc.balance;
  document.getElementById('accCurrency').value = acc.currency || 'BRL';

  document.getElementById('accountFormTitle').textContent = 'Editar Conta';
  document.getElementById('accSubmitBtn').textContent = 'Atualizar Conta';
  document.getElementById('accCancelBtn').style.display = 'inline-block';
}

async function handleAccountSubmit(e) {
  e.preventDefault();
  const id = document.getElementById('accountId').value;
  const body = {
    name: document.getElementById('accName').value.trim(),
    type: document.getElementById('accType').value,
    initial_balance: parseFloat(document.getElementById('accBalance').value)
  };

  let res;
  if (id) {
    res = await apiCall(`/accounts/${id}`, 'PUT', body);
  } else {
    res = await apiCall('/accounts', 'POST', body);
  }

  if (res.ok) {
    alert(id ? 'Conta atualizada com sucesso!' : 'Conta criada com sucesso!');
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
      const isLiability = acc.type === 'LIABILITY';
      const opt = document.createElement('option');
      opt.value = acc.id;
      opt.textContent = `${acc.name} (${typeLabel}) - ${formatCurrency(acc.balance, acc.currency)}${isLiability ? ' [Passivo/Cartão]' : ''}`;
      el.appendChild(opt);
    });

    if (currentVal) el.value = currentVal;
  });
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
    alert('Transferência realizada com sucesso!');
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
  const selectCardInvoice = document.getElementById('selectCardInvoice');
  const cpCard = document.getElementById('cpCard');

  tbody.innerHTML = '';
  selectCardInvoice.innerHTML = '<option value="">-- Selecione o Cartão --</option>';
  cpCard.innerHTML = '<option value="">-- Selecione o Cartão --</option>';

  if (res.ok && Array.isArray(res.data)) {
    globalCardsCache = res.data;
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

      const opt1 = document.createElement('option');
      opt1.value = card.id;
      opt1.textContent = `${card.name} (Fechamento: Dia ${card.closing_day})`;
      selectCardInvoice.appendChild(opt1);

      const opt2 = document.createElement('option');
      opt2.value = card.id;
      opt2.textContent = card.name;
      cpCard.appendChild(opt2);
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
    document.getElementById('forecastTableBody').innerHTML = '<tr><td colspan="7">Erro ao carregar previsão de 12 meses.</td></tr>';
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
    tbody.innerHTML = '<tr><td colspan="7">Nenhuma transação recorrente prevista para este mês. Cadastre novas regras abaixo!</td></tr>';
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

    const overrideNotice = item.is_overridden ? ' <small style="color:#d9534f;">(Valor alterado no mês)</small>' : '';

    let actionButtons = '';
    if (isFulfilled) {
      actionButtons = `<small style="color:#28a745;">Quitado no extrato</small>`;
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
      <td>${formatCategory(item.category)}</td>
      <td>${statusBadge}</td>
      <td>${actionButtons}</td>
    `;
    tbody.appendChild(tr);
  });
}

async function fulfillChecklistItem(recId, month) {
  if (!confirm(`Deseja confirmar o pagamento/recebimento deste item para o mês ${month}? Uma transação real será gravada no extrato.`)) return;

  const res = await apiCall(`/recurring-transactions/${recId}/fulfill`, 'POST', { reference_month: month });
  if (res.ok) {
    alert('Item baixado com sucesso! A transação foi gravada no extrato.');
    loadForecast(globalForecastResponse ? globalForecastResponse.start_month : '');
    loadAccounts(); // Refresh balance
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
    if (res.data.length === 0) {
      tbody.innerHTML = '<tr><td colspan="6">Nenhuma regra recorrente cadastrada.</td></tr>';
      return;
    }

    res.data.forEach(rec => {
      const tr = document.createElement('tr');
      const isExpense = rec.type === 'EXPENSE';
      const typeLabel = isExpense ? 'Despesa Fixa' : 'Salário / Receita';
      tr.innerHTML = `
        <td><strong>${escapeHtml(rec.description)}</strong></td>
        <td>${typeLabel}</td>
        <td>${formatCurrency(rec.amount)}</td>
        <td>Dia ${rec.due_day}</td>
        <td>${formatCategory(rec.category)}</td>
        <td>
          <button onclick="deleteRecurringTransaction('${rec.id}')" class="btn-sm btn-danger">Excluir Regra</button>
        </td>
      `;
      tbody.appendChild(tr);
    });
  } else {
    tbody.innerHTML = '<tr><td colspan="6">Erro ao carregar regras recorrentes.</td></tr>';
  }
}

async function handleRecurringSubmit(e) {
  e.preventDefault();
  const body = {
    account_id: document.getElementById('recAccount').value,
    description: document.getElementById('recDescription').value.trim(),
    amount: parseFloat(document.getElementById('recAmount').value),
    type: document.getElementById('recType').value,
    due_day: parseInt(document.getElementById('recDueDay').value),
    category: document.getElementById('recCategory').value
  };

  const res = await apiCall('/recurring-transactions', 'POST', body);
  if (res.ok) {
    alert('Regra recorrente cadastrada com sucesso!');
    document.getElementById('recDescription').value = '';
    document.getElementById('recAmount').value = '';
    loadForecast();
    loadRecurringMasterList();
  } else {
    alert('Erro ao cadastrar regra recorrente.');
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

// --- UTILITY HELPERS ---
function populateCategorySelects() {
  const catSelects = ['filterCategory', 'txCategory', 'cpCategory', 'recCategory'];
  catSelects.forEach(id => {
    const el = document.getElementById(id);
    if (!el) return;
    el.innerHTML = id === 'filterCategory' ? '<option value="">Todas as Categorias</option>' : '';
    Object.keys(CATEGORIES).forEach(catKey => {
      const opt = document.createElement('option');
      opt.value = catKey;
      opt.textContent = CATEGORIES[catKey];
      el.appendChild(opt);
    });
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
  }
});
