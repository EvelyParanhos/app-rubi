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

    def register(self, name, phone_number, pin):
        payload = {
            "name": name,
            "phone_number": phone_number,
            "pin": pin
        }
        return self._request("POST", "/users/register", payload, require_auth=False)

    def login(self, phone_number, pin):
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
        return None

    def ensure_login(self, phone_number, pin, name=None):
        if not phone_number or not pin:
            raise ValueError("Telefone e PIN são obrigatórios para autenticação.")

        try:
            tok = self.login(phone_number, pin)
            if tok:
                return tok
        except Exception as e:
            logger.warning(f"[LOG AUTENTICAÇÃO] Login inicial falhou para {phone_number} ({e}). Tentando registrar nova conta...")

        try:
            reg_res = self.register(name or "Usuário", phone_number, pin)
            if isinstance(reg_res, dict) and "token" in reg_res:
                self.token = reg_res["token"]
                self.phone_number = phone_number
                self.pin = pin
                return self.token
            return self.login(phone_number, pin)
        except Exception:
            try:
                return self.login(phone_number, pin)
            except Exception as final_err:
                logger.error(f"[LOG DIAGNÓSTICO] Falha definitiva no login/registro para {phone_number}: {final_err}")
                raise final_err

    def get(self, endpoint, params=None):
        return self._request("GET", endpoint, params=params)

    def post(self, endpoint, payload=None):
        return self._request("POST", endpoint, payload=payload)

    def _request(self, method, endpoint, payload=None, params=None, require_auth=True, is_retry=False):
        url = f"{self.base_url}{endpoint}"

        if require_auth and not self.token:
            if self.phone_number and self.pin:
                logger.info("[LOG RE-AUTENTICANDO] Token ausente. Efetuando login...")
                self.ensure_login(self.phone_number, self.pin)
            else:
                raise RuntimeError("HTTP_401: Usuário não autenticado. Por favor, informe o celular e PIN.")

        headers = {}
        if require_auth and self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        logger.info(f"[LOG REQUISIÇÃO] {method} {url} | Params: {params} | Payload: {payload}")

        try:
            if method.upper() == "GET":
                response = requests.get(url, params=params, headers=headers, timeout=10)
            else:
                response = requests.post(url, json=payload if payload else {}, headers=headers, timeout=10)

            logger.info(f"[LOG RESPOSTA] {method} {url} ➔ Status: {response.status_code}")

            if response.status_code in (401, 403) and require_auth and not is_retry:
                logger.warning(f"[LOG RENOVAÇÃO TOKEN] Status {response.status_code} recebido. Renovando token...")
                if self.phone_number and self.pin:
                    self.ensure_login(self.phone_number, self.pin)
                    return self._request(method, endpoint, payload=payload, params=params, require_auth=True, is_retry=True)

            if response.status_code in (200, 201):
                try:
                    return response.json()
                except ValueError:
                    return {"success": True}
            else:
                error_detail = response.text
                logger.error(f"[LOG ERRO BACKEND] {method} {url} | Status: {response.status_code} | Detalhes: {error_detail}")
                raise RuntimeError(f"HTTP_{response.status_code}: {error_detail}")
        except requests.exceptions.RequestException as e:
            logger.error(f"[LOG ERRO CONEXÃO] {method} {url} | Exceção: {e}")
            raise RuntimeError(f"Erro de conexão com o servidor Rubi: {e}")

    # Auxiliares de Negócio
    def get_accounts(self):
        try:
            res = self.get("/accounts")
            return res if isinstance(res, list) else []
        except Exception as e:
            logger.error(f"[LOG ERRO] Falha ao buscar contas: {e}")
            return []

    def get_credit_cards(self):
        try:
            res = self.get("/credit-cards")
            return res if isinstance(res, list) else []
        except Exception as e:
            logger.error(f"[LOG ERRO] Falha ao buscar cartões: {e}")
            return []

    def get_active_partnership(self):
        try:
            return self.get("/partnerships/active")
        except Exception as e:
            logger.warning(f"[LOG AVISO] Falha ao verificar parceria ativa: {e}")
            return {"has_active_partnership": False}

    def get_recurring_expenses(self):
        try:
            res = self.get("/recurring-transactions")
            return res if isinstance(res, list) else []
        except Exception as e:
            logger.error(f"[LOG ERRO] Falha ao buscar transações recorrentes: {e}")
            return []

    def create_recurring_expense(self, account_id, description, amount, exp_type, due_day, category="UNCATEGORIZED"):
        payload = {
            "account_id": account_id,
            "description": description,
            "amount": amount,
            "type": exp_type,
            "due_day": due_day,
            "category": category
        }
        return self.post("/recurring-transactions", payload)

    def create_transaction(self, account_id, amount, trans_type, description=None, category="UNCATEGORIZED"):
        payload = {
            "account_id": account_id,
            "amount": amount,
            "type": trans_type,
            "description": description,
            "category": category
        }
        return self.post("/transactions", payload)

    def get_transactions(self, month=None, account_id=None, category=None):
        params = {}
        if month:
            params["month"] = month
        if account_id:
            params["account_id"] = account_id
        if category:
            params["category"] = category
        try:
            res = self.get("/transactions", params=params)
            return res if isinstance(res, list) else []
        except Exception as e:
            logger.error(f"[LOG ERRO] Falha ao buscar extrato: {e}")
            return []

    def pay_settlement(self, month, source_account_id, amount):
        payload = {
            "month": month,
            "source_account_id": source_account_id,
            "amount": amount
        }
        return self.post("/settlements/pay", payload)

