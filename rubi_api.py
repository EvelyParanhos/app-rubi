import os
import logging
import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class RubiApiClient:
    def __init__(self, token=None, phone_number=None, pin=None):
        self.base_url = os.getenv("JAVA_API_URL", "http://localhost:8080/api")
        self.token = token
        self.phone_number = phone_number
        self.pin = pin

    def set_token(self, token: str):
        self.token = token

    def login(self, phone_number: str, pin: str) -> str:
        payload = {
            "phone_number": phone_number,
            "pin": pin
        }
        res = self._request("POST", "/auth/login", payload, require_auth=False)
        if isinstance(res, dict) and "token" in res:
            self.token = res["token"]
            self.phone_number = phone_number
            self.pin = pin
            return self.token
        raise RuntimeError("Resposta de login inválida.")

    def ensure_login(self, phone_number: str, pin: str, name: str = None) -> str:
        if not phone_number or not pin:
            raise ValueError("Telefone e PIN são obrigatórios para autenticação.")

        try:
            tok = self.login(phone_number, pin)
            if tok:
                return tok
        except Exception as e:
            logger.info(f"[RUBI API] Login inicial para {phone_number} não efetuado ({e}). Criando cadastro...")

        reg_res = self.register(name or "Usuário Telegram", phone_number, pin)
        if isinstance(reg_res, dict) and "token" in reg_res:
            self.token = reg_res["token"]
            self.phone_number = phone_number
            self.pin = pin
            return self.token

        return self.login(phone_number, pin)

    def register(self, name: str, phone_number: str, pin: str) -> dict:
        payload = {
            "name": name,
            "phone_number": phone_number,
            "pin": pin
        }
        return self._request("POST", "/users/register", payload, require_auth=False)

    def link_telegram(self, chat_id: str) -> dict:
        payload = {"telegram_chat_id": str(chat_id)}
        return self._request("POST", "/users/telegram-link", payload)

    def get_user_profile(self) -> dict:
        return self._request("GET", "/users/me")

    def complete_onboarding(self) -> dict:
        return self._request("POST", "/users/onboarding/complete")

    def get_accounts(self) -> list:
        res = self._request("GET", "/accounts")
        return res if isinstance(res, list) else []

    def create_account(self, name: str, acc_type: str = "CHECKING", initial_balance: float = 0.0) -> dict:
        payload = {
            "name": name,
            "type": acc_type,
            "initial_balance": initial_balance
        }
        return self._request("POST", "/accounts", payload)

    def get_credit_cards(self) -> list:
        res = self._request("GET", "/credit-cards")
        return res if isinstance(res, list) else []

    def create_credit_card(self, account_id: str, name: str, credit_limit: float, closing_day: int, due_day: int) -> dict:
        payload = {
            "account_id": account_id,
            "name": name,
            "credit_limit": credit_limit,
            "closing_day": closing_day,
            "due_day": due_day
        }
        return self._request("POST", "/credit-cards", payload)

    def get_card_invoices(self, card_id: str) -> list:
        res = self._request("GET", f"/credit-cards/{card_id}/invoices")
        return res if isinstance(res, list) else []

    def get_invoice_by_id(self, invoice_id: str) -> dict:
        return self._request("GET", f"/invoices/{invoice_id}")

    def pay_invoice(self, invoice_id: str, source_account_id: str, amount: float) -> dict:
        payload = {
            "source_account_id": source_account_id,
            "amount": amount
        }
        return self._request("POST", f"/invoices/{invoice_id}/pay", payload)

    def get_monthly_forecast(self, start_month: str = None, months: int = 12) -> dict:
        params = {}
        if start_month:
            params["start_month"] = start_month
        if months:
            params["months"] = months
        return self._request("GET", "/forecast/monthly", params=params)

    def create_transaction(self, account_id: str, amount: float, trans_type: str, description: str = None, category: str = "UNCATEGORIZED", reference_date: str = None) -> dict:
        payload = {
            "account_id": account_id,
            "amount": amount,
            "type": trans_type,
            "description": description or ("Crédito" if trans_type == "CREDIT" else "Débito"),
            "category": category
        }
        if reference_date:
            payload["reference_date"] = reference_date
        return self._request("POST", "/transactions", payload)

    def update_transaction(self, transaction_id: str, account_id: str, amount: float = None, trans_type: str = "DEBIT", description: str = None, category: str = None) -> dict:
        payload = {
            "account_id": account_id,
            "amount": amount,
            "type": trans_type,
            "description": description,
            "category": category
        }
        return self._request("PUT", f"/transactions/{transaction_id}", payload)

    def delete_transaction(self, transaction_id: str) -> dict:
        return self._request("DELETE", f"/transactions/{transaction_id}")

    def get_transactions(self, month: str = None, account_id: str = None, category: str = None) -> list:
        params = {}
        if month:
            params["month"] = month
        if account_id:
            params["account_id"] = account_id
        if category:
            params["category"] = category
        res = self._request("GET", "/transactions", params=params)
        return res if isinstance(res, list) else []

    def get_recurring_transactions(self) -> list:
        res = self._request("GET", "/recurring-transactions")
        return res if isinstance(res, list) else []

    def create_recurring_transaction(self, account_id: str, description: str, amount: float, rec_type: str, due_day: int, category: str = "UNCATEGORIZED") -> dict:
        payload = {
            "account_id": account_id,
            "description": description,
            "amount": amount,
            "type": rec_type,
            "due_day": due_day,
            "category": category
        }
        return self._request("POST", "/recurring-transactions", payload)

    def _request(self, method: str, endpoint: str, payload: dict = None, params: dict = None, require_auth: bool = True) -> dict | list:
        url = f"{self.base_url}{endpoint}"
        headers = {"Content-Type": "application/json"}

        if require_auth:
            if not self.token:
                raise RuntimeError("Sessão expirada ou não autenticada. Utilize /login para entrar.")
            headers["Authorization"] = f"Bearer {self.token}"

        logger.info(f"[API {method}] {url} | Params: {params} | Body: {payload}")

        try:
            m = method.upper()
            if m == "GET":
                response = requests.get(url, params=params, headers=headers, timeout=10)
            elif m == "PUT":
                response = requests.put(url, json=payload if payload else {}, headers=headers, timeout=10)
            elif m == "DELETE":
                response = requests.delete(url, headers=headers, timeout=10)
            else:
                response = requests.post(url, json=payload if payload else {}, headers=headers, timeout=10)

            if response.status_code in (200, 201):
                try:
                    return response.json()
                except ValueError:
                    return {"success": True}
            elif response.status_code == 204:
                return {"success": True}
            else:
                err_text = response.text
                logger.error(f"[API ERRO {response.status_code}] {url} -> {err_text}")
                raise RuntimeError(f"Erro na requisição ({response.status_code}): {err_text}")
        except requests.exceptions.RequestException as e:
            logger.error(f"[API CONEXÃO] Falha ao conectar em {url}: {e}")
            raise RuntimeError("Não foi possível conectar ao servidor Rubi. Verifique se o backend está ativo.")
