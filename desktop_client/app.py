import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QStackedWidget
from login import LoginWidget
from signup import SignupWidget
from dashboard import DashboardWidget
from PyQt6.QtGui import QFont

class MainAppController(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gikuru POS Terminal")
        self.resize(560, 660)

        # Light desktop shell for the auth screens and main terminal.
        self.setStyleSheet("""
            QMainWindow {
                background-color: #F6F9FC;
            }
            QStackedWidget {
                background-color: #F6F9FC;
            }
            QLabel {
                color: #07111F;
                font-family: 'Segoe UI', Helvetica, Arial, sans-serif;
            }
            QLineEdit {
                background-color: #FFFFFF;
                border: 1px solid #D6DEE8;
                border-radius: 4px;
                padding: 11px 12px;
                color: #07111F;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 1px solid #008C72;
            }
            QPushButton {
                font-weight: bold;
                font-size: 14px;
                padding: 12px;
                border-radius: 4px;
                border: none;
            }
            QComboBox {
                background-color: #FFFFFF;
                border: 1px solid #D6DEE8;
                border-radius: 4px;
                padding: 10px;
                color: #07111F;
            }
            QComboBox:focus {
                border: 1px solid #008C72;
            }
        """)

        self.central_stack = QStackedWidget()
        self.setCentralWidget(self.central_stack)

        # Initialize the modular widgets
        self.login_page = LoginWidget()
        self.signup_page = SignupWidget()
        self.dashboard_page = DashboardWidget()

        # Mount pages onto our stack index
        self.central_stack.addWidget(self.login_page)     # Index 0
        self.central_stack.addWidget(self.signup_page)    # Index 1
        self.central_stack.addWidget(self.dashboard_page) # Index 2

        # Wire routing signals together
        self.login_page.login_successful.connect(self.go_to_dashboard)
        self.login_page.signup_requested.connect(self.go_to_signup)
        self.signup_page.back_to_login.connect(self.go_to_login)
        self.dashboard_page.logout_requested.connect(self.go_to_login)

        self.go_to_login()

    def go_to_dashboard(self, session_data):
        self.dashboard_page.set_session_data(session_data)
        self.central_stack.setCurrentIndex(2)

    def go_to_signup(self):
        self.central_stack.setCurrentIndex(1)

    def go_to_login(self):
        self.login_page.tenant_input.clear()
        self.login_page.username_input.clear()
        self.login_page.password_input.clear()
        self.central_stack.setCurrentIndex(0)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    main_window = MainAppController()
    main_window.show()
    sys.exit(app.exec())
