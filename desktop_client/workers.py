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
            
class SalesCheckoutWorker(QThread):
    """
    Submits a completed cart to the backend for checkout. Runs off the UI
    thread since this hits the database, and for card/M-Pesa payments, an
    external gateway too.
    """
    checkout_ready = pyqtSignal(dict)
    checkout_failed = pyqtSignal(str)

    def __init__(self, tenant, token, items, payment_method, phone_number=None):
        super().__init__()
        self.tenant = tenant
        self.token = token
        self.items = items
        self.payment_method = payment_method
        self.phone_number = phone_number

    def run(self):
        url, headers = get_api_routing(self.tenant, "api/v1/sales/checkout/")
        headers["Authorization"] = f"Token {self.token}"

        payload = {"items": self.items, "payment_method": self.payment_method}
        if self.phone_number:
            payload["phone_number"] = self.phone_number

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=20)
            if response.status_code in (200, 201, 202):
                self.checkout_ready.emit(response.json())
            else:
                try:
                    detail = response.json().get("error", "Checkout failed.")
                except ValueError:
                    detail = "Checkout failed."
                self.checkout_failed.emit(detail)
        except requests.exceptions.RequestException as e:
            self.checkout_failed.emit(str(e))

class BarcodeLookupWorker(QThread):
    """
    Resolves a single scanned barcode/SKU against the backend when it's
    not found in the desktop client's locally synced catalog (stale cache
    or a product added since the last sync).
    """
    lookup_finished = pyqtSignal(dict)   # Emitted with the matched product
    lookup_failed = pyqtSignal(str)      # Emitted on 404 or network failure

    def __init__(self, tenant, token, code):
        super().__init__()
        self.tenant = tenant
        self.token = token
        self.code = code

    def run(self):
        url, headers = get_api_routing(self.tenant, "api/v1/inventory/products/lookup/")
        headers["Authorization"] = f"Token {self.token}"

        try:
            response = requests.get(url, headers=headers, params={"code": self.code}, timeout=10)
            if response.status_code == 200:
                self.lookup_finished.emit(response.json())
            elif response.status_code == 404:
                self.lookup_failed.emit("Product not found")
            else:
                self.lookup_failed.emit(f"Server returned status code: {response.status_code}")
        except requests.exceptions.RequestException as e:
            self.lookup_failed.emit(str(e))