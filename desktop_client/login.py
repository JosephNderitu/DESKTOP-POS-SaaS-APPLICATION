import requests
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QVBoxLayout, QWidget
from PyQt6.QtCore import Qt, pyqtSignal


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

        title = QLabel("DUKA YANGU POS")
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

    def show_password_reset_note(self):
        QMessageBox.information(
            self,
            "Password Reset",
            "Password reset will use the email saved on the owner or staff account. The login screen will stay simple: store subdomain, username, and password."
        )