from PyQt6.QtWidgets import QComboBox, QFrame, QLabel, QLineEdit, QMessageBox, QPushButton, QVBoxLayout, QWidget
from PyQt6.QtCore import Qt, pyqtSignal
import requests
import qtawesome as qta

class SignupWidget(QWidget):
    back_to_login = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        page_layout = QVBoxLayout()
        page_layout.setContentsMargins(34, 34, 34, 34)
        page_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        card = QFrame()
        card.setObjectName("authCard")
        card.setFixedWidth(390)
        card.setStyleSheet("""
            QFrame#authCard {
                background-color: #FFFFFF;
                border: 2px solid #061A40;
                border-radius: 2px;
            }
        """)

        layout = QVBoxLayout(card)
        layout.setSpacing(13)
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

        brand = QLabel("Gikuru POS")
        brand.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand.setStyleSheet("font-size: 29px; font-weight: 900; color: #FFFFFF;")
        brand_layout.addWidget(brand)

        brand_subtitle = QLabel("point of sale made simple")
        brand_subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand_subtitle.setStyleSheet("font-size: 11px; color: #7DD3FC;")
        brand_layout.addWidget(brand_subtitle)
        layout.addWidget(brand_bar)

        form_layout = QVBoxLayout()
        form_layout.setSpacing(12)
        form_layout.setContentsMargins(42, 16, 42, 0)

        title = QLabel("Create Store Account")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 20px; font-weight: 800; color: #061A40;")
        form_layout.addWidget(title)

        subtitle = QLabel("Set up an isolated store workspace")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("font-size: 12px; color: #334155;")
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

        plan_label = QLabel("Subscription plan")
        plan_label.setStyleSheet("font-size: 13px; color: #07111F; font-weight: 700; margin-top: 4px;")
        form_layout.addWidget(plan_label)
        
        self.plan_box = QComboBox()
        self.plan_box.addItems([
            "Starter - $29/mo (1 terminal)",
            "Growth - $79/mo (multi-branch + M-Pesa ready)",
            "Scale - $199/mo (priority support + full gateways)"
        ])
        form_layout.addWidget(self.plan_box)

        self.signup_btn = QPushButton("Create Store")
        self.signup_btn.setStyleSheet("""
            QPushButton {
                background-color: #008C72;
                color: #FFFFFF;
                border: 1px solid #007763;
                margin-top: 6px;
            }
            QPushButton:hover { background-color: #006F5B; }
        """)
        self.signup_btn.clicked.connect(self.process_payment_and_signup)
        form_layout.addWidget(self.signup_btn)

        self.back_btn = QPushButton("Return to login")
        self.back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.back_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #334155;
                font-size: 13px;
                padding: 4px;
            }
            QPushButton:hover { color: #061A40; text-decoration: underline; }
        """)
        self.back_btn.clicked.connect(self.back_to_login.emit)
        form_layout.addWidget(self.back_btn)

        layout.addLayout(form_layout)
        page_layout.addWidget(card)
        self.setLayout(page_layout)

    def process_payment_and_signup(self):
        business = self.business_name.text().strip()
        sub = self.subdomain.text().strip()
        email = self.admin_email.text().strip()
        plan = self.plan_box.currentText()

        if not business or not sub or not email:
            QMessageBox.warning(self, "Input Error", "Enter the business name, store subdomain, and owner email.")
            return

        # Target the global public endpoint
        api_url = "http://127.0.0.1:8000/api/v1/register/"
        payload = {
            "business_name": business,
            "subdomain": sub,
            "email": email,
            "plan": plan
        }

        # Add explicit headers to route this directly into Django's Public Schema
        headers = {
            "Host": "localhost:8000",
            "Content-Type": "application/json"
        }
        
        # Change button text to show activity/loading state
        self.signup_btn.setText("Creating store...")
        self.signup_btn.setEnabled(False)

        # desktop_client/signup.py -> inside process_payment_and_signup()

        try:
            # Extended timeout since standard migrations take time to format tables
            response = requests.post(api_url, json=payload, timeout=20, headers=headers)
            
            # Check if the backend responded with JSON data before parsing
            if "application/json" in response.headers.get("Content-Type", ""):
                response_data = response.json()
                
                # desktop_client/signup.py -> Update this section inside process_payment_and_signup()

                if response.status_code == 201:
                    creds = response_data.get('generated_credentials', {})
                    username = creds.get('username', 'N/A')
                    password = creds.get('password', 'N/A')

                    # Create a customized modal dialog
                    msg_box = QMessageBox(self)
                    msg_box.setWindowTitle("Subscription Success")
                    
                    # Generate a crisp, green FontAwesome checkmark icon
                    success_icon = qta.icon('fa5s.check-circle', color='#008C72')
                    msg_box.setWindowIcon(success_icon)
                    msg_box.setIconPixmap(success_icon.pixmap(48, 48)) # 48x48px crisp icon

                    msg_box.setText("Your store workspace has been created.")
                    msg_box.setInformativeText(
                        f"Store Subdomain ID: {sub}\n\n"
                        f"Default Admin Username: {username}\n"
                        f"Default Admin Password: {password}\n\n"
                        f"Save these credentials safely. Use store subdomain + username + password to log in. Email is only for password recovery."
                    )
                    msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
                    msg_box.exec()

                    # Clear form parameters and return home
                    self.business_name.clear()
                    self.subdomain.clear()
                    self.admin_email.clear()
                    self.back_to_login.emit()
                else:
                    error_msg = response_data.get('error', 'Registration process rejected.')
                    QMessageBox.critical(self, "Provisioning Refused", error_msg)
            else:
                # If the response isn't JSON, output the raw error code status text
                print(f"Raw Server Debug Code:\n{response.text}")
                QMessageBox.critical(
                    self, 
                    "Unexpected Response", 
                    f"The cloud system returned an unreadable layout response (HTTP {response.status_code}). Check your server logs for routing exceptions."
                )

        except requests.exceptions.RequestException as e:
            QMessageBox.critical(self, "Network Error", f"Failed to contact registration server: {e}")
        
        finally:
            # Restore button state
            self.signup_btn.setText("Create Store")
            self.signup_btn.setEnabled(True)
