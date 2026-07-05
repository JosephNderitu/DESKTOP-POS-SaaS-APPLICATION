import webbrowser

from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton,
    QScrollArea, QVBoxLayout, QWidget
)
from PyQt6.QtCore import Qt, pyqtSignal
import requests
import qtawesome as qta

from workers import SubscriptionPlanFetchWorker, SubscriptionCheckoutWorker


# ---------------------------------------------------------------------------
# Selectable cards
# ---------------------------------------------------------------------------

class PlanCardWidget(QFrame):
    """A single subscription plan tile. Click to select; parent widget
    manages which one card in the row is highlighted at a time."""
    clicked = pyqtSignal(str)  # emits plan code

    def __init__(self, plan_data, parent=None):
        super().__init__(parent)
        self.plan_data = plan_data
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedWidth(160)
        self.setMinimumHeight(230)
        self._build_ui()
        self.set_selected(False)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(3)

        name_label = QLabel(self.plan_data.get('name', ''))
        name_label.setStyleSheet("font-size: 14px; font-weight: 900; color: #061A40; border: none;")
        layout.addWidget(name_label)

        tagline_label = QLabel(self.plan_data.get('tagline', ''))
        tagline_label.setWordWrap(True)
        tagline_label.setStyleSheet("font-size: 10px; color: #64748B; border: none;")
        layout.addWidget(tagline_label)

        price_kes = float(self.plan_data.get('price_kes', 0) or 0)
        price_usd = float(self.plan_data.get('price_usd', 0) or 0)

        price_label = QLabel(f"KES {price_kes:,.0f}")
        price_label.setStyleSheet("font-size: 19px; font-weight: 900; color: #008C72; border: none; margin-top: 6px;")
        layout.addWidget(price_label)

        usd_label = QLabel(f"or ${price_usd:,.0f} USD")
        usd_label.setStyleSheet("font-size: 10px; color: #94A3B8; border: none;")
        layout.addWidget(usd_label)

        for feature in (self.plan_data.get('features') or [])[:4]:
            feature_label = QLabel(f"\u2713  {feature}")
            feature_label.setWordWrap(True)
            feature_label.setStyleSheet("font-size: 10px; color: #334155; border: none; margin-top: 4px;")
            layout.addWidget(feature_label)

        layout.addStretch()

    def mousePressEvent(self, event):
        self.clicked.emit(self.plan_data.get('code', ''))
        super().mousePressEvent(event)

    def set_selected(self, selected):
        border = "2px solid #008C72" if selected else "1px solid #D6DEE8"
        bg = "#F0FDF9" if selected else "#FFFFFF"
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {bg};
                border: {border};
                border-radius: 8px;
            }}
        """)


class GatewayCardWidget(QFrame):
    """A single payment method tile with an icon — Stripe, PayPal, or M-Pesa."""
    clicked = pyqtSignal(str)  # emits gateway code

    ICONS = {
        "STRIPE": ("fa5b.stripe-s", "#635BFF"),
        "PAYPAL": ("fa5b.paypal", "#0070BA"),
        "MPESA": ("fa5s.mobile-alt", "#00A651"),
    }
    LABELS = {
        "STRIPE": "Card (Stripe)",
        "PAYPAL": "PayPal",
        "MPESA": "M-Pesa",
    }

    def __init__(self, gateway_code, parent=None):
        super().__init__(parent)
        self.gateway_code = gateway_code
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedWidth(105)
        self.setFixedHeight(76)
        self._build_ui()
        self.set_selected(False)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 10, 8, 10)
        layout.setSpacing(5)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon_name, color = self.ICONS.get(self.gateway_code, ("fa5s.credit-card", "#334155"))
        icon_label = QLabel()
        icon_label.setPixmap(qta.icon(icon_name, color=color).pixmap(24, 24))
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet("border: none;")
        layout.addWidget(icon_label)

        text_label = QLabel(self.LABELS.get(self.gateway_code, self.gateway_code))
        text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        text_label.setStyleSheet("font-size: 10px; font-weight: 800; color: #07111F; border: none;")
        layout.addWidget(text_label)

    def mousePressEvent(self, event):
        self.clicked.emit(self.gateway_code)
        super().mousePressEvent(event)

    def set_selected(self, selected):
        border = "2px solid #008C72" if selected else "1px solid #D6DEE8"
        bg = "#F0FDF9" if selected else "#FFFFFF"
        self.setStyleSheet(f"QFrame {{ background-color: {bg}; border: {border}; border-radius: 8px; }}")


# ---------------------------------------------------------------------------
# Signup page
# ---------------------------------------------------------------------------

class SignupWidget(QWidget):
    back_to_login = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.all_plans = []
        self.selected_billing_cycle = "MONTHLY"
        self.selected_plan_code = None
        self.selected_gateway = None
        self.plan_cards = []
        self.gateway_cards = []
        self.init_ui()
        self.load_plans()

    # -- layout ------------------------------------------------------------

    def init_ui(self):
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background-color: #F6F9FC; }")

        page_layout = QVBoxLayout()
        page_layout.setContentsMargins(34, 34, 34, 34)
        page_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        card = QFrame()
        card.setObjectName("authCard")
        card.setFixedWidth(460)
        card.setStyleSheet("""
            QFrame#authCard {
                background-color: #FFFFFF;
                border: 2px solid #061A40;
                border-radius: 6px;
            }
        """)

        layout = QVBoxLayout(card)
        layout.setSpacing(14)
        layout.setContentsMargins(0, 0, 0, 26)

        layout.addWidget(self._build_brand_bar())

        form_layout = QVBoxLayout()
        form_layout.setSpacing(12)
        form_layout.setContentsMargins(36, 16, 36, 0)

        title = QLabel("Create Store Account")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 20px; font-weight: 800; color: #061A40; border: none;")
        form_layout.addWidget(title)

        subtitle = QLabel("Set up an isolated store workspace")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("font-size: 12px; color: #334155; border: none;")
        form_layout.addWidget(subtitle)

        self.business_name = QLineEdit()
        self.business_name.setPlaceholderText("Business name")
        form_layout.addWidget(self.business_name)

        self.subdomain = QLineEdit()
        self.subdomain.setPlaceholderText("Store subdomain (e.g., gikuru-demo)")
        form_layout.addWidget(self.subdomain)

        self.admin_email = QLineEdit()
        self.admin_email.setPlaceholderText("Owner email for password resets")
        form_layout.addWidget(self.admin_email)

        form_layout.addWidget(self._build_section_label("Choose a plan"))
        form_layout.addWidget(self._build_cycle_toggle())

        self.plans_status_label = QLabel("Loading plans...")
        self.plans_status_label.setStyleSheet("font-size: 12px; color: #94A3B8; border: none;")
        self.plans_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        form_layout.addWidget(self.plans_status_label)

        self.plans_scroll = QScrollArea()
        self.plans_scroll.setWidgetResizable(True)
        self.plans_scroll.setFixedHeight(250)
        self.plans_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.plans_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.plans_scroll.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")
        self.plans_container = QWidget()
        self.plans_container.setStyleSheet("background-color: transparent;")
        self.plans_row_layout = QHBoxLayout(self.plans_container)
        self.plans_row_layout.setSpacing(10)
        self.plans_row_layout.setContentsMargins(2, 2, 2, 2)
        self.plans_scroll.setWidget(self.plans_container)
        form_layout.addWidget(self.plans_scroll)

        form_layout.addWidget(self._build_section_label("Choose a payment method"))

        gateways_row = QHBoxLayout()
        gateways_row.setSpacing(10)
        gateways_row.setContentsMargins(0, 0, 0, 0)
        for gateway_code in ("STRIPE", "PAYPAL", "MPESA"):
            gateway_card = GatewayCardWidget(gateway_code)
            gateway_card.clicked.connect(self.on_gateway_selected)
            self.gateway_cards.append(gateway_card)
            gateways_row.addWidget(gateway_card)
        gateways_row.addStretch()
        form_layout.addLayout(gateways_row)

        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("M-Pesa phone number (e.g., 2547XXXXXXXX)")
        self.phone_input.setVisible(False)
        form_layout.addWidget(self.phone_input)

        self.signup_btn = QPushButton("Create Store & Subscribe")
        self.signup_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.signup_btn.setStyleSheet("""
            QPushButton {
                background-color: #008C72;
                color: #FFFFFF;
                border: 1px solid #007763;
                margin-top: 6px;
                padding: 12px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover { background-color: #006F5B; }
            QPushButton:disabled { background-color: #94A3B8; border-color: #94A3B8; }
        """)
        self.signup_btn.clicked.connect(self.process_signup)
        form_layout.addWidget(self.signup_btn)

        self.back_btn = QPushButton("Return to login")
        self.back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.back_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #334155;
                font-size: 13px;
                padding: 4px;
                border: none;
            }
            QPushButton:hover { color: #061A40; text-decoration: underline; }
        """)
        self.back_btn.clicked.connect(self.back_to_login.emit)
        form_layout.addWidget(self.back_btn)

        layout.addLayout(form_layout)
        page_layout.addWidget(card)
        scroll.setWidget(self._wrap(page_layout))
        outer_layout.addWidget(scroll)

    @staticmethod
    def _wrap(inner_layout):
        wrapper = QWidget()
        wrapper.setLayout(inner_layout)
        wrapper.setStyleSheet("background-color: #F6F9FC;")
        return wrapper

    def _build_brand_bar(self):
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

        brand = QLabel("RVC POS")
        brand.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand.setStyleSheet("font-size: 29px; font-weight: 900; color: #FFFFFF; border: none;")
        brand_layout.addWidget(brand)

        brand_subtitle = QLabel("point of sale made simple")
        brand_subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand_subtitle.setStyleSheet("font-size: 11px; color: #7DD3FC; border: none;")
        brand_layout.addWidget(brand_subtitle)
        return brand_bar

    @staticmethod
    def _build_section_label(text):
        label = QLabel(text)
        label.setStyleSheet("font-size: 13px; color: #07111F; font-weight: 700; margin-top: 6px; border: none;")
        return label

    def _build_cycle_toggle(self):
        row = QHBoxLayout()
        row.setSpacing(0)
        self.monthly_btn = QPushButton("Monthly")
        self.yearly_btn = QPushButton("Yearly — 2 months free")
        for btn in (self.monthly_btn, self.yearly_btn):
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.monthly_btn.clicked.connect(lambda: self.set_billing_cycle("MONTHLY"))
        self.yearly_btn.clicked.connect(lambda: self.set_billing_cycle("YEARLY"))
        row.addWidget(self.monthly_btn)
        row.addWidget(self.yearly_btn)
        self._style_cycle_toggle()
        wrapper = QWidget()
        wrapper.setLayout(row)
        return wrapper

    def _style_cycle_toggle(self):
        active_style = """
            QPushButton {
                background-color: #DFF7F1; color: #061A40; border: 1px solid #A7E8DB;
                font-size: 12px; padding: 8px; font-weight: 800;
            }
        """
        inactive_style = """
            QPushButton {
                background-color: #FFFFFF; color: #07111F; border: 1px solid #D6DEE8;
                font-size: 12px; padding: 8px;
            }
            QPushButton:hover { background-color: #E0F2FE; }
        """
        self.monthly_btn.setStyleSheet(active_style if self.selected_billing_cycle == "MONTHLY" else inactive_style)
        self.yearly_btn.setStyleSheet(active_style if self.selected_billing_cycle == "YEARLY" else inactive_style)

    # -- plan loading and rendering ------------------------------------------

    def load_plans(self):
        self.plan_worker = SubscriptionPlanFetchWorker()
        self.plan_worker.fetch_finished.connect(self.on_plans_loaded)
        self.plan_worker.fetch_failed.connect(self.on_plans_failed)
        self.plan_worker.start()

    def on_plans_loaded(self, plans):
        self.all_plans = plans
        self.plans_status_label.setVisible(False)
        self.render_plan_cards()

    def on_plans_failed(self, error_message):
        self.plans_status_label.setText(f"Could not load plans: {error_message}")

    def set_billing_cycle(self, cycle):
        self.selected_billing_cycle = cycle
        self.selected_plan_code = None
        self._style_cycle_toggle()
        self.render_plan_cards()

    def render_plan_cards(self):
        while self.plans_row_layout.count():
            item = self.plans_row_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
        self.plan_cards = []

        matching_plans = [p for p in self.all_plans if p.get('billing_cycle') == self.selected_billing_cycle]
        if not matching_plans:
            self.plans_status_label.setText("No plans available for this billing cycle right now.")
            self.plans_status_label.setVisible(True)
            return

        for plan_data in matching_plans:
            plan_card = PlanCardWidget(plan_data)
            plan_card.clicked.connect(self.on_plan_selected)
            self.plan_cards.append(plan_card)
            self.plans_row_layout.addWidget(plan_card)
        self.plans_row_layout.addStretch()

    def on_plan_selected(self, plan_code):
        self.selected_plan_code = plan_code
        for card in self.plan_cards:
            card.set_selected(card.plan_data.get('code') == plan_code)

    def on_gateway_selected(self, gateway_code):
        self.selected_gateway = gateway_code
        for card in self.gateway_cards:
            card.set_selected(card.gateway_code == gateway_code)
        self.phone_input.setVisible(gateway_code == "MPESA")

    # -- submission ----------------------------------------------------------

    def process_signup(self):
        business = self.business_name.text().strip()
        sub = self.subdomain.text().strip()
        email = self.admin_email.text().strip()

        if not business or not sub or not email:
            QMessageBox.warning(self, "Input Error", "Enter the business name, store subdomain, and owner email.")
            return
        if not self.selected_plan_code:
            QMessageBox.warning(self, "Input Error", "Choose a subscription plan to continue.")
            return
        if not self.selected_gateway:
            QMessageBox.warning(self, "Input Error", "Choose a payment method to continue.")
            return
        if self.selected_gateway == "MPESA" and not self.phone_input.text().strip():
            QMessageBox.warning(self, "Input Error", "Enter the phone number to receive the M-Pesa payment prompt on.")
            return

        api_url = "http://127.0.0.1:8000/api/v1/register/"
        payload = {"business_name": business, "subdomain": sub, "email": email}
        headers = {"Host": "localhost:8000", "Content-Type": "application/json"}

        self.signup_btn.setText("Creating store...")
        self.signup_btn.setEnabled(False)

        try:
            response = requests.post(api_url, json=payload, timeout=20, headers=headers)

            if "application/json" in response.headers.get("Content-Type", ""):
                response_data = response.json()

                if response.status_code == 201:
                    creds = response_data.get('generated_credentials', {})
                    self._start_checkout(sub, creds.get('username'), creds.get('password'))
                else:
                    error_msg = response_data.get('error', 'Registration process rejected.')
                    QMessageBox.critical(self, "Provisioning Refused", error_msg)
                    self._reset_submit_button()
            else:
                QMessageBox.critical(
                    self, "Unexpected Response",
                    f"The server returned an unreadable response (HTTP {response.status_code})."
                )
                self._reset_submit_button()

        except requests.exceptions.RequestException as e:
            QMessageBox.critical(self, "Network Error", f"Failed to contact registration server: {e}")
            self._reset_submit_button()

    def _start_checkout(self, subdomain, username, password):
        self.signup_btn.setText("Starting checkout...")

        phone_number = self.phone_input.text().strip() if self.selected_gateway == "MPESA" else None

        self._pending_creds = (username, password)
        self.checkout_worker = SubscriptionCheckoutWorker(
            tenant=subdomain, username=username, password=password,
            plan_code=self.selected_plan_code, gateway=self.selected_gateway,
            phone_number=phone_number,
        )
        self.checkout_worker.checkout_ready.connect(self.on_checkout_ready)
        self.checkout_worker.checkout_failed.connect(self.on_checkout_failed)
        self.checkout_worker.start()

    def on_checkout_ready(self, result):
        username, password = self._pending_creds
        checkout_url = result.get('checkout_url')

        if checkout_url:
            webbrowser.open(checkout_url)
            body = (
                f"Store Subdomain ID: {self.subdomain.text().strip()}\n\n"
                f"Default Admin Username: {username}\n"
                f"Default Admin Password: {password}\n\n"
                "Save these credentials safely.\n\n"
                "A browser window has opened to complete your payment. "
                "Once payment is done, come back and log in with the credentials above."
            )
        else:
            # M-Pesa has no checkout_url — it's an STK push to the phone instead
            body = (
                f"Store Subdomain ID: {self.subdomain.text().strip()}\n\n"
                f"Default Admin Username: {username}\n"
                f"Default Admin Password: {password}\n\n"
                f"{result.get('message', 'Check your phone to complete the M-Pesa payment.')}"
            )

        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Store Created")
        success_icon = qta.icon('fa5s.check-circle', color='#008C72')
        msg_box.setIconPixmap(success_icon.pixmap(48, 48))
        msg_box.setText("Your store workspace has been created.")
        msg_box.setInformativeText(body)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg_box.exec()

        self._clear_form()
        self.back_to_login.emit()

    def on_checkout_failed(self, error_message):
        username, password = self._pending_creds
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Store Created — Subscription Pending")
        msg_box.setIcon(QMessageBox.Icon.Warning)
        msg_box.setText("Your store was created, but we couldn't start checkout automatically.")
        msg_box.setInformativeText(
            f"Default Admin Username: {username}\nDefault Admin Password: {password}\n\n{error_message}"
        )
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg_box.exec()

        self._clear_form()
        self.back_to_login.emit()

    def _clear_form(self):
        self.business_name.clear()
        self.subdomain.clear()
        self.admin_email.clear()
        self.phone_input.clear()
        self._reset_submit_button()

    def _reset_submit_button(self):
        self.signup_btn.setText("Create Store & Subscribe")
        self.signup_btn.setEnabled(True)