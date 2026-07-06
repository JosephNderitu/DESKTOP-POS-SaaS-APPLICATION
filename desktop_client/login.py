import webbrowser

import requests
from PyQt6.QtWidgets import (
    QDialog, QFrame, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QVBoxLayout, QWidget
)
from PyQt6.QtCore import Qt, pyqtSignal
import qtawesome as qta

from signup import GatewayCardWidget
from config import get_api_routing


class LoginWidget(QWidget):
    login_successful = pyqtSignal(dict)
    signup_requested = pyqtSignal()  # Route link trigger

    ACTIVE_TAB_STYLE = """
        QPushButton {
            background-color: #DFF7F1;
            color: #061A40;
            border: 1px solid #A7E8DB;
            border-radius: 3px;
            font-size: 12px;
            padding: 10px 8px;
            font-weight: 700;
        }
    """
    INACTIVE_TAB_STYLE = """
        QPushButton {
            background-color: #FFFFFF;
            color: #07111F;
            border: 1px solid #D6DEE8;
            border-radius: 3px;
            font-size: 12px;
            padding: 10px 8px;
        }
        QPushButton:hover { background-color: #E0F2FE; border-color: #7DD3FC; }
    """

    def __init__(self):
        super().__init__()
        self.active_tab = "owner"
        self.init_ui()

    def init_ui(self):
        page_layout = QVBoxLayout()
        page_layout.setContentsMargins(34, 34, 34, 34)
        page_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        card = QFrame()
        card.setObjectName("authCard")
        card.setFixedWidth(360)
        card.setStyleSheet("""
            QFrame#authCard {
                background-color: #FFFFFF;
                border: 2px solid #061A40;
                border-radius: 6px;
            }
        """)

        layout = QVBoxLayout(card)
        layout.setSpacing(14)
        layout.setContentsMargins(0, 0, 0, 24)

        brand_bar = QFrame()
        brand_bar.setObjectName("brandBar")
        brand_bar.setStyleSheet("""
            QFrame#brandBar {
                background-color: #061A40;
                border: none;
                border-bottom: 4px solid #008C72;
            }
        """)
        brand_layout = QVBoxLayout(brand_bar)
        brand_layout.setContentsMargins(22, 18, 22, 15)
        brand_layout.setSpacing(0)

        title = QLabel("RVC POS")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 29px; font-weight: 900; color: #FFFFFF; border: none;")
        brand_layout.addWidget(title)

        subtitle = QLabel("point of sale made simple")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("font-size: 11px; color: #7DD3FC; border: none;")
        brand_layout.addWidget(subtitle)
        layout.addWidget(brand_bar)

        form_layout = QVBoxLayout()
        form_layout.setSpacing(13)
        form_layout.setContentsMargins(46, 18, 46, 0)

        tabs = QHBoxLayout()
        tabs.setSpacing(0)
        self.owner_tab = QPushButton("Owner Login")
        self.employee_tab = QPushButton("Employee Login")
        for tab_btn in (self.owner_tab, self.employee_tab):
            tab_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.owner_tab.clicked.connect(lambda: self._set_active_tab("owner"))
        self.employee_tab.clicked.connect(lambda: self._set_active_tab("employee"))
        tabs.addWidget(self.owner_tab)
        tabs.addWidget(self.employee_tab)
        form_layout.addLayout(tabs)
        self._apply_tab_styles()

        self.tenant_input = QLineEdit()
        self.tenant_input.setPlaceholderText("Store subdomain")
        self.tenant_input.setToolTip("Example: gikuru-demo")
        form_layout.addWidget(self.tenant_input)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Username")
        form_layout.addWidget(self.username_input)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        form_layout.addWidget(self.password_input)

        self.login_btn = QPushButton("Login")
        self.login_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.login_btn.setStyleSheet("""
            QPushButton {
                background-color: #008C72;
                color: #FFFFFF;
                border: 1px solid #007763;
                padding: 12px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover { background-color: #006F5B; }
            QPushButton:disabled { background-color: #94A3B8; border-color: #94A3B8; }
        """)
        self.login_btn.clicked.connect(self.handle_login)
        form_layout.addWidget(self.login_btn)

        self.forgot_password_btn = QPushButton("Forgot password? Reset with email")
        self.forgot_password_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.forgot_password_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #006F5B;
                font-size: 12px;
                font-weight: 600;
                padding: 4px;
                border: none;
            }
            QPushButton:hover { color: #0284C7; text-decoration: underline; }
        """)
        self.forgot_password_btn.clicked.connect(self.show_password_reset_note)
        form_layout.addWidget(self.forgot_password_btn)

        self.go_signup_btn = QPushButton("Create a new store")
        self.go_signup_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.go_signup_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #334155;
                font-size: 13px;
                padding: 4px;
                border: none;
            }
            QPushButton:hover { color: #061A40; text-decoration: underline; }
        """)
        self.go_signup_btn.clicked.connect(self.signup_requested.emit)
        form_layout.addWidget(self.go_signup_btn)

        layout.addLayout(form_layout)

        page_layout.addWidget(card)
        self.setLayout(page_layout)

    def _set_active_tab(self, tab_name):
        # Visual grouping only for now — both tabs authenticate the same way.
        # Once role-scoped login screens exist, branch the request here.
        self.active_tab = tab_name
        self._apply_tab_styles()

    def _apply_tab_styles(self):
        self.owner_tab.setStyleSheet(self.ACTIVE_TAB_STYLE if self.active_tab == "owner" else self.INACTIVE_TAB_STYLE)
        self.employee_tab.setStyleSheet(self.ACTIVE_TAB_STYLE if self.active_tab == "employee" else self.INACTIVE_TAB_STYLE)

    def handle_login(self):
        tenant = self.tenant_input.text().strip()
        username = self.username_input.text().strip()
        password = self.password_input.text()

        if not tenant or not username or not password:
            QMessageBox.warning(self, "Input Error", "Enter your store subdomain, username, and password.")
            return

        api_url = "http://127.0.0.1:8000/api/v1/login/"
        headers = {"Host": f"{tenant}.localhost:8000", "Content-Type": "application/json"}

        self.login_btn.setText("Signing in...")
        self.login_btn.setEnabled(False)

        try:
            response = requests.post(api_url, json={"username": username, "password": password}, headers=headers, timeout=8)
            if response.status_code == 200:
                data = response.json()
                data['tenant'] = tenant

                if data.get('subscription_status') == 'PENDING_PAYMENT':
                    # This account exists and the password is correct, but the
                    # tenant is locked server-side until a real payment
                    # succeeds — every endpoint except login/checkout is
                    # blocked regardless of what's in this response. Offer to
                    # resume payment instead of pretending this is a normal
                    # successful login.
                    self.show_resume_payment_dialog(tenant, data.get('token'), data.get('subscription_plan'))
                else:
                    self.login_successful.emit(data)
            elif response.status_code == 402:
                self.show_subscription_blocked(response)
            else:
                QMessageBox.critical(self, "Access Denied", "Invalid store subdomain, username, or password.")
        except requests.exceptions.RequestException:
            QMessageBox.critical(self, "Network Failure", "Unable to reach cloud network.")
        finally:
            self.login_btn.setText("Login")
            self.login_btn.setEnabled(True)

    def show_subscription_blocked(self, response):
        """Shows the specific reason a store's access is blocked — suspended, terminated, or trial ended."""
        try:
            payload = response.json()
        except ValueError:
            payload = {}

        status = payload.get('subscription_status', '')
        detail = payload.get('detail', "This store's access is currently unavailable.")

        title = {
            'TERMINATED': "Subscription Terminated",
            'SUSPENDED': "Account Suspended",
        }.get(status, "Access Unavailable")

        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Icon.Warning)
        msg_box.setWindowTitle(title)
        msg_box.setText(detail)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg_box.exec()

    def show_resume_payment_dialog(self, tenant, token, plan_code):
        dialog = ResumePaymentDialog(tenant, token, plan_code, self)
        dialog.exec()

    def show_password_reset_note(self):
        QMessageBox.information(
            self,
            "Password Reset",
            "Password reset will use the email saved on the owner or staff account. The login screen will stay simple: store subdomain, username, and password."
        )


