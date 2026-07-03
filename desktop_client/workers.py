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
        # Build the dynamic URL and headers using our environment switcher
        url, headers = get_api_routing(self.tenant, "api/v1/inventory/products/")
        headers["Authorization"] = f"Token {self.token}"

        try:
            # Execute the network call on this background worker thread thread
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                products_list = response.json()
                self.fetch_finished.emit(products_list)
            else:
                self.fetch_failed.emit(f"Server returned status code: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            self.fetch_failed.emit(str(e))