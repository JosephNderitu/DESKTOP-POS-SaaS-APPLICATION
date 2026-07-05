import requests
from PyQt6.QtCore import QThread, pyqtSignal
from config import get_api_routing


class InventoryFetchWorker(QThread):
    """
    Asynchronous network thread worker that downloads a store's
    product catalog cleanly in the background.
    """
    fetch_finished = pyqtSignal(list)   # Emitted on request success
    fetch_failed = pyqtSignal(str)     # Emitted if a network failure occurs

    def __init__(self, tenant, token):
        super().__init__()
        self.tenant = tenant
        self.token = token

    def run(self):
        url, headers = get_api_routing(self.tenant, "api/v1/inventory/products/")
        headers["Authorization"] = f"Token {self.token}"

        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                products_list = response.json()
                self.fetch_finished.emit(products_list)
            else:
                self.fetch_failed.emit(f"Server returned status code: {response.status_code}")
        except requests.exceptions.RequestException as e:
            self.fetch_failed.emit(str(e))


class SubscriptionPlanFetchWorker(QThread):
    """Fetches the live, active subscription plans from the public schema."""
    fetch_finished = pyqtSignal(list)
    fetch_failed = pyqtSignal(str)

    def run(self):
        url, headers = get_api_routing("public", "api/v1/billing/plans/")
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                self.fetch_finished.emit(response.json())
            else:
                self.fetch_failed.emit(f"Server returned status code: {response.status_code}")
        except requests.exceptions.RequestException as e:
            self.fetch_failed.emit(str(e))


class SubscriptionCheckoutWorker(QThread):
    """
    Runs immediately after a new store is provisioned: logs in with the
    freshly generated default admin credentials to obtain a token, then
    initiates a gateway checkout for the plan the person picked during
    signup. Both calls happen off the UI thread since the login step can
    be slow the very first time a brand-new tenant schema is queried.
    """
    checkout_ready = pyqtSignal(dict)
    checkout_failed = pyqtSignal(str)

    def __init__(self, tenant, username, password, plan_code, gateway, phone_number=None):
        super().__init__()
        self.tenant = tenant
        self.username = username
        self.password = password
        self.plan_code = plan_code
        self.gateway = gateway
        self.phone_number = phone_number

    def run(self):
        try:
            login_url, login_headers = get_api_routing(self.tenant, "api/v1/login/")
            login_response = requests.post(
                login_url,
                json={"username": self.username, "password": self.password},
                headers=login_headers,
                timeout=10,
            )
            if login_response.status_code != 200:
                self.checkout_failed.emit(
                    "Your store was created, but we couldn't automatically start checkout. "
                    "Log in and subscribe from the dashboard instead."
                )
                return

            token = login_response.json().get("token")

            checkout_url, checkout_headers = get_api_routing(self.tenant, "api/v1/billing/checkout/")
            checkout_headers["Authorization"] = f"Token {token}"

            payload = {"plan_code": self.plan_code, "gateway": self.gateway}
            if self.phone_number:
                payload["phone_number"] = self.phone_number

            checkout_response = requests.post(checkout_url, json=payload, headers=checkout_headers, timeout=20)

            if checkout_response.status_code in (200, 202):
                self.checkout_ready.emit(checkout_response.json())
            else:
                try:
                    detail = checkout_response.json().get("error", "Could not start checkout.")
                except ValueError:
                    detail = "Could not start checkout."
                self.checkout_failed.emit(detail)

        except requests.exceptions.RequestException as e:
            self.checkout_failed.emit(str(e))