class ResumePaymentDialog(QDialog):
    """
    Shown when a store logs in successfully but its tenant is still
    PENDING_PAYMENT — meaning signup happened but no payment ever completed
    (abandoned checkout, failed gateway call, etc.). Lets the person pick a
    gateway again and retry, without ever landing in a functioning dashboard
    while unpaid — every other endpoint stays blocked server-side regardless
    of what happens in this dialog.
    """

    def __init__(self, tenant, token, plan_code, parent=None):
        super().__init__(parent)
        self.tenant = tenant
        self.token = token
        self.plan_code = plan_code
        self.selected_gateway = None
        self.gateway_cards = []

        self.setWindowTitle("Complete Your Payment")
        self.setFixedWidth(360)
        self.setStyleSheet("QDialog { background-color: #FFFFFF; }")
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        icon_label = QLabel()
        icon_label.setPixmap(qta.icon('fa5s.lock', color='#F59E0B').pixmap(36, 36))
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)

        title = QLabel("Your store is locked")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 16px; font-weight: 900; color: #061A40;")
        layout.addWidget(title)

        message = QLabel(
            f"Payment for the {self.plan_code or 'selected'} plan was never completed. "
            "Choose a payment method to try again."
        )
        message.setWordWrap(True)
        message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        message.setStyleSheet("font-size: 12px; color: #64748B;")
        layout.addWidget(message)

        gateways_row = QHBoxLayout()
        gateways_row.setSpacing(10)
        for gateway_code in ("STRIPE", "PAYPAL", "MPESA"):
            gateway_card = GatewayCardWidget(gateway_code)
            gateway_card.clicked.connect(self.on_gateway_selected)
            self.gateway_cards.append(gateway_card)
            gateways_row.addWidget(gateway_card)
        layout.addLayout(gateways_row)

        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("M-Pesa phone number (e.g., 2547XXXXXXXX)")
        self.phone_input.setVisible(False)
        layout.addWidget(self.phone_input)

        self.pay_btn = QPushButton("Retry Payment")
        self.pay_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pay_btn.setStyleSheet("""
            QPushButton {
                background-color: #008C72; color: white; padding: 11px;
                font-weight: 900; font-size: 13px; border-radius: 6px; border: none;
            }
            QPushButton:hover { background-color: #006F5B; }
            QPushButton:disabled { background-color: #94A3B8; }
        """)
        self.pay_btn.clicked.connect(self.retry_payment)
        layout.addWidget(self.pay_btn)

        close_btn = QPushButton("Cancel")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton { background-color: transparent; color: #334155; font-size: 12px; border: none; padding: 4px; }
            QPushButton:hover { color: #061A40; text-decoration: underline; }
        """)
        close_btn.clicked.connect(self.reject)
        layout.addWidget(close_btn)

    def on_gateway_selected(self, gateway_code):
        self.selected_gateway = gateway_code
        for card in self.gateway_cards:
            card.set_selected(card.gateway_code == gateway_code)
        self.phone_input.setVisible(gateway_code == "MPESA")

    def retry_payment(self):
        if not self.selected_gateway:
            QMessageBox.warning(self, "Choose a Method", "Select a payment method to continue.")
            return
        if self.selected_gateway == "MPESA" and not self.phone_input.text().strip():
            QMessageBox.warning(self, "Phone Required", "Enter the phone number to receive the M-Pesa payment prompt on.")
            return

        self.pay_btn.setText("Starting checkout...")
        self.pay_btn.setEnabled(False)

        try:
            url, headers = get_api_routing(self.tenant, "api/v1/billing/checkout/")
            headers["Authorization"] = f"Token {self.token}"
            payload = {"plan_code": self.plan_code, "gateway": self.selected_gateway}
            if self.selected_gateway == "MPESA":
                payload["phone_number"] = self.phone_input.text().strip()

            response = requests.post(url, json=payload, headers=headers, timeout=20)
            if response.status_code in (200, 202):
                result = response.json()
                checkout_url = result.get('checkout_url')
                if checkout_url:
                    webbrowser.open(checkout_url)
                    QMessageBox.information(
                        self, "Checkout Opened",
                        "A browser window has opened to complete your payment. Log in again once payment succeeds."
                    )
                else:
                    QMessageBox.information(
                        self, "Check Your Phone",
                        result.get('message', 'Check your phone to complete the M-Pesa payment.')
                    )
                self.accept()
            else:
                try:
                    error_msg = response.json().get('error', 'Could not start checkout.')
                except ValueError:
                    error_msg = 'Could not start checkout.'
                QMessageBox.critical(self, "Checkout Failed", error_msg)
        except requests.exceptions.RequestException as e:
            QMessageBox.critical(self, "Network Error", f"Failed to contact server: {e}")
        finally:
            self.pay_btn.setText("Retry Payment")
            self.pay_btn.setEnabled(True)