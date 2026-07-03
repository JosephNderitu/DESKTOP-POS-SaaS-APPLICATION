from PyQt6.QtWidgets import (
    QComboBox, QFrame, QGraphicsOpacityEffect, QGridLayout, QHBoxLayout,
    QLabel, QLineEdit, QMessageBox, QPushButton, QScrollArea, QSizePolicy,
    QSpacerItem, QToolButton, QVBoxLayout, QWidget
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QAction
from workers import InventoryFetchWorker
import qtawesome as qta

from functools import lru_cache


# ---------------------------------------------------------------------------
# Product card
# ---------------------------------------------------------------------------

class ProductCardWidget(QFrame):
    """Ecommerce-style product tile for cashier catalog browsing."""
    add_requested = pyqtSignal(dict)

    IMAGE_BOX = 132  # fixed square image slot, keeps the grid perfectly aligned

    def __init__(self, product, parent=None):
        super().__init__(parent)
        self.product = product
        self.init_ui()

    def init_ui(self):
        self.setObjectName("productCard")
        self.setMinimumWidth(215)
        self.setMaximumWidth(320)
        self.setMinimumHeight(320)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(9)

        layout.addWidget(self._build_image_panel())

        meta_row = QHBoxLayout()
        category_name = self.product.get('category_detail', {}) or {}
        category_text = category_name.get('name', 'Catalog item')
        category_label = QLabel(category_text.upper())
        category_label.setStyleSheet("color: #0B3D91; font-size: 10px; font-weight: 800; letter-spacing: 0.4px;")
        category_label.setWordWrap(False)
        meta_row.addWidget(category_label)
        meta_row.addStretch()

        discount_value = self.product.get('discount_percent') or self.product.get('product_discount') or self.product.get('discount')
        has_discount = bool(discount_value) and float(discount_value) > 0
        if has_discount:
            discount_pill = QLabel(f"-{discount_value}%")
            discount_pill.setStyleSheet("""
                background-color: #FEE2E2; color: #DC2626; font-size: 10px; font-weight: 900;
                border-radius: 7px; padding: 2px 7px;
            """)
            meta_row.addWidget(discount_pill)
        layout.addLayout(meta_row)

        name_label = QLabel(self.product.get('name', 'Unknown Item'))
        name_label.setStyleSheet("font-size: 15px; font-weight: 800; color: #07111F;")
        name_label.setWordWrap(True)
        name_label.setMaximumHeight(42)
        layout.addWidget(name_label)

        sku_label = QLabel(f"SKU: {self.product.get('sku', 'N/A')}")
        sku_label.setStyleSheet("font-size: 11px; color: #94A3B8;")
        layout.addWidget(sku_label)

        layout.addStretch()

        selling_price = float(self.product.get('selling_price', 0.0))
        discount = float(discount_value) if has_discount else 0
        price_row = QHBoxLayout()
        price_row.setSpacing(8)
        if discount > 0:
            discounted_price = selling_price * (1 - discount / 100)
            price_label = QLabel(f"KES {discounted_price:,.2f}")
            price_label.setStyleSheet("font-size: 17px; font-weight: 900; color: #008C72;")
            price_row.addWidget(price_label)
            original_price_label = QLabel(f"KES {selling_price:,.2f}")
            original_price_label.setStyleSheet("font-size: 11px; color: #94A3B8; text-decoration: line-through;")
            price_row.addWidget(original_price_label)
        else:
            price_label = QLabel(f"KES {selling_price:,.2f}")
            price_label.setStyleSheet("font-size: 17px; font-weight: 900; color: #008C72;")
            price_row.addWidget(price_label)
        price_row.addStretch()
        layout.addLayout(price_row)

        qty = self.product.get('stock_quantity', 0)
        low_stock_threshold = self.product.get('low_stock_threshold', 5)
        is_low = qty <= low_stock_threshold
        stock_row = QHBoxLayout()
        qty_label = QLabel(f"{qty} in stock")
        qty_label.setStyleSheet(f"font-size: 11px; font-weight: 700; color: {'#DC2626' if is_low else '#64748B'};")
        stock_row.addWidget(qty_label)
        stock_row.addStretch()
        stock_pill = QLabel("Low stock" if is_low and qty > 0 else ("Out of stock" if qty <= 0 else "In stock"))
        stock_pill.setStyleSheet(f"""
            font-size: 10px; font-weight: 800; color: white; border-radius: 7px; padding: 2px 8px;
            background-color: {'#DC2626' if qty <= 0 else ('#F59E0B' if is_low else '#008C72')};
        """)
        stock_row.addWidget(stock_pill)
        layout.addLayout(stock_row)

        add_btn = QPushButton(" Add to Checkout")
        add_btn.setIcon(qta.icon('fa5s.cart-plus', color='white'))
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.setEnabled(qty > 0)
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #008C72;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 10px 10px;
                font-size: 13px;
                font-weight: 800;
            }
            QPushButton:hover { background-color: #006F5B; }
            QPushButton:disabled { background-color: #CBD5E1; color: #64748B; }
        """)
        add_btn.clicked.connect(lambda: self.add_requested.emit(self.product))
        layout.addWidget(add_btn)

        self.setStyleSheet("""
            QFrame#productCard {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 10px;
            }
            QFrame#productCard:hover {
                border: 1px solid #38BDF8;
                background-color: #F8FCFF;
            }
        """)

        # Visually communicate "unavailable" beyond just disabling the button,
        # a dimmed card reads instantly to a cashier scanning the grid
        if qty <= 0:
            effect = QGraphicsOpacityEffect(self)
            effect.setOpacity(0.55)
            self.setGraphicsEffect(effect)

    def _build_image_panel(self):
        image_panel = QFrame()
        image_panel.setObjectName("productImage")
        image_panel.setFixedHeight(self.IMAGE_BOX)
        image_panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        image_layout = QVBoxLayout(image_panel)
        image_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        image_layout.setContentsMargins(0, 0, 0, 0)

        image_icon = QLabel()
        image_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        image_icon.setFixedSize(self.IMAGE_BOX - 16, self.IMAGE_BOX - 16)

        image_url = self.product.get('image_url')
        pixmap = self.get_cached_pixmap(image_url) if image_url else None
        if pixmap:
            scaled_pixmap = pixmap.scaled(
                image_icon.width(), image_icon.height(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            image_icon.setPixmap(scaled_pixmap)
        else:
            image_icon.setPixmap(qta.icon('fa5s.shopping-bag', color='#93C5FD').pixmap(44, 44))

        image_layout.addWidget(image_icon)

        image_panel.setStyleSheet("""
            QFrame#productImage {
                background-color: #F0F9FF;
                border: 1px solid #E0F2FE;
                border-radius: 8px;
            }
        """)
        return image_panel

    @staticmethod
    @lru_cache(maxsize=128)
    def get_cached_pixmap(image_url):
        """
        Fetches and caches a product image.

        Development note: tenant subdomains like store1.localhost aren't
        resolved by Python's DNS stack the way browsers special-case them.
        We connect straight to the known dev host/port and pass the real
        tenant hostname via the Host header instead, since TenantMainMiddleware
        routes purely off that header, not the socket destination.
        """
        try:
            import requests
            from urllib.parse import urlparse
            from PyQt6.QtGui import QPixmap
            from PyQt6.QtCore import QByteArray
            from config import IS_DEVELOPMENT, BASE_DEV_URL

            fetch_url = image_url
            headers = {}

            if IS_DEVELOPMENT:
                parsed = urlparse(image_url)
                dev_netloc = urlparse(BASE_DEV_URL).netloc
                headers["Host"] = parsed.netloc
                fetch_url = image_url.replace(parsed.netloc, dev_netloc, 1)

            response = requests.get(fetch_url, headers=headers, timeout=5)
            if response.status_code == 200:
                pixmap = QPixmap()
                pixmap.loadFromData(QByteArray(response.content))
                if not pixmap.isNull():
                    return pixmap
        except Exception as e:
            print("Image fetch failed:", e)
        return None


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

class DashboardWidget(QWidget):
    logout_requested = pyqtSignal()

    # Placeholder navigation signals, wire these up to real screens later
    scanner_requested = pyqtSignal()
    settings_requested = pyqtSignal()
    sales_history_requested = pyqtSignal()
    manager_requested = pyqtSignal()
    notifications_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.session_info = {}
        self.products = []
        self.filtered_products = []
        self.cart = {}
        self.current_columns = 0
        self.init_ui()

    # -- layout construction -------------------------------------------------

    def init_ui(self):
        self.setStyleSheet("QWidget { font-family: 'Segoe UI', Helvetica, Arial, sans-serif; }")

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        root_layout.addWidget(self._build_header())

        body = QWidget()
        body.setStyleSheet("background-color: #F1F5F9;")
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(18, 16, 18, 16)
        body_layout.setSpacing(18)

        left_panel = QVBoxLayout()
        left_panel.setSpacing(12)
        left_panel.addWidget(self._build_toolbar())
        left_panel.addWidget(self._build_catalog_area(), stretch=1)
        body_layout.addLayout(left_panel, stretch=3)

        body_layout.addWidget(self._build_cart_sidebar(), stretch=1)

        root_layout.addWidget(body, stretch=1)
        self.refresh_cart()

    def _build_header(self):
        """Top bar: branding on the left, primary navigation and profile on the right."""
        header = QWidget()
        header.setFixedHeight(64)
        header.setStyleSheet("background-color: #061A40;")
        layout = QHBoxLayout(header)
        layout.setContentsMargins(20, 0, 16, 0)
        layout.setSpacing(14)

        # Branding / logo placeholder
        logo_icon = QLabel()
        logo_icon.setPixmap(qta.icon('fa5s.receipt', color='#7DD3FC').pixmap(26, 26))
        layout.addWidget(logo_icon)

        brand_box = QVBoxLayout()
        brand_box.setSpacing(0)
        brand_title = QLabel("RVC POS")
        brand_title.setStyleSheet("color: #FFFFFF; font-size: 16px; font-weight: 900; letter-spacing: 0.4px;")
        brand_box.addWidget(brand_title)
        self.tenant_subtitle = QLabel("Connecting to store...")
        self.tenant_subtitle.setStyleSheet("color: #93A9CC; font-size: 10px; font-weight: 600;")
        brand_box.addWidget(self.tenant_subtitle)
        layout.addLayout(brand_box)

        layout.addStretch()

        # Primary navigation, all placeholders for now
        layout.addWidget(self._nav_button('fa5s.th-large', "Dashboard", active=True))
        layout.addWidget(self._nav_button('fa5s.barcode', "Scanner", self._on_scanner))
        layout.addWidget(self._nav_button('fa5s.history', "Sales History", self._on_sales_history))
        layout.addWidget(self._nav_button('fa5s.user-tie', "Manager Dashboard", self._on_manager))
        layout.addWidget(self._nav_button('fa5s.bell', "Notifications", self._on_notifications))
        layout.addWidget(self._nav_button('fa5s.cog', "Settings", self._on_settings))

        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.VLine)
        divider.setStyleSheet("color: #1E3A6D;")
        layout.addWidget(divider)

        layout.addWidget(self._build_profile_pill())

        return header

    def _nav_button(self, icon_name, tooltip, on_click=None, active=False):
        btn = QToolButton()
        btn.setIcon(qta.icon(icon_name, color='#0B3D91' if active else '#DCEBFA'))
        btn.setIconSize(QSize(18, 18))
        btn.setToolTip(tooltip)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setAutoRaise(True)
        btn.setStyleSheet(f"""
            QToolButton {{
                background-color: {'#7DD3FC' if active else 'transparent'};
                border-radius: 8px;
                padding: 9px;
            }}
            QToolButton:hover {{
                background-color: {'#7DD3FC' if active else 'rgba(255,255,255,0.12)'};
            }}
        """)
        if on_click:
            btn.clicked.connect(on_click)
        else:
            btn.clicked.connect(lambda: None)
        return btn

    def _build_profile_pill(self):
        pill = QFrame()
        pill.setStyleSheet("background-color: #0B3D91; border-radius: 18px;")
        layout = QHBoxLayout(pill)
        layout.setContentsMargins(6, 6, 12, 6)
        layout.setSpacing(8)

        self.avatar_label = QLabel("?")
        self.avatar_label.setFixedSize(28, 28)
        self.avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.avatar_label.setStyleSheet("""
            background-color: #7DD3FC; color: #061A40; border-radius: 14px;
            font-weight: 900; font-size: 12px;
        """)
        layout.addWidget(self.avatar_label)

        profile_box = QVBoxLayout()
        profile_box.setSpacing(0)
        self.profile_name_label = QLabel("Operator")
        self.profile_name_label.setStyleSheet("color: #FFFFFF; font-size: 12px; font-weight: 800;")
        profile_box.addWidget(self.profile_name_label)
        self.profile_role_label = QLabel("Role")
        self.profile_role_label.setStyleSheet("color: #93A9CC; font-size: 10px;")
        profile_box.addWidget(self.profile_role_label)
        layout.addLayout(profile_box)

        return pill

    def _build_toolbar(self):
        """Search + category filter + catalog sync, grouped as catalog-scoped actions."""
        toolbar = QFrame()
        toolbar.setStyleSheet("QFrame { background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; }")
        layout = QHBoxLayout(toolbar)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search products by name or SKU...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #E2E8F0; border-radius: 6px; padding: 8px 10px;
                font-size: 13px; color: #07111F; background-color: #F8FAFC;
            }
            QLineEdit:focus { border: 1px solid #008C72; }
        """)
        search_icon_action = QAction(qta.icon('fa5s.search', color='#94A3B8'), "", self.search_input)
        self.search_input.addAction(search_icon_action, QLineEdit.ActionPosition.LeadingPosition)
        self.search_input.textChanged.connect(self.apply_filters)
        layout.addWidget(self.search_input, stretch=3)

        self.category_filter = QComboBox()
        self.category_filter.addItem("All Categories")
        self.category_filter.setStyleSheet("""
            QComboBox {
                border: 1px solid #E2E8F0; border-radius: 6px; padding: 8px 10px;
                font-size: 13px; color: #07111F; background-color: #F8FAFC; min-width: 150px;
            }
            QComboBox:focus { border: 1px solid #008C72; }
            QComboBox QAbstractItemView {
                background-color: #FFFFFF;
                color: #07111F;
                selection-background-color: #DBEAFE;
                selection-color: #07111F;
                border: 1px solid #E2E8F0;
                outline: none;
                padding: 4px;
            }
        """)
        self.category_filter.currentIndexChanged.connect(self.apply_filters)
        layout.addWidget(self.category_filter, stretch=1)

        scan_btn = QPushButton(" Scan")
        scan_btn.setIcon(qta.icon('fa5s.barcode', color='#0B3D91'))
        scan_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        scan_btn.setStyleSheet("""
            QPushButton {
                background-color: #EAF4FF; color: #0B3D91; border: 1px solid #BFDBFE;
                border-radius: 6px; padding: 8px 14px; font-size: 12px; font-weight: 800;
            }
            QPushButton:hover { background-color: #DBEAFE; }
        """)
        scan_btn.clicked.connect(self._on_scanner)
        layout.addWidget(scan_btn)

        self.refresh_btn = QPushButton(" Sync Catalog")
        self.refresh_btn.setIcon(qta.icon('fa5s.sync-alt', color='white'))
        self.refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #0B3D91; color: white; font-size: 12px; font-weight: 800;
                padding: 8px 14px; border-radius: 6px;
            }
            QPushButton:hover { background-color: #061A40; }
            QPushButton:disabled { background-color: #94A3B8; }
        """)
        self.refresh_btn.clicked.connect(self.trigger_background_sync)
        layout.addWidget(self.refresh_btn)

        return toolbar

    def _build_catalog_area(self):
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(8)

        title_row = QHBoxLayout()
        catalog_title = QLabel("Product Catalog")
        catalog_title.setStyleSheet("font-size: 15px; font-weight: 800; color: #061A40;")
        title_row.addWidget(catalog_title)
        title_row.addStretch()
        self.results_count_label = QLabel("")
        self.results_count_label.setStyleSheet("font-size: 11px; color: #64748B;")
        title_row.addWidget(self.results_count_label)
        container_layout.addLayout(title_row)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")

        self.grid_container = QWidget()
        self.grid_container.setStyleSheet("background-color: transparent;")
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setSpacing(16)
        self.grid_layout.setContentsMargins(2, 2, 2, 12)

        self.scroll_area.setWidget(self.grid_container)
        container_layout.addWidget(self.scroll_area, stretch=1)

        return container

    def _build_cart_sidebar(self):
        right_sidebar_widget = QWidget()
        right_sidebar_widget.setMinimumWidth(280)
        right_sidebar_widget.setMaximumWidth(360)
        right_sidebar_widget.setStyleSheet("""
            QWidget {
                background-color: #061A40;
                border-radius: 10px;
            }
            QLabel { border: none; }
            QPushButton { border: none; }
        """)

        right_panel = QVBoxLayout(right_sidebar_widget)
        right_panel.setContentsMargins(20, 20, 20, 20)
        right_panel.setSpacing(14)

        sidebar_title = QLabel("Terminal Status")
        sidebar_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #FFFFFF;")
        right_panel.addWidget(sidebar_title)

        self.meta_label = QLabel("Connecting...")
        self.meta_label.setStyleSheet("font-size: 12px; color: #DCEBFA;")
        self.meta_label.setWordWrap(True)
        right_panel.addWidget(self.meta_label)

        cart_header_row = QHBoxLayout()
        cart_title = QLabel("Checkout Cart")
        cart_title.setStyleSheet("font-size: 16px; font-weight: 900; color: #FFFFFF; margin-top: 8px;")
        cart_header_row.addWidget(cart_title)
        cart_header_row.addStretch()
        clear_cart_btn = QToolButton()
        clear_cart_btn.setIcon(qta.icon('fa5s.trash-alt', color='#93A9CC'))
        clear_cart_btn.setToolTip("Clear cart")
        clear_cart_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_cart_btn.setAutoRaise(True)
        clear_cart_btn.clicked.connect(self.clear_cart)
        cart_header_row.addWidget(clear_cart_btn)
        right_panel.addLayout(cart_header_row)

        self.cart_scroll = QScrollArea()
        self.cart_scroll.setWidgetResizable(True)
        self.cart_scroll.setMinimumHeight(220)
        self.cart_scroll.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")
        self.cart_container = QWidget()
        self.cart_container.setStyleSheet("background-color: transparent; border: none;")
        self.cart_layout = QVBoxLayout(self.cart_container)
        self.cart_layout.setContentsMargins(0, 0, 0, 0)
        self.cart_layout.setSpacing(8)
        self.cart_scroll.setWidget(self.cart_container)
        right_panel.addWidget(self.cart_scroll, stretch=1)

        summary_frame = QFrame()
        summary_frame.setStyleSheet("background-color: #0B3D91; border-radius: 8px;")
        summary_layout = QVBoxLayout(summary_frame)
        summary_layout.setContentsMargins(14, 12, 14, 12)
        summary_layout.setSpacing(4)

        self.cart_subtotal_label = QLabel("Subtotal: KES 0.00")
        self.cart_subtotal_label.setStyleSheet("font-size: 12px; color: #DCEBFA;")
        summary_layout.addWidget(self.cart_subtotal_label)

        self.cart_total_label = QLabel("Total: KES 0.00")
        self.cart_total_label.setStyleSheet("font-size: 18px; font-weight: 900; color: #7DD3FC;")
        summary_layout.addWidget(self.cart_total_label)
        right_panel.addWidget(summary_frame)

        self.checkout_btn = QPushButton(" Checkout")
        self.checkout_btn.setIcon(qta.icon('fa5s.cash-register', color='white'))
        self.checkout_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.checkout_btn.setEnabled(False)
        self.checkout_btn.setStyleSheet("""
            QPushButton {
                background-color: #008C72;
                color: white;
                padding: 11px;
                font-weight: 900;
                font-size: 13px;
                border-radius: 6px;
            }
            QPushButton:hover { background-color: #006F5B; }
            QPushButton:disabled { background-color: #475569; color: #CBD5E1; }
        """)
        right_panel.addWidget(self.checkout_btn)

        self.logout_btn = QPushButton(" End Shift")
        self.logout_btn.setIcon(qta.icon('fa5s.power-off', color='white'))
        self.logout_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.logout_btn.setStyleSheet("""
            QPushButton {
                background-color: #DC2626;
                color: white;
                padding: 9px;
                font-weight: bold;
                font-size: 12px;
                border-radius: 6px;
            }
            QPushButton:hover { background-color: #B91C1C; }
        """)
        self.logout_btn.clicked.connect(self.logout_requested.emit)
        right_panel.addWidget(self.logout_btn)

        return right_sidebar_widget

    # -- placeholder nav handlers ---------------------------------------------
    # Each emits its signal (so real screens can be wired in later without
    # touching this file) and shows a lightweight "coming soon" notice so the
    # buttons feel alive today rather than dead-clicking.

    def _on_scanner(self):
        self.scanner_requested.emit()
        self._show_coming_soon("Barcode Scanner", "Point a connected scanner at a barcode to add items instantly.")

    def _on_settings(self):
        self.settings_requested.emit()
        self._show_coming_soon("Settings", "Terminal preferences, printer setup, and receipt options will live here.")

    def _on_sales_history(self):
        self.sales_history_requested.emit()
        self._show_coming_soon("Sales History", "A searchable log of this terminal's past transactions.")

    def _on_manager(self):
        self.manager_requested.emit()
        self._show_coming_soon("Manager Dashboard", "Store-wide reporting and staff management for managers.")

    def _on_notifications(self):
        self.notifications_requested.emit()
        self._show_coming_soon("Notifications", "Low-stock alerts and system notices will appear here.")

    def _show_coming_soon(self, feature_name, description):
        QMessageBox.information(self, feature_name, f"{description}\n\nThis feature is coming soon.")

    # -- session / data --------------------------------------------------------

    def set_session_data(self, session_info):
        self.session_info = session_info
        tenant = session_info.get('tenant', 'store')
        username = session_info.get('username', 'Operator')
        role = session_info.get('role', 'Cashier')

        self.tenant_subtitle.setText(f"{tenant}.localhost")
        self.profile_name_label.setText(username)
        self.profile_role_label.setText(role)
        self.avatar_label.setText((username[:1] or "?").upper())

        self.meta_label.setText(
            f"<b>Tenant Location:</b><br>{tenant}.localhost<br><br>"
            f"<b>Access Clearances:</b><br>{role}<br><br>"
            f"<b>Network State:</b><br><font color='#7DD3FC'>Online Session</font>"
        )
        self.trigger_background_sync()

    def trigger_background_sync(self):
        self.refresh_btn.setEnabled(False)
        self.refresh_btn.setText(" Syncing...")
        self.clear_product_grid()

        self.worker = InventoryFetchWorker(
            tenant=self.session_info.get('tenant'),
            token=self.session_info.get('token')
        )
        self.worker.fetch_finished.connect(self.populate_product_grid)
        self.worker.fetch_failed.connect(self.handle_sync_failure)
        self.worker.start()

    def populate_product_grid(self, products):
        self.refresh_btn.setEnabled(True)
        self.refresh_btn.setText(" Sync Catalog")
        self.products = products
        self._refresh_category_options()
        self.apply_filters()

    def _refresh_category_options(self):
        categories = sorted({
            (p.get('category_detail') or {}).get('name')
            for p in self.products
            if (p.get('category_detail') or {}).get('name')
        })
        self.category_filter.blockSignals(True)
        self.category_filter.clear()
        self.category_filter.addItem("All Categories")
        for category in categories:
            self.category_filter.addItem(category)
        self.category_filter.blockSignals(False)

    def apply_filters(self):
        query = self.search_input.text().strip().lower() if hasattr(self, 'search_input') else ""
        selected_category = self.category_filter.currentText() if hasattr(self, 'category_filter') else "All Categories"

        filtered = self.products
        if query:
            filtered = [
                p for p in filtered
                if query in (p.get('name', '') or '').lower() or query in (p.get('sku', '') or '').lower()
            ]
        if selected_category and selected_category != "All Categories":
            filtered = [
                p for p in filtered
                if (p.get('category_detail') or {}).get('name') == selected_category
            ]

        self.filtered_products = filtered
        self.results_count_label.setText(f"{len(filtered)} of {len(self.products)} products")
        self.render_product_grid()

    def clear_product_grid(self):
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)

    def render_product_grid(self):
        self.clear_product_grid()
        products_to_render = self.filtered_products

        if not products_to_render:
            message = "No active products found in this branch inventory." if not self.products \
                else "No products match your search or filter."
            empty_box = QVBoxLayout()
            icon_label = QLabel()
            icon_label.setPixmap(qta.icon('fa5s.box-open', color='#CBD5E1').pixmap(40, 40))
            icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            text_label = QLabel(message)
            text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            text_label.setStyleSheet("color: #64748B; font-size: 13px; font-style: italic; margin-top: 8px;")
            wrapper = QWidget()
            wrapper_layout = QVBoxLayout(wrapper)
            wrapper_layout.addWidget(icon_label)
            wrapper_layout.addWidget(text_label)
            self.grid_layout.addWidget(wrapper, 0, 0, alignment=Qt.AlignmentFlag.AlignCenter)
            return

        available_width = max(self.scroll_area.viewport().width(), 260)
        card_min_width = 235
        cols = max(1, min(6, available_width // card_min_width))
        self.current_columns = cols

        for index, item in enumerate(products_to_render):
            row = index // cols
            col = index % cols
            card = ProductCardWidget(item)
            card.add_requested.connect(self.add_to_cart)
            self.grid_layout.addWidget(card, row, col)

        for col in range(cols):
            self.grid_layout.setColumnStretch(col, 1)

    # -- cart --------------------------------------------------------------

    def add_to_cart(self, product):
        product_id = product.get('id') or product.get('sku')
        if product_id not in self.cart:
            self.cart[product_id] = {"product": product, "quantity": 0}

        stock_quantity = int(product.get('stock_quantity', 0))
        if self.cart[product_id]["quantity"] >= stock_quantity:
            QMessageBox.information(self, "Stock Limit", "All available stock for this item is already in the cart.")
            return

        self.cart[product_id]["quantity"] += 1
        self.refresh_cart()

    def clear_cart(self):
        if not self.cart:
            return
        confirm = QMessageBox.question(
            self, "Clear Cart", "Remove all items from the checkout cart?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self.cart = {}
            self.refresh_cart()

    def refresh_cart(self):
        while self.cart_layout.count():
            item = self.cart_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)

        total = 0.0
        if not self.cart:
            empty_label = QLabel("Cart is empty. Add products from the catalog.")
            empty_label.setWordWrap(True)
            empty_label.setStyleSheet("color: #CBD5E1; font-size: 12px;")
            self.cart_layout.addWidget(empty_label)
        else:
            for product_id, cart_item in self.cart.items():
                product = cart_item["product"]
                quantity = cart_item["quantity"]
                price = float(product.get('selling_price', 0.0))
                line_total = price * quantity
                total += line_total

                item_frame = QFrame()
                item_frame.setObjectName("cartItem")
                item_frame.setStyleSheet("""
                    QFrame#cartItem {
                        background-color: #0B3D91;
                        border: 1px solid #1D4ED8;
                        border-radius: 6px;
                    }
                    QLabel { border: none; }
                    QPushButton { border: none; }
                """)
                item_layout = QVBoxLayout(item_frame)
                item_layout.setContentsMargins(10, 8, 10, 8)
                item_layout.setSpacing(4)

                item_name = QLabel(product.get('name', 'Unknown Item'))
                item_name.setWordWrap(True)
                item_name.setStyleSheet("color: #FFFFFF; font-size: 12px; font-weight: 800;")
                item_layout.addWidget(item_name)

                item_meta = QLabel(f"{quantity} x KES {price:,.2f} = KES {line_total:,.2f}")
                item_meta.setStyleSheet("color: #DCEBFA; font-size: 11px;")
                item_layout.addWidget(item_meta)

                actions = QHBoxLayout()
                minus_btn = QPushButton("-")
                plus_btn = QPushButton("+")
                for btn in (minus_btn, plus_btn):
                    btn.setFixedSize(28, 24)
                    btn.setCursor(Qt.CursorShape.PointingHandCursor)
                    btn.setStyleSheet("""
                        QPushButton {
                            background-color: #FFFFFF;
                            color: #061A40;
                            border-radius: 4px;
                            font-weight: 900;
                            font-size: 14px;
                            padding: 0px;
                        }
                        QPushButton:hover { background-color: #E0F2FE; }
                    """)
                minus_btn.clicked.connect(lambda _, pid=product_id: self.change_cart_quantity(pid, -1))
                plus_btn.clicked.connect(lambda _, pid=product_id: self.change_cart_quantity(pid, 1))
                actions.addWidget(minus_btn)
                actions.addWidget(plus_btn)
                actions.addStretch()
                item_layout.addLayout(actions)

                self.cart_layout.addWidget(item_frame)

        self.cart_layout.addStretch()
        self.cart_subtotal_label.setText(f"Subtotal: KES {total:,.2f}")
        self.cart_total_label.setText(f"Total: KES {total:,.2f}")
        self.checkout_btn.setEnabled(bool(self.cart))

    def change_cart_quantity(self, product_id, delta):
        if product_id not in self.cart:
            return

        product = self.cart[product_id]["product"]
        next_quantity = self.cart[product_id]["quantity"] + delta
        stock_quantity = int(product.get('stock_quantity', 0))

        if next_quantity <= 0:
            del self.cart[product_id]
        elif next_quantity <= stock_quantity:
            self.cart[product_id]["quantity"] = next_quantity
        else:
            QMessageBox.information(self, "Stock Limit", "You cannot add more than the available stock.")

        self.refresh_cart()

    # -- responsiveness ------------------------------------------------------

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.filtered_products:
            available_width = max(self.scroll_area.viewport().width(), 260)
            next_columns = max(1, min(6, available_width // 235))
            if next_columns != self.current_columns:
                self.render_product_grid()

    def handle_sync_failure(self, error_message):
        self.refresh_btn.setEnabled(True)
        self.refresh_btn.setText(" Sync Catalog")
        QMessageBox.warning(self, "Catalog Sync Interrupted", f"Failed to fetch stock updates: {error_message}")