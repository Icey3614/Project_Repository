"""基于 PySide6 的界面：毛玻璃主窗口 + 设置对话框。"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, QThreadPool, QTimer, Qt, Signal
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .api import BalanceResult, DeepSeekClient
from .config import (
    DEFAULT_BASE_URL,
    PRESET_BASE_URLS,
    Config,
    State,
    clear_config,
    load_state,
    save_config,
    save_state,
    update_consumption,
)
from .pricing import MODEL_PEAK_PRICES, current_prices, pricing_status

APP_STYLE = """
* { font-family: "Microsoft YaHei UI"; font-size: 12px; color: #E8EAEF; }
QWidget { background: transparent; }
QLabel { background: transparent; border: none; }
QLabel#TitleLabel { font-size: 13px; font-weight: 600; color: rgba(255,255,255,215); }
QLabel#SectionLabel { font-size: 11px; color: rgba(255,255,255,150); }
QLabel#BalanceValue { font-size: 19px; font-weight: 700; color: #FFFFFF; }
QLabel#ConsumptionValue { font-size: 15px; font-weight: 600; color: #FFFFFF; }
QLabel#Secondary { font-size: 11px; color: rgba(255,255,255,150); }
QLabel#StatusOk { font-size: 11px; color: rgba(255,255,255,170); }
QLabel#StatusErr { font-size: 11px; color: #FF7B7B; }
QLabel#PriceLine { font-size: 10px; color: rgba(255,255,255,160); }
QLabel#Hint { font-size: 11px; color: rgba(255,255,255,130); }
QLabel#TestOk { font-size: 12px; color: #5FE3A8; }
QLabel#TestErr { font-size: 12px; color: #FF7B7B; }
QToolButton { background: transparent; border: none; border-radius: 13px;
              color: rgba(255,255,255,200); font-size: 13px; }
QToolButton:hover { background: rgba(255,255,255,45); }
QToolButton#CloseBtn:hover { background: rgba(232,17,35,200); color: #FFFFFF; }
QToolButton#ToggleBtn { font-size: 13px; border: none; background: transparent; }
QLineEdit { background: rgba(255,255,255,35); border: 1px solid rgba(255,255,255,55);
            border-radius: 8px; padding: 7px 10px; color: #FFFFFF;
            selection-background-color: #4D9FFF; }
QLineEdit:focus { border: 1px solid rgba(77,159,255,190); }
QComboBox { background: rgba(255,255,255,35); border: 1px solid rgba(255,255,255,55);
            border-radius: 8px; padding: 5px 8px; color: #FFFFFF; }
QComboBox:focus { border: 1px solid rgba(77,159,255,190); }
QComboBox QAbstractItemView { background: rgba(38,42,58,245); color: #FFFFFF;
                              selection-background-color: #4D9FFF; outline: none; }
QCheckBox { color: rgba(255,255,255,190); spacing: 6px; background: transparent; }
QDoubleSpinBox { background: rgba(255,255,255,35); border: 1px solid rgba(255,255,255,55);
                 border-radius: 8px; padding: 5px 8px; color: #FFFFFF; }
QDoubleSpinBox:focus { border: 1px solid rgba(77,159,255,190); }
QPushButton { background: rgba(77,159,255,200); border: none; border-radius: 8px;
              padding: 7px 16px; color: #FFFFFF; font-weight: 600; }
QPushButton:hover { background: rgba(77,159,255,240); }
QPushButton#SecondaryBtn { background: rgba(255,255,255,30); border: 1px solid rgba(255,255,255,60);
                           font-weight: 400; }
QPushButton#SecondaryBtn:hover { background: rgba(255,255,255,55); }
QPushButton#DangerBtn { background: rgba(232,17,35,170); }
QPushButton#DangerBtn:hover { background: rgba(232,17,35,210); }
QPushButton:disabled { background: rgba(255,255,255,25); color: rgba(255,255,255,100); }
"""


class WorkerSignals(QObject):
    done = Signal(object)
    error = Signal(str)


class Worker(QRunnable):
    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self._fn = fn
        self._args = args
        self._kwargs = kwargs
        self.signals = WorkerSignals()

    def run(self):
        try:
            result = self._fn(*self._args, **self._kwargs)
            self.signals.done.emit(result)
        except Exception as exc:
            self.signals.error.emit(str(exc))


class FrostedWindowMixin:
    """圆角 + 半透明背景 + Acrylic 毛玻璃。"""

    def _setup_frosted(self, radius: int = 16):
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self._radius = radius
        self._drag_pos = None

    def showEvent(self, event):
        super().showEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(1, 1, -1, -1)
        path = QPainterPath()
        path.addRoundedRect(rect, self._radius, self._radius)

        # 接近不透明的深色渐变：壁纸不透出，且不依赖任何系统层
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0.0, QColor(40, 44, 62, 240))
        gradient.setColorAt(1.0, QColor(22, 24, 34, 246))
        painter.fillPath(path, gradient)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and event.position().y() < 34:
            self._drag_pos = (
                event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            )
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None and event.buttons() & Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        super().mouseReleaseEvent(event)


def _icon_button(text: str, tip: str, slot, danger: bool = False) -> QToolButton:
    btn = QToolButton()
    btn.setText(text)
    btn.setToolTip(tip)
    btn.setCursor(Qt.PointingHandCursor)
    btn.setFixedSize(26, 26)
    btn.clicked.connect(slot)
    if danger:
        btn.setObjectName("CloseBtn")
    return btn


class MainWindow(FrostedWindowMixin, QWidget):
    def __init__(self, app_dir: Path, config: Config | None, demo: bool = False):
        super().__init__()
        self.app_dir = app_dir
        self.config = config
        self.demo = demo
        self.state = load_state(app_dir)
        self._fetching = False
        self._workers: list[Worker] = []
        self._auto_opened_settings = False

        self.setWindowTitle("API 余额")
        self.setWindowFlags(Qt.FramelessWindowHint)
        self._setup_frosted(radius=16)
        self.setFixedSize(310, 210)

        self._build_ui()

        interval = (config.refresh_interval if config else 10) * 1000
        self.timer = QTimer(self)
        self.timer.setInterval(interval)
        self.timer.timeout.connect(self.refresh)
        self.timer.start()

        if demo:
            self._demo_state()
            QTimer.singleShot(150, self.refresh)
        elif config is not None:
            QTimer.singleShot(200, self.refresh)

    # ---------- 界面搭建 ----------
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 8, 14, 9)
        root.setSpacing(5)

        root.addLayout(self._build_titlebar())

        # 余额行
        balance_row = QHBoxLayout()
        balance_col = QVBoxLayout()
        balance_col.setSpacing(0)
        balance_col.addWidget(self._section_label("余额"))
        self.balance_value = QLabel("--")
        self.balance_value.setObjectName("BalanceValue")
        balance_col.addWidget(self.balance_value)
        balance_row.addLayout(balance_col)
        balance_row.addStretch(1)
        root.addLayout(balance_row)

        # 累计消费行
        consumption_row = QHBoxLayout()
        consumption_row.addWidget(self._section_label("累计消费金额"))
        consumption_row.addStretch(1)
        self.consumption_value = QLabel("--")
        self.consumption_value.setObjectName("ConsumptionValue")
        consumption_row.addWidget(self.consumption_value)
        root.addLayout(consumption_row)

        # 分隔线
        divider = QLabel()
        divider.setFixedHeight(1)
        divider.setStyleSheet("background: rgba(255,255,255,40);")
        root.addWidget(divider)

        # 当前时段
        self.period_container = QWidget()
        period_row = QHBoxLayout(self.period_container)
        period_row.setContentsMargins(0, 0, 0, 0)
        period_row.setSpacing(8)
        period_row.addWidget(self._section_label("当前时段"))
        self.period_badge = QLabel()
        self.period_badge.setAlignment(Qt.AlignCenter)
        period_row.addWidget(self.period_badge)
        period_row.addStretch(1)
        root.addWidget(self.period_container)

        self.period_detail = QLabel("--")
        self.period_detail.setObjectName("Secondary")
        root.addWidget(self.period_detail)

        # 当前价格
        self.price_flash = QLabel("--")
        self.price_flash.setObjectName("PriceLine")
        root.addWidget(self.price_flash)
        self.price_pro = QLabel("--")
        self.price_pro.setObjectName("PriceLine")
        root.addWidget(self.price_pro)

        root.addStretch(1)

        self.status_label = QLabel("就绪")
        self.status_label.setObjectName("StatusOk")
        root.addWidget(self.status_label)

        self._update_time_ui()

    def _build_titlebar(self) -> QHBoxLayout:
        bar = QHBoxLayout()
        bar.setSpacing(3)
        bar.setContentsMargins(0, 0, 0, 0)
        title = QLabel("API 余额")
        title.setObjectName("TitleLabel")
        bar.addWidget(title)
        bar.addStretch(1)
        bar.addWidget(_icon_button("⟳", "刷新", self.refresh))
        bar.addWidget(_icon_button("⚙\uFE0E", "设置", self.open_settings))
        bar.addWidget(_icon_button("─", "最小化", self.showMinimized))
        bar.addWidget(_icon_button("✕", "关闭", self.close, danger=True))
        return bar

    def _section_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("SectionLabel")
        return label

    # ---------- 数据刷新 ----------
    @staticmethod
    def _demo_result() -> BalanceResult:
        from .api import BalanceEntry

        return BalanceResult(
            is_available=True,
            balances=[
                BalanceEntry("CNY", 110.00, 10.00, 100.00),
                BalanceEntry("USD", 15.00, 0.00, 15.00),
            ],
        )

    def _demo_state(self):
        self.state.prev_total = {"CNY": 110.50, "USD": 15.50}
        self.state.accumulated = {"CNY": 0.50, "USD": 0.50}

    def refresh(self):
        if self._fetching:
            return
        if self.demo:
            self._on_balance(self._demo_result())
            return
        if self.config is None:
            self.status_label.setText("未配置，请打开设置")
            self.status_label.setObjectName("StatusErr")
            self.status_label.setStyleSheet("")
            return

        self._fetching = True
        self.status_label.setText("正在刷新…")
        self.status_label.setObjectName("StatusOk")
        self.status_label.setStyleSheet("")
        client = DeepSeekClient(self.config.api_key, self.config.base_url)
        worker = Worker(client.fetch_balance)
        worker.signals.done.connect(self._on_balance)
        worker.signals.error.connect(self._on_error)
        self._workers.append(worker)
        QThreadPool.globalInstance().start(worker)

    def _on_balance(self, result: BalanceResult):
        self._fetching = False
        self._update_time_ui()

        if result.balances:
            parts = []
            for entry in result.balances:
                symbol = "¥" if entry.currency == "CNY" else "$"
                parts.append(f"{symbol}{entry.total_balance:,.2f} {entry.currency}")
            self.balance_value.setText("  ·  ".join(parts))
        else:
            self.balance_value.setText("--")

        if not self.demo:
            update_consumption(self.state, result.totals())
            self._check_alert(result)
            save_state(self.app_dir, self.state)
        self._show_consumption()

        if not result.is_available:
            self.status_label.setText("余额不足，API 可能无法调用")
            self.status_label.setObjectName("StatusErr")
            self.status_label.setStyleSheet("")
        else:
            self.status_label.setText(
                f"已更新 {datetime.now().strftime('%H:%M:%S')} · 每 {self.timer.interval() // 1000}s 自动刷新"
            )
            self.status_label.setObjectName("StatusOk")
            self.status_label.setStyleSheet("")

    def _check_alert(self, result: BalanceResult):
        """余额低于预警线时弹窗提醒；余额恢复后重置，避免反复弹窗。"""
        if (
            self.config is None
            or not self.config.alert_enabled
            or not result.balances
        ):
            return
        totals = result.totals()
        first = result.balances[0]
        if "CNY" in totals:
            currency, total = "CNY", totals["CNY"]
        else:
            currency, total = first.currency, totals[first.currency]
        symbol = "¥" if currency == "CNY" else "$"
        threshold = self.config.alert_threshold

        if total < threshold:
            if not self.state.alert_fired:
                self.state.alert_fired = True
                QMessageBox.warning(
                    self,
                    "余额预警",
                    f"当前余额 {symbol}{total:,.2f} {currency} "
                    f"已低于预警线 {symbol}{threshold:,.2f}",
                )
        elif self.state.alert_fired:
            self.state.alert_fired = False

    def _show_consumption(self):
        if not self.state.accumulated:
            self.consumption_value.setText("¥0.00")
            return
        parts = []
        for currency, amount in self.state.accumulated.items():
            symbol = "¥" if currency == "CNY" else "$"
            parts.append(f"{symbol}{amount:,.2f} {currency}")
        self.consumption_value.setText("  ·  ".join(parts))

    def _on_error(self, message: str):
        self._fetching = False
        self.status_label.setText(message)
        self.status_label.setObjectName("StatusErr")
        self.status_label.setStyleSheet("")
        # 启动时配置文件存在但连接失败 → 自动打开设置（只弹一次）
        if (
            not self._auto_opened_settings
            and not self.demo
            and self.config is not None
        ):
            self._auto_opened_settings = True
            QTimer.singleShot(150, self.open_settings)

    # ---------- 时段与价格显示 ----------
    def _is_deepseek(self) -> bool:
        """根据 Base URL 判断是否 DeepSeek API（决定是否显示峰谷定价）。"""
        base_url = (
            self.config.base_url if self.config is not None else DEFAULT_BASE_URL
        )
        return "api.deepseek.com" in base_url.lower()

    def _update_time_ui(self):
        is_deepseek = self._is_deepseek()
        self.period_container.setVisible(is_deepseek)
        self.period_detail.setVisible(is_deepseek)

        if is_deepseek:
            status = pricing_status()
            color = "#2ECC8F" if not status.is_peak else "#F5A623"
            self.period_badge.setText(
                f"  {status.period_name} · {status.discount_text}  "
            )
            self.period_badge.setStyleSheet(
                f"background: {color}22; color: {color}; border: 1px solid {color}88;"
                " border-radius: 9px; padding: 1px 4px; font-weight: 600;"
            )
            self.period_detail.setText(
                f"{status.window_text} · {status.now_text}"
            )
            prices = current_prices(status)
        else:
            # 其他平台无峰谷定价，只显示标准价格（全价）
            prices = MODEL_PEAK_PRICES

        flash, pro = prices["deepseek-v4-flash"], prices["deepseek-v4-pro"]
        self.price_flash.setText(
            f"deepseek-v4-flash  输入 ¥{flash['输入']} / 输出 ¥{flash['输出']}（元/百万）"
        )
        self.price_pro.setText(
            f"deepseek-v4-pro    输入 ¥{pro['输入']} / 输出 ¥{pro['输出']}（元/百万）"
        )

    # ---------- 设置 ----------
    def open_settings(self):
        dialog = SettingsDialog(self.app_dir, self.config, parent=self)
        if dialog.exec() and dialog.saved_config is not None:
            self.config = dialog.saved_config
            self.timer.setInterval(self.config.refresh_interval * 1000)
            self.timer.start()
            self.refresh()

    def open_settings_first_run(self):
        dialog = SettingsDialog(self.app_dir, None, parent=self)
        dialog.exec()
        if dialog.saved_config is None:
            return False
        self.config = dialog.saved_config
        self.timer.setInterval(self.config.refresh_interval * 1000)
        self.timer.start()
        self.refresh()
        return True


class SettingsDialog(FrostedWindowMixin, QDialog):
    def __init__(
        self, app_dir: Path, config: Config | None, parent: QWidget | None = None
    ):
        super().__init__(parent)
        self.app_dir = app_dir
        self.config = config
        self.saved_config: Config | None = None
        self._testing = False
        self._workers: list[Worker] = []

        self.setWindowTitle("设置")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self._setup_frosted(radius=16)
        self.setFixedSize(460, 385)

        self._build_ui(config)

    def _build_ui(self, config: Config | None):
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 8, 18, 14)
        root.setSpacing(8)

        bar = QHBoxLayout()
        title = QLabel("设置")
        title.setObjectName("TitleLabel")
        bar.addWidget(title)
        bar.addStretch(1)
        bar.addWidget(_icon_button("✕", "关闭", self.reject, danger=True))
        root.addLayout(bar)

        # API Key
        api_row = QHBoxLayout()
        api_label = self._field_label("API Key")
        api_label.setFixedWidth(80)
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setPlaceholderText("sk-...")
        self.api_key_edit.setEchoMode(QLineEdit.Password)
        toggle = QToolButton()
        toggle.setText("👁\uFE0E")
        toggle.setObjectName("ToggleBtn")
        toggle.setCursor(Qt.PointingHandCursor)
        toggle.setCheckable(True)
        toggle.toggled.connect(
            lambda checked: self.api_key_edit.setEchoMode(
                QLineEdit.Normal if checked else QLineEdit.Password
            )
        )
        api_row.addWidget(api_label)
        api_row.addWidget(self.api_key_edit, 1)
        api_row.addWidget(toggle)
        root.addLayout(api_row)

        # Base URL（可下拉选择，也可手动输入）
        url_row = QHBoxLayout()
        url_label = self._field_label("Base URL")
        url_label.setFixedWidth(80)
        self.base_url_combo = QComboBox()
        self.base_url_combo.setEditable(True)
        preset_urls = {url for _, url in PRESET_BASE_URLS}
        for name, url in PRESET_BASE_URLS:
            self.base_url_combo.addItem(url, url)
            index = self.base_url_combo.count() - 1
            self.base_url_combo.setItemData(index, name, Qt.ToolTipRole)
        if config is not None:
            for url in config.custom_base_urls:
                if url and url not in preset_urls:
                    self.base_url_combo.addItem(url, url)
            if config.base_url:
                self.base_url_combo.setCurrentText(config.base_url)
        else:
            self.base_url_combo.setCurrentText(DEFAULT_BASE_URL)
        url_row.addWidget(url_label)
        url_row.addWidget(self.base_url_combo, 1)
        root.addLayout(url_row)

        # 余额预警
        alert_row = QHBoxLayout()
        alert_label = self._field_label("余额预警")
        alert_label.setFixedWidth(80)
        self.alert_check = QCheckBox("低于预警线时弹窗提醒")
        self.alert_spin = QDoubleSpinBox()
        self.alert_spin.setRange(0.01, 999999.0)
        self.alert_spin.setDecimals(2)
        self.alert_spin.setPrefix("¥ ")
        self.alert_spin.setSingleStep(5.0)
        self.alert_spin.setValue(
            config.alert_threshold if config is not None else 10.0
        )
        alert_enabled = bool(config is not None and config.alert_enabled)
        self.alert_check.setChecked(alert_enabled)
        self.alert_spin.setEnabled(alert_enabled)
        self.alert_check.toggled.connect(self.alert_spin.setEnabled)
        alert_row.addWidget(alert_label)
        alert_row.addWidget(self.alert_check)
        alert_row.addStretch(1)
        alert_row.addWidget(self.alert_spin)
        root.addLayout(alert_row)

        hint = QLabel("配置将保存在程序同目录下的 config.json，请勿泄露 API Key。")
        hint.setObjectName("Hint")
        hint.setWordWrap(True)
        root.addWidget(hint)

        self.test_result = QLabel("")
        self.test_result.setObjectName("TestOk")
        self.test_result.setWordWrap(True)
        root.addWidget(self.test_result)

        root.addStretch(1)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        test_btn = QPushButton("连接测试")
        test_btn.setObjectName("SecondaryBtn")
        test_btn.clicked.connect(self._test_connection)
        btn_row.addWidget(test_btn)
        clear_btn = QPushButton("一键清除配置")
        clear_btn.setObjectName("DangerBtn")
        clear_btn.clicked.connect(self._clear_config)
        btn_row.addWidget(clear_btn)
        btn_row.addStretch(1)
        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self._save)
        btn_row.addWidget(save_btn)
        root.addLayout(btn_row)

        if config is not None:
            self.api_key_edit.setText(config.api_key)

    def _field_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("SectionLabel")
        return label

    def _read_form(self) -> Config:
        url = self.base_url_combo.currentText().strip() or DEFAULT_BASE_URL
        custom_urls = list(self.config.custom_base_urls) if self.config else []
        preset_urls = {u for _, u in PRESET_BASE_URLS}
        if url not in preset_urls and url not in custom_urls:
            custom_urls.append(url)
        return Config(
            api_key=self.api_key_edit.text().strip(),
            base_url=url,
            refresh_interval=10,
            alert_enabled=self.alert_check.isChecked(),
            alert_threshold=round(self.alert_spin.value(), 2),
            custom_base_urls=custom_urls,
        )

    def _set_test_result(self, text: str, ok: bool):
        self.test_result.setObjectName("TestOk" if ok else "TestErr")
        self.test_result.setText(text)

    def _test_connection(self):
        if self._testing:
            return
        cfg = self._read_form()
        error = cfg.validate()
        if error:
            self._set_test_result(error, ok=False)
            return
        self._testing = True
        self._set_test_result("正在测试连接…", ok=True)
        client = DeepSeekClient(cfg.api_key, cfg.base_url)
        worker = Worker(client.fetch_balance)
        worker.signals.done.connect(self._on_test_ok)
        worker.signals.error.connect(self._on_test_fail)
        self._workers.append(worker)
        QThreadPool.globalInstance().start(worker)

    def _on_test_ok(self, result: BalanceResult):
        self._testing = False
        if result.balances:
            entry = result.balances[0]
            symbol = "¥" if entry.currency == "CNY" else "$"
            self._set_test_result(
                f"连接成功！当前余额 {symbol}{entry.total_balance:,.2f} {entry.currency}",
                ok=True,
            )
        else:
            self._set_test_result("连接成功，但未返回余额数据", ok=True)

    def _on_test_fail(self, message: str):
        self._testing = False
        self._set_test_result(f"连接失败：{message}", ok=False)

    def _save(self):
        cfg = self._read_form()
        try:
            save_config(self.app_dir, cfg)
        except OSError as exc:
            QMessageBox.warning(self, "保存失败", f"无法写入配置文件：{exc}")
            return
        self.saved_config = cfg
        self._set_test_result("✓ 保存成功，配置已写入 config.json", ok=True)
        QTimer.singleShot(800, self.accept)

    def _clear_config(self):
        answer = QMessageBox.question(
            self,
            "清除配置",
            "确定清除程序同目录下的配置文件吗？\n清除后需重新填写 API Key，"
            "且累计消费记录也会一并重置。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        removed = clear_config(self.app_dir)
        self.api_key_edit.clear()
        self.base_url_combo.setCurrentText(DEFAULT_BASE_URL)
        self.alert_check.setChecked(False)
        self.alert_spin.setValue(10.0)
        self._set_test_result(
            "已清除配置文件与消费记录" if removed else "未发现配置文件", ok=True
        )
