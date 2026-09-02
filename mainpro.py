"""
CareEyes Pro v5.2
轻量护眼工具 - 紧凑界面版

依赖安装:
    pip install PyQt5 pynput

桌面宠物（新增）:
  - 纯 QPainter 绘制，无额外依赖；跟随护眼状态变表情
  - 脚下细进度条显示距离下次休息的进度
  - 戳一戳有反应、拖动贴边、位置记忆
  - 右键菜单：打开主界面 / 立即休息 / 切换护眼 / 藏起来 / 退出
  - 托盘和设置页均有开关，状态写入配置文件

v5.2 新增/修复:
  - 顶部紧凑导航替代宽侧边栏，减少界面占用
  - 预设按钮和页面间距收紧，信息密度更高
  - 去除未使用的 pywin32 依赖
  - 增加精简 PyInstaller 构建配置和 Windows 版本信息
"""

import sys
import ctypes
import ctypes.wintypes
import math
import json
import os
import winreg
from datetime import datetime, date, timedelta
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QLabel,
    QSlider, QHBoxLayout, QFrame, QStackedWidget, QSpinBox,
    QSystemTrayIcon, QMenu, QAction, QCheckBox, QGraphicsDropShadowEffect,
    QSizePolicy
)
from PyQt5.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve, QRect, pyqtSignal, QObject
)
from PyQt5.QtGui import (
    QColor, QCursor, QFont, QFontMetrics, QIcon, QPainter, QPen, QPixmap
)

# ─────────────────────────────────────────────
# ⚙️  全局常量
# ─────────────────────────────────────────────
APP_NAME    = "CareEyesPro"
APP_TITLE   = "CareEyes Pro"
APP_VER     = "v5.2"
CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".care_eyes_pro.json")

# 全屏检测：这些进程名即便占全屏也不触发推迟（黑名单=不推迟）
FULLSCREEN_WHITELIST = {
    "explorer.exe", "shellexperiencehost.exe", "searchhost.exe",
    "wallpaperengine.exe", "desktopwindowmanager.exe", "dwm.exe",
    "lively.exe", "rainmeter.exe", "everything.exe",
}
# 全屏检测：这些进程名强制推迟（白名单=一定推迟，优先级高于尺寸判断）
FULLSCREEN_FORCE_DEFER = {
    "javaw.exe",   # Minecraft
}

MODES = {
    "常规": {"temp": 5000, "bright": 0.90, "icon": "○"},
    "办公": {"temp": 5500, "bright": 1.00, "icon": "□"},
    "游戏": {"temp": 6000, "bright": 1.00, "icon": "◈"},
    "阅读": {"temp": 4000, "bright": 0.80, "icon": "≡"},
    "睡眠": {"temp": 2500, "bright": 0.55, "icon": "◐"},
    "户外": {"temp": 6500, "bright": 1.00, "icon": "◉"},
}

# 24小时自动色温曲线
AUTO_CURVE = {
    0: 2700, 1: 2700, 2: 2700, 3: 2700, 4: 2700, 5: 3200,
    6: 4000, 7: 5000, 8: 5800, 9: 6200, 10: 6500, 11: 6500,
    12: 6500, 13: 6500, 14: 6500, 15: 6200, 16: 5800, 17: 5200,
    18: 4500, 19: 4000, 20: 3500, 21: 3200, 22: 3000, 23: 2700,
}

# ─────────────────────────────────────────────
# 🎨  系统主题色读取 (#10)
# ─────────────────────────────────────────────
def _read_system_accent() -> str:
    """读取 Windows 系统强调色，返回 #RRGGBB，失败时返回默认蓝。"""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Explorer\Accent"
        )
        # AccentColorMenu 是 ABGR 格式的 DWORD
        val, _ = winreg.QueryValueEx(key, "AccentColorMenu")
        winreg.CloseKey(key)
        b = (val >> 16) & 0xFF
        g = (val >>  8) & 0xFF
        r =  val        & 0xFF
        # 太暗的颜色（亮度 < 40）回退默认
        if (r * 299 + g * 587 + b * 114) // 1000 < 40:
            return "#0ea5e9"
        return f"#{r:02x}{g:02x}{b:02x}"
    except Exception:
        return "#0ea5e9"


# ─────────────────────────────────────────────
# 🔑  权限检测 (#2)
# ─────────────────────────────────────────────
def _is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


class DisplayManager:
    @staticmethod
    def _kelvin_to_rgb(temp_kelvin):
        t = temp_kelvin / 100
        if t <= 66:
            r = 255
            g = max(0.0, 99.47 * math.log(max(t, 1)) - 161.12)
        else:
            r = max(0.0, min(255.0, 329.7 * ((t - 60) ** -0.13)))
            g = max(0.0, min(255.0, 288.1 * ((t - 60) ** -0.07)))
        b = (255.0 if t >= 66 else
             0.0   if t <= 19 else
             max(0.0, min(255.0, 138.5 * math.log(t - 10) - 305.05)))
        return r / 255, g / 255, b / 255

    @staticmethod
    def _build_ramp(r, g, b):
        ramp = (ctypes.c_ushort * 256 * 3)()
        for i in range(256):
            base = i * 256
            ramp[0][i] = int(min(65535, r * base))
            ramp[1][i] = int(min(65535, g * base))
            ramp[2][i] = int(min(65535, b * base))
        return ramp

    @classmethod
    def apply(cls, temp_kelvin, brightness):
        r, g, b = cls._kelvin_to_rgb(temp_kelvin)
        r *= brightness; g *= brightness; b *= brightness
        ramp = cls._build_ramp(r, g, b)
        # 尝试多显示器
        applied = False
        try:
            monitors = []
            MONITORENUMPROC = ctypes.WINFUNCTYPE(
                ctypes.c_bool,
                ctypes.wintypes.HMONITOR, ctypes.wintypes.HDC,
                ctypes.POINTER(ctypes.wintypes.RECT), ctypes.wintypes.LPARAM
            )
            def _cb(hMon, hdcMon, lprcMon, dwData):
                monitors.append(hMon)
                return True
            cb = MONITORENUMPROC(_cb)
            ctypes.windll.user32.EnumDisplayMonitors(None, None, cb, 0)

            # MONITORINFOEX: cbSize(4) + rcMonitor(16) + rcWork(16) + dwFlags(4) + szDevice(64)
            class MONITORINFOEX(ctypes.Structure):
                _fields_ = [
                    ("cbSize", ctypes.wintypes.DWORD),
                    ("rcMonitor", ctypes.wintypes.RECT),
                    ("rcWork", ctypes.wintypes.RECT),
                    ("dwFlags", ctypes.wintypes.DWORD),
                    ("szDevice", ctypes.c_wchar * 32),
                ]

            for hMon in monitors:
                info = MONITORINFOEX()
                info.cbSize = ctypes.sizeof(MONITORINFOEX)
                ctypes.windll.user32.GetMonitorInfoW(hMon, ctypes.byref(info))
                hdc = ctypes.windll.gdi32.CreateDCW(info.szDevice, None, None, None)
                if hdc:
                    ctypes.windll.gdi32.SetDeviceGammaRamp(hdc, ctypes.byref(ramp))
                    ctypes.windll.gdi32.DeleteDC(hdc)
                    applied = True
        except Exception:
            pass
        # 降级：主屏
        if not applied:
            try:
                hdc = ctypes.windll.user32.GetDC(0)
                ctypes.windll.gdi32.SetDeviceGammaRamp(hdc, ctypes.byref(ramp))
            except Exception:
                pass

    @classmethod
    def reset(cls):
        cls.apply(6500, 1.0)


# ─────────────────────────────────────────────
# 🔁  SmoothTransition —— 平滑渐变
# ─────────────────────────────────────────────
class SmoothTransition(QObject):
    finished = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._step)
        self._cur_temp = 5000.0; self._cur_bright = 1.0
        self._tgt_temp = 5000.0; self._tgt_bright = 1.0
        self._steps = 1; self._done = 0

    def start(self, cur_temp, cur_bright, tgt_temp, tgt_bright,
              duration_ms=1500, step_ms=50):
        self._timer.stop()
        self._cur_temp = float(cur_temp); self._cur_bright = float(cur_bright)
        self._tgt_temp = float(tgt_temp); self._tgt_bright = float(tgt_bright)
        self._steps = max(1, duration_ms // step_ms)
        self._done = 0
        self._timer.start(step_ms)

    def _step(self):
        self._done += 1
        t = self._done / self._steps
        t_e = 1 - (1 - t) ** 3   # ease-out cubic
        temp   = self._cur_temp   + (self._tgt_temp   - self._cur_temp)   * t_e
        bright = self._cur_bright + (self._tgt_bright - self._cur_bright) * t_e
        DisplayManager.apply(temp, bright)
        if self._done >= self._steps:
            self._timer.stop()
            self.finished.emit()

    def stop(self):
        self._timer.stop()


# ─────────────────────────────────────────────
# 🖥  SuperDimOverlay —— 软件超暗遮罩（多屏版）(#5)
# ─────────────────────────────────────────────
class SuperDimOverlay(QWidget):
    """单屏超暗遮罩，鼠标穿透。由 DimManager 统一管理多实例。"""
    def __init__(self, screen_geometry):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint |
            Qt.Tool | Qt.WindowTransparentForInput
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self._alpha = 80
        self.setGeometry(screen_geometry)

    def set_alpha(self, alpha: int):
        self._alpha = max(0, min(200, alpha))
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(0, 0, 0, self._alpha))


class DimManager:
    """管理所有屏幕的超暗遮罩，支持热插拔。"""
    def __init__(self):
        self._overlays: list[SuperDimOverlay] = []
        self._alpha = 80
        self._active = False

    def show(self, alpha: int):
        self._active = True
        self._alpha = alpha
        self._rebuild()

    def hide(self):
        self._active = False
        for ov in self._overlays:
            ov.hide()

    def set_alpha(self, alpha: int):
        self._alpha = alpha
        for ov in self._overlays:
            ov.set_alpha(alpha)

    def rebuild(self):
        """屏幕数量变化时重建（热插拔）。"""
        if self._active:
            self._rebuild()

    def _rebuild(self):
        # 清除旧实例
        for ov in self._overlays:
            ov.close()
        self._overlays.clear()
        # 为每块屏幕创建独立遮罩
        for screen in QApplication.screens():
            ov = SuperDimOverlay(screen.geometry())
            ov.set_alpha(self._alpha)
            ov.show()
            self._overlays.append(ov)


# ─────────────────────────────────────────────
# 👁  EyeExerciseOverlay —— 视力训练窗口
#     #7: 关闭时停球定时器  #9: 前10秒锁定跳过
# ─────────────────────────────────────────────
class EyeExerciseOverlay(QWidget):
    def __init__(self, duration_secs=20, force_mode=False):
        super().__init__()
        self.total = duration_secs
        self.remaining = duration_secs
        self.force_mode = force_mode          # #9 强制模式
        self._lock_secs = 10 if force_mode else 0
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.showFullScreen()
        self._ball_angle = 0.0
        self._build_ui()
        self._cd = QTimer(self)
        self._cd.timeout.connect(self._tick)
        self._cd.start(1000)
        self._bt = QTimer(self)               # #7 球动画仅在窗口存在时运行
        self._bt.timeout.connect(self._move_ball)
        self._bt.start(16)

    @property
    def _cx(self): return self.width() // 2
    @property
    def _cy(self): return self.height() // 2
    @property
    def _rx(self): return min(320, self.width() // 3)
    @property
    def _ry(self): return min(160, self.height() // 5)

    @property
    def _ball_xy(self):
        x = self._cx + self._rx * math.cos(self._ball_angle)
        y = self._cy + self._ry * math.sin(self._ball_angle)
        return int(x), int(y)

    def _move_ball(self):
        self._ball_angle += 0.025
        bx, by = self._ball_xy
        self._ball.move(bx - 18, by - 18)

    def _build_ui(self):
        bg = QFrame(self)
        bg.setStyleSheet("background: rgba(2,8,20,215);")
        bg.setGeometry(self.rect())

        def lbl(text, style, parent=self):
            l = QLabel(text, parent)
            l.setStyleSheet(style)
            l.adjustSize()
            return l

        title = lbl("眼睛休息时间",
                    "color:#e2e8f0;font-size:44px;font-weight:800;letter-spacing:3px;")
        title.move(self._cx - title.width()//2, self._cy - 230)

        sub = lbl("请跟随小球缓慢转动眼球，放松睫状肌",
                  "color:#64748b;font-size:17px;")
        sub.move(self._cx - sub.width()//2, self._cy - 168)

        self._timer_lbl = lbl(str(self.remaining),
                              "color:#0ea5e9;font-size:72px;font-weight:900;")
        self._timer_lbl.move(self._cx - self._timer_lbl.width()//2, self._cy + 110)

        self._sec_lbl = lbl("秒后自动结束", "color:#475569;font-size:15px;")
        self._sec_lbl.move(self._cx - self._sec_lbl.width()//2, self._cy + 195)

        self._ball = QFrame(self)
        self._ball.setFixedSize(36, 36)
        self._ball.setStyleSheet("background:#0ea5e9;border-radius:18px;")
        eff = QGraphicsDropShadowEffect()
        eff.setBlurRadius(28); eff.setColor(QColor("#0ea5e9")); eff.setOffset(0, 0)
        self._ball.setGraphicsEffect(eff)

        # #9 跳过按钮 — 强制模式下前10秒禁用
        self._skip = QPushButton("跳过", self)
        self._skip.setFixedSize(100, 38)
        self._skip.setStyleSheet("""
            QPushButton {
                background:rgba(255,255,255,0.07); color:#64748b;
                border:1px solid rgba(255,255,255,0.1); border-radius:19px; font-size:14px;
            }
            QPushButton:hover { background:rgba(255,255,255,0.14); color:#e2e8f0; }
            QPushButton:disabled { color:#2d3748; border-color:rgba(255,255,255,0.04); }
        """)
        self._skip.move(self._cx - 50, self.height() - 80)
        self._skip.clicked.connect(self._close)
        if self.force_mode:
            self._skip.setEnabled(False)
            self._lock_lbl = lbl(f"强制休息中，{self._lock_secs}秒后可跳过",
                                 "color:#f97316;font-size:13px;")
            self._lock_lbl.move(self._cx - self._lock_lbl.width()//2, self.height() - 120)
        else:
            self._lock_lbl = None

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        pen = QPen(QColor(14, 165, 233, 28), 2, Qt.DashLine)
        p.setPen(pen)
        p.drawEllipse(self._cx - self._rx, self._cy - self._ry,
                      self._rx * 2, self._ry * 2)

    def _tick(self):
        self.remaining -= 1
        # #9 解锁逻辑
        if self.force_mode and self._lock_secs > 0:
            self._lock_secs -= 1
            if self._lock_secs <= 0:
                self._skip.setEnabled(True)
                if self._lock_lbl:
                    self._lock_lbl.setText("现在可以跳过")
            elif self._lock_lbl:
                self._lock_lbl.setText(f"强制休息中，{self._lock_secs}秒后可跳过")

        self._timer_lbl.setText(str(self.remaining))
        self._timer_lbl.adjustSize()
        self._timer_lbl.move(self._cx - self._timer_lbl.width()//2, self._cy + 110)
        if self.remaining <= 0:
            self._close()

    def _close(self):
        self._cd.stop()
        self._bt.stop()   # #7 确保球动画定时器停止
        self.close()


# ─────────────────────────────────────────────
# 🎨  自定义控件
# ─────────────────────────────────────────────
class AnimatedToggle(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setFixedSize(52, 26)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#0ea5e9") if self.isChecked() else QColor("#374151"))
        p.drawRoundedRect(0, 0, self.width(), self.height(), 13, 13)
        x = self.width() - 22 if self.isChecked() else 4
        p.setBrush(QColor("#ffffff"))
        p.drawEllipse(x, 3, 19, 19)


class RingProgress(QWidget):
    def __init__(self, size=110, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self._v = 0; self._sz = size

    def setValue(self, v):
        self._v = max(0, min(100, v)); self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        m = 7
        rect = QRect(m, m, self._sz - 2*m, self._sz - 2*m)
        p.setPen(Qt.NoPen); p.setBrush(QColor("#161b22"))
        p.drawEllipse(rect)
        pen = QPen(QColor("#0ea5e9"), 6, Qt.SolidLine, Qt.RoundCap)
        p.setPen(pen); p.setBrush(Qt.NoBrush)
        p.drawArc(rect, 90*16, int(-self._v * 360 / 100 * 16))
        p.setPen(QColor("#e6edf3"))
        p.setFont(QFont("Segoe UI", max(8, int(self._sz * 0.12)), QFont.Bold))
        p.drawText(rect, Qt.AlignCenter, f"{self._v}%")


class BarChart(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(110)
        self._data = [0]*7; self._labels = []

    def set_data(self, data, labels):
        self._data = data[-7:]; self._labels = labels[-7:]; self.update()

    def paintEvent(self, event):
        if not self._data: return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        n = len(self._data)
        bar_w  = max(10, (w - 20) // n - 6)
        spacing = (w - bar_w * n) // (n + 1)
        max_h  = h - 32
        max_val = max(480, max(self._data) if self._data else 1)
        for i, val in enumerate(self._data):
            x = spacing + i * (bar_w + spacing)
            bh = max(2, int(val / max_val * max_h))
            y  = max_h - bh + 4
            color = QColor("#0ea5e9") if i == n-1 else QColor("#1e4a6e")
            p.setPen(Qt.NoPen); p.setBrush(color)
            p.drawRoundedRect(x, y, bar_w, bh, 3, 3)
            p.setPen(QColor("#484f58"))
            p.setFont(QFont("Segoe UI", 9))
            lbl = self._labels[i] if i < len(self._labels) else ""
            p.drawText(x, h - 14, bar_w, 14, Qt.AlignCenter, lbl)


# ─────────────────────────────────────────────
# 📱  主应用
# ─────────────────────────────────────────────
# ─────────────────────────────────────────────
# 🐾  DesktopPet —— 护眼桌宠
# ─────────────────────────────────────────────
class DesktopPet(QWidget):
    """纯 QPainter 绘制的桌面宠物，无额外依赖。

    左键戳一下有反应，拖动移动并自动贴边；右键出菜单；
    外观跟随主程序状态：正常 / 快到休息 / 休息中 / 护眼关闭。
    """
    W, H = 150, 168
    BODY_TOP = 36

    # state: (主体色, 高光色, 肚皮色)
    PALETTE = {
        "idle":    ("#0ea5e9", "#38bdf8", "#e0f2fe"),
        "tired":   ("#f59e0b", "#fbbf24", "#fef3c7"),
        "resting": ("#6366f1", "#818cf8", "#e0e7ff"),
        "off":     ("#475569", "#64748b", "#e2e8f0"),
    }

    TIPS = {
        "idle":    ["今天也要好好护眼", "记得多眨眨眼", "坐直一点，别驼背",
                    "喝口水吧", "我在这儿陪着你", "看看远处，放松一下"],
        "tired":   ["快到休息时间啦", "眼睛有点酸了呢"],
        "resting": ["闭上眼睛，放松一会儿", "看看窗外的远处"],
        "off":     ["护眼已关闭，别熬太久"],
    }

    def __init__(self, open_app=None, hide_pet=None, quit_app=None,
                 rest_now=None, toggle_care=None, on_moved=None):
        super().__init__(None)
        self._open_app    = open_app
        self._hide_pet    = hide_pet
        self._quit_app    = quit_app
        self._rest_now    = rest_now
        self._toggle_care = toggle_care
        self._on_moved    = on_moved

        self._state = "idle"
        self._phase = 0.0
        self._blink = 0             # 剩余眨眼帧
        self._next_blink = 40
        self._squash = 0.0          # 被戳时的挤压动画
        self._drag_from = None
        self._dragged = False
        self._msg = ""
        self._tip_idx = 0
        self._left_secs = 0
        self._total_secs = 0
        self._look = (0.0, 0.0)     # 眼球偏移

        self.setFixedSize(self.W, self.H)
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint |
                            Qt.WindowStaysOnTopHint | Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip("左键戳一下 · 拖动移动 · 右键菜单")

        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._tick)
        self._anim_timer.start(60)
        self._msg_timer = QTimer(self)
        self._msg_timer.setSingleShot(True)
        self._msg_timer.timeout.connect(self._clear_msg)
        self._chat_timer = QTimer(self)          # 偶尔自己冒个泡
        self._chat_timer.timeout.connect(self._auto_chat)
        self._chat_timer.start(120_000)

    # ── 位置 ──────────────────────────────────
    def place(self, pos=None):
        """恢复上次的位置；没有记录或已越界则贴到右下角。"""
        if pos and len(pos) == 2 and self._on_any_screen(pos[0], pos[1]):
            self.move(int(pos[0]), int(pos[1]))
            return
        scr = QApplication.primaryScreen()
        if scr:
            a = scr.availableGeometry()
            self.move(a.right() - self.width() - 24, a.bottom() - self.height() - 8)

    @staticmethod
    def _on_any_screen(x, y) -> bool:
        probe = QRect(int(x), int(y), 48, 48)
        return any(s.availableGeometry().intersects(probe)
                   for s in QApplication.screens())

    def keep_on_screen(self):
        """显示器热插拔后把桌宠拉回可见区域。"""
        if not self._on_any_screen(self.x(), self.y()):
            self.place(None)

    def _snap_edge(self):
        """拖动结束后限制在屏幕内，靠近左右边缘时自动贴边。"""
        scr = QApplication.screenAt(self.geometry().center()) or QApplication.primaryScreen()
        if not scr:
            return
        a = scr.availableGeometry()
        x = min(max(self.x(), a.left()), a.right() - self.width())
        y = min(max(self.y(), a.top()), a.bottom() - self.height())
        if x - a.left() < 32:
            x = a.left()
        elif a.right() - (x + self.width()) < 32:
            x = a.right() - self.width()
        self.move(x, y)

    # ── 与主程序联动 ──────────────────────────
    def set_state(self, state: str):
        if state not in self.PALETTE or state == self._state:
            return
        self._state = state
        if state != "idle":
            self.say(self.TIPS[state][0], 5000)
        self.update()

    def set_countdown(self, left_secs: int, total_secs: int):
        self._left_secs = max(0, int(left_secs))
        self._total_secs = max(0, int(total_secs))
        m, s = divmod(self._left_secs, 60)
        self.setToolTip(f"距离下次休息 {m:02d}:{s:02d}\n"
                        f"左键戳一下 · 拖动移动 · 右键菜单")
        if self._total_secs:
            self.update()

    def say(self, text: str, ms: int = 3200):
        self._msg = text
        self._msg_timer.start(ms)
        self.update()

    def _clear_msg(self):
        self._msg = ""
        self.update()

    def _auto_chat(self):
        tips = self.TIPS.get(self._state, self.TIPS["idle"])
        self._tip_idx = (self._tip_idx + 1) % len(tips)
        self.say(tips[self._tip_idx])

    # ── 动画 ──────────────────────────────────
    def _tick(self):
        self._phase += 0.09
        if self._squash > 0:
            self._squash = max(0.0, self._squash - 0.1)
        if self._blink > 0:
            self._blink -= 1
        else:
            self._next_blink -= 1
            if self._next_blink <= 0:
                self._blink = 4
                self._next_blink = 45 + int(abs(math.sin(self._phase * 3)) * 45)
        # 眼球追随鼠标
        d = QCursor.pos() - self.geometry().center()
        self._look = (max(-3.0, min(3.0, d.x() / 55)),
                      max(-2.5, min(2.5, d.y() / 75)))
        self.update()

    # ── 绘制 ──────────────────────────────────
    def paintEvent(self, event):
        body, light, belly = self.PALETTE[self._state]
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        bob = math.sin(self._phase) * 3.0 + self._squash * 5
        top = self.BODY_TOP + bob
        p.setPen(Qt.NoPen)

        # 影子：跳得越高越小
        sw = 92 - int(bob * 2)
        p.setBrush(QColor(0, 0, 0, 70))
        p.drawEllipse(int(self.W / 2 - sw / 2), 142, sw, 12)

        # 尾巴（左右摆动）
        wag = math.sin(self._phase * 1.7) * 9
        p.setBrush(QColor(body))
        p.drawEllipse(int(106 + wag * 0.5), int(top + 60), 28, 13)

        # 耳朵
        p.setBrush(QColor(light))
        p.drawEllipse(25, int(top - 4), 30, 34)
        p.drawEllipse(95, int(top - 4), 30, 34)
        p.setBrush(QColor(belly))
        p.drawEllipse(33, int(top + 5), 13, 17)
        p.drawEllipse(103, int(top + 5), 13, 17)

        # 身体 + 肚皮 + 脚
        p.setBrush(QColor(body))
        p.drawRoundedRect(QRect(28, int(top + 8), 94, 90), 34, 34)
        p.setBrush(QColor(belly))
        p.drawEllipse(39, int(top + 22), 72, 62)
        p.setBrush(QColor(body).darker(112))
        p.drawEllipse(38, int(top + 84), 28, 15)
        p.drawEllipse(84, int(top + 84), 28, 15)

        self._paint_face(p, top)
        self._paint_bar(p)
        self._paint_bubble(p)

    def _paint_face(self, p, top):
        ink = QColor("#0f172a")
        ex, ey = self._look
        eye_y = top + 36
        if self._blink > 0 or self._state == "resting":
            p.setBrush(Qt.NoBrush)
            p.setPen(QPen(ink, 3, Qt.SolidLine, Qt.RoundCap))
            p.drawArc(50, int(eye_y + 4), 16, 12, 0, -180 * 16)
            p.drawArc(85, int(eye_y + 4), 16, 12, 0, -180 * 16)
        else:
            eh = 11 if self._state == "tired" else 17
            for cx in (50, 88):
                p.setPen(Qt.NoPen); p.setBrush(ink)
                p.drawEllipse(int(cx + ex), int(eye_y + ey), 13, eh)
                p.setBrush(QColor(255, 255, 255, 230))
                p.drawEllipse(int(cx + 3 + ex), int(eye_y + 3 + ey), 4, 5)
            if self._state == "tired":              # 半睁的上眼皮
                p.setBrush(Qt.NoBrush)
                p.setPen(QPen(ink, 3, Qt.SolidLine, Qt.RoundCap))
                p.drawLine(50, int(eye_y - 1), 63, int(eye_y - 2))
                p.drawLine(88, int(eye_y - 2), 101, int(eye_y - 1))
        # 腮红
        p.setPen(Qt.NoPen); p.setBrush(QColor(251, 113, 133, 140))
        p.drawEllipse(41, int(eye_y + 20), 13, 8)
        p.drawEllipse(96, int(eye_y + 20), 13, 8)
        # 嘴，休息时再冒两个 z
        p.setBrush(Qt.NoBrush); p.setPen(QPen(ink, 2, Qt.SolidLine, Qt.RoundCap))
        p.drawArc(68, int(eye_y + 18), 16, 12, 200 * 16, 140 * 16)
        if self._state == "resting":
            zf = QFont("Segoe UI"); zf.setPixelSize(13); zf.setBold(True)
            p.setFont(zf)
            p.setPen(QColor("#c7d2fe"))
            p.drawText(112, int(eye_y - 4 + math.sin(self._phase) * 2), "z")
            p.drawText(122, int(eye_y - 16 + math.sin(self._phase + 1.2) * 2), "z")

    def _paint_bar(self, p):
        """脚下的细进度条：距离下次休息的进度。"""
        if self._state == "off" or self._total_secs <= 0:
            return
        done = 1 - self._left_secs / self._total_secs
        bar = QRect(33, 157, 84, 5)
        p.setPen(Qt.NoPen); p.setBrush(QColor(255, 255, 255, 45))
        p.drawRoundedRect(bar, 3, 3)
        p.setBrush(QColor("#f59e0b") if self._left_secs <= 60 else QColor("#38bdf8"))
        p.drawRoundedRect(QRect(bar.x(), bar.y(),
                                max(4, int(bar.width() * max(0.0, min(1.0, done)))),
                                bar.height()), 3, 3)

    def _paint_bubble(self, p):
        if not self._msg:
            return
        box = QRect(2, 0, self.W - 4, 30)
        p.setBrush(QColor(1, 4, 9, 235)); p.setPen(QPen(QColor("#38bdf8"), 1))
        p.drawRoundedRect(box.adjusted(0, 1, 0, -2), 8, 8)
        # 用像素字号，避免不同 DPI 下文字撑破气泡
        f = QFont("Microsoft YaHei"); f.setPixelSize(12)
        p.setFont(f); p.setPen(QColor("#dbeafe"))
        inner = box.adjusted(6, 0, -6, -1)
        p.drawText(inner, Qt.AlignCenter,
                   QFontMetrics(f).elidedText(self._msg, Qt.ElideRight, inner.width()))

    # ── 交互 ──────────────────────────────────
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_from = event.globalPos() - self.frameGeometry().topLeft()
            self._dragged = False
            event.accept()
        elif event.button() == Qt.RightButton:
            self._show_menu(event.globalPos())
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_from is not None and event.buttons() & Qt.LeftButton:
            self.move(event.globalPos() - self._drag_from)
            self._dragged = True
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._drag_from is not None:
            self._drag_from = None
            if self._dragged:
                self._snap_edge()
                if self._on_moved:
                    self._on_moved(self.x(), self.y())
            else:
                self._poke()          # 只是戳了一下
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton and self._open_app:
            self._open_app()
        super().mouseDoubleClickEvent(event)

    def enterEvent(self, event):
        if self._total_secs and self._state != "off":
            m, s = divmod(self._left_secs, 60)
            self.say(f"距离休息还有 {m:02d}:{s:02d}", 2500)
        super().enterEvent(event)

    def _poke(self):
        self._squash = 1.0
        self._blink = 4
        self._auto_chat()

    def _show_menu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet("QMenu{background:#161b22;color:#c9d1d9;"
                           "border:1px solid #30363d;padding:4px;}"
                           "QMenu::item{padding:5px 24px 5px 14px;}"
                           "QMenu::item:selected{background:#21262d;}")
        acts = {}
        for label, cb in [("打开主界面", self._open_app),
                          ("立即休息一下", self._rest_now),
                          ("切换护眼", self._toggle_care),
                          (None, None),
                          ("藏起来", self._hide_pet),
                          ("退出程序", self._quit_app)]:
            if label is None:
                menu.addSeparator(); continue
            act = menu.addAction(label)
            act.setEnabled(cb is not None)
            acts[act] = cb
        cb = acts.get(menu.exec_(pos))
        if cb:
            cb()


class CareEyesApp(QWidget):
    hotkey_brightness = pyqtSignal(int)
    hotkey_temperature = pyqtSignal(int)
    hotkey_toggle = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._quitting = False
        self.overlay = None
        self.pet = None
        # ── 读取系统主题色 (#10) ──
        self._accent = _read_system_accent()

        # 默认状态
        self.temp = 5000; self.bright = 1.0
        self.is_enabled = True; self.auto_mode = False
        self.super_dim = False; self.super_dim_alpha = 80
        self.rest_interval_min = 45; self.rest_duration_sec = 20
        self.force_rest = False          # #9 强制休息
        self.autostart = False; self.sound_enabled = True
        self.pet_enabled = True
        self.pet_pos = None
        self.session_start = datetime.now()
        self.today_minutes = 0; self.break_count = 0
        self.week_data = {}
        self._next_rest_secs = self.rest_interval_min * 60
        self._warned_1min = False
        self._transition = SmoothTransition(self)
        self._dim_mgr = DimManager()     # #5 多屏超暗管理器

        self.hotkey_brightness.connect(self._hk_bright)
        self.hotkey_temperature.connect(self._hk_temp)
        self.hotkey_toggle.connect(self._hk_toggle)

        self.load_settings()
        self.init_ui()
        self.init_tray()
        self.init_pet()
        self.init_timers()
        self.init_hotkeys()
        self.apply_effect()

        # #2 权限检测：低权限时托盘提示
        if not _is_admin():
            QTimer.singleShot(2000, lambda: self.tray.showMessage(
                APP_TITLE,
                "当前以普通权限运行。若护眼对管理员进程无效，请右键以管理员身份运行。",
                QSystemTrayIcon.Warning, 6000
            ))

    # ══════════════════════════════════════════
    def init_timers(self):
        self.rest_timer = QTimer(self)
        self.rest_timer.timeout.connect(self._on_rest_trigger)
        self.rest_timer.start(self.rest_interval_min * 60 * 1000)

        # #1 守护频率提升至 800ms
        self.guard_timer = QTimer(self)
        self.guard_timer.timeout.connect(self._guard_apply)
        if self.is_enabled:
            self.guard_timer.start(800)

        self.stat_timer = QTimer(self)
        self.stat_timer.timeout.connect(self._update_stat)
        self.stat_timer.start(60_000)

        self.countdown_timer = QTimer(self)
        self.countdown_timer.timeout.connect(self._refresh_countdown)
        self.countdown_timer.start(1000)

        self.auto_timer = QTimer(self)
        self.auto_timer.timeout.connect(self._auto_mode_tick)
        self.auto_timer.start(60_000)

        # #3 多显示器热插拔监听
        QApplication.instance().primaryScreenChanged.connect(self._on_screen_change)
        try:
            QApplication.instance().screenAdded.connect(self._on_screen_change)
            QApplication.instance().screenRemoved.connect(self._on_screen_change)
        except Exception:
            pass

    # ══════════════════════════════════════════
    #  桌宠
    # ══════════════════════════════════════════
    def init_pet(self):
        self.pet = DesktopPet(
            open_app=self._open_main,
            hide_pet=lambda: self._on_pet_toggle(False),
            quit_app=self._quit_app,
            rest_now=self.show_rest_overlay,
            toggle_care=self._hk_toggle,
            on_moved=self._on_pet_moved,
        )
        self.pet.setVisible(False)
        self.pet.set_countdown(self._next_rest_secs, self.rest_interval_min * 60)
        if not self.is_enabled:
            self.pet.set_state("off")
        if self.pet_enabled:
            self._show_pet()

    def _show_pet(self):
        if self.pet is None:
            return
        if not self.pet.isVisible():
            self.pet.place(self.pet_pos)
            self.pet.show()
        self.pet.raise_()

    def _hide_pet(self):
        if self.pet is not None:
            self.pet.hide()

    def _open_main(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def _on_pet_moved(self, x, y):
        self.pet_pos = [int(x), int(y)]
        self._schedule_save()

    def _pet_state(self):
        """根据当前护眼/休息状态推导桌宠表情。"""
        if self.pet is None:
            return
        if not self.is_enabled:
            state = "off"
        elif self.overlay is not None and self.overlay.isVisible():
            state = "resting"
        elif self._next_rest_secs <= 60:
            state = "tired"
        else:
            state = "idle"
        self.pet.set_state(state)

    def _on_pet_toggle(self, state):
        self.pet_enabled = bool(state)
        if self.pet_enabled:
            self._show_pet()
        else:
            self._hide_pet()
        if hasattr(self, "pet_action"):
            self.pet_action.blockSignals(True)
            self.pet_action.setChecked(self.pet_enabled)
            self.pet_action.blockSignals(False)
        if hasattr(self, "pet_cb"):
            self.pet_cb.blockSignals(True)
            self.pet_cb.setChecked(self.pet_enabled)
            self.pet_cb.blockSignals(False)
        self._schedule_save()

    # ══════════════════════════════════════════
    def init_hotkeys(self):
        try:
            from pynput import keyboard as kb
            self._hk_pressed = set()

            def _on_press(key):
                try:
                    self._hk_pressed.add(key)
                    ctrl = {kb.Key.ctrl, kb.Key.ctrl_l, kb.Key.ctrl_r}
                    alt  = {kb.Key.alt,  kb.Key.alt_l,  kb.Key.alt_r}
                    if self._hk_pressed & ctrl and self._hk_pressed & alt:
                        if key == kb.Key.up:    self.hotkey_brightness.emit(+5)
                        elif key == kb.Key.down: self.hotkey_brightness.emit(-5)
                        elif key == kb.Key.right: self.hotkey_temperature.emit(+200)
                        elif key == kb.Key.left:  self.hotkey_temperature.emit(-200)
                        elif key == kb.Key.end:   self.hotkey_toggle.emit()
                except Exception: pass

            def _on_release(key):
                self._hk_pressed.discard(key)

            self._hk_listener = kb.Listener(
                on_press=_on_press, on_release=_on_release, daemon=True
            )
            self._hk_listener.start()
        except ImportError:
            pass

    def _hk_bright(self, d):
        self.bright_slider.setValue(max(30, min(100, int(self.bright*100)+d)))
    def _hk_temp(self, d):
        self.temp_slider.setValue(max(2000, min(8000, self.temp+d)))
    def _hk_toggle(self):
        self.toggle.setChecked(not self.toggle.isChecked())
        self.toggle_master()

    # ══════════════════════════════════════════
    #  UI
    # ══════════════════════════════════════════
    def init_ui(self):
        self.setWindowTitle(APP_TITLE)
        self.setMinimumSize(660, 460)
        self.resize(700, 500)
        self.setStyleSheet(self._qss())

        root = QVBoxLayout(self)
        root.setContentsMargins(0,0,0,0); root.setSpacing(0)
        root.addWidget(self._build_header())
        self.pages = QStackedWidget()
        for fn in [self._page_home, self._page_timer, self._page_stats, self._page_settings]:
            self.pages.addWidget(fn())
        root.addWidget(self.pages, 1)

    def _qss(self):
        ac = self._accent  # 系统强调色
        return f"""
        QWidget {{ background:#0d1117; color:#c9d1d9;
            font-family:'Segoe UI','Microsoft YaHei UI',sans-serif; font-size:13px; }}
        QSlider::groove:horizontal {{ height:5px; background:#21262d; border-radius:3px; }}
        QSlider::sub-page:horizontal {{
            background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 {ac},stop:1 #8b5cf6);
            border-radius:3px; }}
        QSlider::handle:horizontal {{
            background:#fff; width:16px; height:16px;
            margin:-6px 0; border-radius:8px; border:2px solid {ac}; }}
        QScrollBar:vertical {{ width:0; }}
        QSpinBox {{ background:#161b22; color:#c9d1d9; border:1px solid #30363d;
            border-radius:5px; padding:4px 8px; min-width:70px; }}
        QCheckBox {{ spacing:8px; }}
        QCheckBox::indicator {{ width:15px; height:15px; border-radius:4px;
            border:1px solid #30363d; background:#161b22; }}
        QCheckBox::indicator:checked {{ background:{ac}; border-color:{ac}; }}
        """

    def _card(self):
        f = QFrame()
        f.setStyleSheet("background:#161b22;border-radius:8px;border:1px solid #21262d;")
        return f

    def _h2(self, t):
        l = QLabel(t); l.setStyleSheet("font-size:18px;font-weight:700;color:#e6edf3;")
        return l

    def _caption(self, t):
        l = QLabel(t); l.setStyleSheet("color:#8b949e;font-size:11px;letter-spacing:1px;")
        return l

    def _div(self):
        f = QFrame(); f.setFrameShape(QFrame.HLine)
        f.setStyleSheet("background:#21262d;max-height:1px;border:none;")
        return f

    # ── 顶部紧凑导航 ──
    def _build_header(self):
        header = QFrame()
        header.setFixedHeight(58)
        header.setStyleSheet("background:#010409;border-bottom:1px solid #21262d;")
        lay = QHBoxLayout(header)
        lay.setContentsMargins(18,0,14,0); lay.setSpacing(4)

        brand = QLabel("◉  CareEyes")
        brand.setStyleSheet("color:#0ea5e9;font-size:14px;font-weight:700;")
        brand.setMinimumWidth(102)
        lay.addWidget(brand)

        self.nav_btns = []
        for label in ["护眼", "休息", "统计", "设置"]:
            btn = QPushButton(label)
            btn.setCheckable(True); btn.setFixedSize(66, 32)
            ac = self._accent
            btn.setStyleSheet(f"""
                QPushButton {{ border:none;border-radius:6px;color:#6e7681;
                    font-size:12px;background:transparent; }}
                QPushButton:hover {{ color:#8b949e;background:rgba(255,255,255,0.03); }}
                QPushButton:checked {{ color:{ac};background:rgba(14,165,233,0.07);
                    border:1px solid {ac}; }}
            """)
            btn.clicked.connect(lambda _,i=len(self.nav_btns): self._nav(i))
            self.nav_btns.append(btn); lay.addWidget(btn)

        self.nav_btns[0].setChecked(True)
        lay.addStretch()
        self.today_stat = QLabel("今日 — 分钟")
        self.today_stat.setStyleSheet("color:#484f58;font-size:11px;")
        lay.addWidget(self.today_stat)
        return header

    # ══════════════════════════════════════════
    #  Page 0
    # ══════════════════════════════════════════
    def _page_home(self):
        page = QWidget(); lay = QVBoxLayout(page)
        lay.setContentsMargins(24,20,24,20); lay.setSpacing(0)

        top = QHBoxLayout()
        top.addWidget(self._h2("护眼控制")); top.addStretch()
        self.toggle_label = QLabel("已开启" if self.is_enabled else "已关闭")
        self.toggle_label.setStyleSheet(
            f"color:{self._accent};margin-right:8px;" if self.is_enabled
            else "color:#484f58;margin-right:8px;")
        self.toggle = AnimatedToggle()
        self.toggle.setChecked(self.is_enabled); self.toggle.clicked.connect(self.toggle_master)
        top.addWidget(self.toggle_label); top.addWidget(self.toggle)
        lay.addLayout(top); lay.addSpacing(14)

        # 自动模式
        auto_row = QHBoxLayout()
        auto_row.addWidget(QLabel("◐  昼夜自动模式")); auto_row.addStretch()
        self.auto_status_lbl = QLabel("")
        self.auto_status_lbl.setStyleSheet("color:#8b5cf6;font-size:12px;margin-right:8px;")
        self.auto_toggle = AnimatedToggle()
        self.auto_toggle.setChecked(self.auto_mode)
        self.auto_toggle.clicked.connect(self._on_auto_toggle)
        auto_row.addWidget(self.auto_status_lbl); auto_row.addWidget(self.auto_toggle)
        lay.addLayout(auto_row); lay.addSpacing(16)

        # 模式按钮
        lay.addWidget(self._caption("预设模式")); lay.addSpacing(7)
        mode_row = QHBoxLayout(); mode_row.setSpacing(6)
        self.mode_btns = {}
        for name, info in MODES.items():
            btn = QPushButton(f"{info['icon']}  {name}")
            btn.setFixedHeight(40)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            btn.setStyleSheet(self._mode_qss(False))
            btn.clicked.connect(lambda _,n=name: self.apply_preset(n))
            self.mode_btns[name] = btn; mode_row.addWidget(btn)
        lay.addLayout(mode_row); lay.addSpacing(14)

        # 滑条卡片
        card = self._card(); cl = QVBoxLayout(card)
        cl.setContentsMargins(20,15,20,15); cl.setSpacing(12)

        tr = QHBoxLayout()
        tr.addWidget(QLabel("◐  蓝光/色温"))
        self.temp_val = QLabel(f"{self.temp} K")
        self.temp_val.setStyleSheet("color:#0ea5e9;min-width:60px;")
        self.temp_slider = QSlider(Qt.Horizontal)
        self.temp_slider.setRange(2000,8000); self.temp_slider.setValue(self.temp)
        self.temp_slider.valueChanged.connect(self.on_slider_change)
        tr.addWidget(self.temp_slider); tr.addWidget(self.temp_val)
        cl.addLayout(tr); cl.addWidget(self._div())

        br = QHBoxLayout()
        br.addWidget(QLabel("○  屏幕亮度"))
        self.bright_val = QLabel(f"{int(self.bright*100)}%")
        self.bright_val.setStyleSheet("color:#0ea5e9;min-width:60px;")
        self.bright_slider = QSlider(Qt.Horizontal)
        self.bright_slider.setRange(30,100); self.bright_slider.setValue(int(self.bright*100))
        self.bright_slider.valueChanged.connect(self.on_slider_change)
        br.addWidget(self.bright_slider); br.addWidget(self.bright_val)
        cl.addLayout(br); cl.addWidget(self._div())

        # 超暗模式
        dim_row = QHBoxLayout()
        dim_row.addWidget(QLabel("□  超暗模式"))
        self.dim_toggle = AnimatedToggle()
        self.dim_toggle.setChecked(self.super_dim)
        self.dim_toggle.clicked.connect(self._on_dim_toggle)
        dim_row.addWidget(self.dim_toggle)
        dim_row.addSpacing(12)
        dim_row.addWidget(QLabel("强度"))
        dim_row.addSpacing(6)
        self.dim_slider = QSlider(Qt.Horizontal)
        self.dim_slider.setRange(20, 200)
        self.dim_slider.setValue(self.super_dim_alpha)
        self.dim_slider.setEnabled(self.super_dim)
        self.dim_slider.setMinimumWidth(120)
        self.dim_slider.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.dim_slider.valueChanged.connect(self._on_dim_alpha)
        dim_row.addWidget(self.dim_slider, 1)
        cl.addLayout(dim_row)

        lay.addWidget(card); lay.addStretch()
        return page

    def _mode_qss(self, active):
        if active:
            return ("QPushButton{background:qlineargradient(x1:0,y1:0,x2:1,y2:1,"
                    "stop:0 #0ea5e9,stop:1 #8b5cf6);color:#fff;border-radius:8px;"
                    "border:none;font-size:13px;font-weight:600;}")
        return ("QPushButton{background:#161b22;color:#8b949e;border-radius:8px;"
                "border:1px solid #30363d;font-size:13px;}"
                "QPushButton:hover{background:#1c2128;color:#e6edf3;}")

    # ══════════════════════════════════════════
    #  Page 1
    # ══════════════════════════════════════════
    def _page_timer(self):
        page = QWidget(); lay = QVBoxLayout(page)
        lay.setContentsMargins(24,20,24,20); lay.setSpacing(12)
        lay.addWidget(self._h2("休息提醒"))

        card = self._card(); cl = QVBoxLayout(card)
        cl.setContentsMargins(22,16,22,16)
        cl.addWidget(self._caption("距下次休息"))
        self.next_rest_label = QLabel("45:00")
        self.next_rest_label.setStyleSheet(
            "color:#0ea5e9;font-size:40px;font-weight:900;")
        cl.addWidget(self.next_rest_label)
        self.fullscreen_warn = QLabel("")
        self.fullscreen_warn.setStyleSheet("color:#f97316;font-size:12px;")
        cl.addWidget(self.fullscreen_warn)
        lay.addWidget(card)

        scard = self._card(); sl = QVBoxLayout(scard)
        sl.setContentsMargins(22,15,22,15); sl.setSpacing(10)
        lbl = QLabel("间隔设置"); lbl.setStyleSheet("color:#e6edf3;font-weight:600;")
        sl.addWidget(lbl)
        for row_lbl, attr, lo, hi, val in [
            ("工作时长（分钟）","interval_spin",5,120,self.rest_interval_min),
            ("休息时长（秒）",  "duration_spin",10,300,self.rest_duration_sec),
        ]:
            row = QHBoxLayout(); row.addWidget(QLabel(row_lbl))
            spin = QSpinBox(); spin.setRange(lo,hi); spin.setValue(val)
            setattr(self,attr,spin); row.addStretch(); row.addWidget(spin)
            sl.addLayout(row); sl.addWidget(self._div())

        ab = QPushButton("应用"); ab.setFixedHeight(33)
        ab.setStyleSheet("QPushButton{background:#0ea5e9;color:#fff;border-radius:7px;"
                         "font-weight:600;border:none;}"
                         "QPushButton:hover{background:#38bdf8;}")
        ab.clicked.connect(self.apply_timer_settings); sl.addWidget(ab)
        lay.addWidget(scard)

        tb = QPushButton("◉  立即测试"); tb.setFixedHeight(36)
        tb.setStyleSheet("QPushButton{background:#161b22;color:#8b949e;"
                         "border:1px solid #30363d;border-radius:8px;}"
                         "QPushButton:hover{color:#e6edf3;border-color:#0ea5e9;}")
        tb.clicked.connect(self.show_rest_overlay); lay.addWidget(tb)
        lay.addStretch()
        return page

    # ══════════════════════════════════════════
    #  Page 2
    # ══════════════════════════════════════════
    def _page_stats(self):
        page = QWidget(); lay = QVBoxLayout(page)
        lay.setContentsMargins(24,20,24,20); lay.setSpacing(12)
        lay.addWidget(self._h2("用眼统计"))

        cr = QHBoxLayout(); cr.setSpacing(10)
        for lbl_t, attr, unit, color in [
            ("今日用眼","stat_today","分钟","#0ea5e9"),
            ("本次连续","stat_session","分钟","#8b5cf6"),
            ("已休息",  "stat_breaks","次","#10b981"),
        ]:
            f = QFrame()
            f.setStyleSheet(f"background:#161b22;border-radius:10px;"
                            f"border-left:3px solid {color};border:1px solid #21262d;")
            fl = QVBoxLayout(f); fl.setContentsMargins(14,11,14,11)
            fl.addWidget(self._caption(lbl_t))
            val = QLabel("0"); val.setStyleSheet(f"color:{color};font-size:26px;font-weight:800;")
            setattr(self,attr,val); fl.addWidget(val)
            u = QLabel(unit); u.setStyleSheet("color:#484f58;font-size:11px;")
            fl.addWidget(u); cr.addWidget(f)
        lay.addLayout(cr)

        bot = QHBoxLayout(); bot.setSpacing(12)
        rc = self._card(); rl = QHBoxLayout(rc)
        rl.setContentsMargins(16,13,16,13)
        self.day_ring = RingProgress(100); rl.addWidget(self.day_ring)
        ri = QVBoxLayout()
        ri_lbl = QLabel("今日用眼目标"); ri_lbl.setStyleSheet("color:#484f58;font-size:11px;")
        ri.addWidget(ri_lbl)
        self.ring_sub = QLabel("≤ 480 分钟"); self.ring_sub.setStyleSheet("color:#484f58;font-size:11px;")
        ri.addWidget(self.ring_sub); ri.addStretch(); rl.addLayout(ri)
        bot.addWidget(rc, 1)

        cc = self._card(); cht = QVBoxLayout(cc)
        cht.setContentsMargins(14,11,14,11)
        cht.addWidget(self._caption("近7天用眼 (分钟)"))
        self.bar_chart = BarChart(); cht.addWidget(self.bar_chart)
        bot.addWidget(cc, 2)
        lay.addLayout(bot); lay.addStretch()
        return page

    # ══════════════════════════════════════════
    #  Page 3
    # ══════════════════════════════════════════
    def _page_settings(self):
        page = QWidget(); lay = QVBoxLayout(page)
        lay.setContentsMargins(24,20,24,20); lay.setSpacing(12)
        lay.addWidget(self._h2("设置"))

        card = self._card(); cl = QVBoxLayout(card)
        cl.setContentsMargins(22,15,22,15); cl.setSpacing(10)

        for row_lbl, attr, default in [
            ("开机自动启动","autostart_cb",self.autostart),
            ("声音提示",   "sound_cb",    self.sound_enabled),
            ("桌面宠物",   "pet_cb",      self.pet_enabled),
            ("强制休息（前10秒锁定跳过）","force_rest_cb", self.force_rest),
        ]:
            row = QHBoxLayout(); row.addWidget(QLabel(row_lbl))
            cb = QCheckBox(); cb.setChecked(default)
            setattr(self,attr,cb); row.addStretch(); row.addWidget(cb)
            cl.addLayout(row); cl.addWidget(self._div())

        self.autostart_cb.stateChanged.connect(self._on_autostart_change)
        self.sound_cb.stateChanged.connect(self._on_sound_toggle)
        self.pet_cb.stateChanged.connect(self._on_pet_toggle)
        self.force_rest_cb.stateChanged.connect(self._on_force_rest_toggle)

        hk = QLabel("全局快捷键\n"
                    "Ctrl+Alt+↑/↓  亮度 ±5%\n"
                    "Ctrl+Alt+←/→  色温 ±200K\n"
                    "Ctrl+Alt+End   开关护眼")
        hk.setStyleSheet("color:#484f58;font-size:11px;line-height:1.8;")
        cl.addWidget(hk)
        lay.addWidget(card)

        ic = self._card(); il = QVBoxLayout(ic)
        il.setContentsMargins(22,13,22,13)
        for k,v in [("版本",APP_VER),("配置文件",CONFIG_FILE)]:
            row = QHBoxLayout()
            kl=QLabel(k); kl.setStyleSheet("color:#484f58;")
            vl=QLabel(v); vl.setStyleSheet("color:#8b949e;")
            row.addWidget(kl); row.addStretch(); row.addWidget(vl)
            il.addLayout(row)
        lay.addWidget(ic)

        rb = QPushButton("◯  重置所有设置"); rb.setFixedHeight(35)
        rb.setStyleSheet("QPushButton{background:transparent;color:#f85149;"
                         "border:1px solid #f85149;border-radius:8px;}"
                         "QPushButton:hover{background:rgba(248,81,73,0.1);}")
        rb.clicked.connect(self._reset_settings); lay.addWidget(rb)
        lay.addStretch()
        return page

    # ══════════════════════════════════════════
    #  托盘
    # ══════════════════════════════════════════
    def init_tray(self):
        px = QPixmap(32,32); px.fill(Qt.transparent)
        p = QPainter(px); p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen); p.setBrush(QColor("#0ea5e9"))
        p.drawEllipse(2,2,28,28); p.setBrush(QColor("#010409"))
        p.drawEllipse(9,9,14,14); p.end()
        self.tray = QSystemTrayIcon(QIcon(px),self)
        menu = QMenu()
        menu.setStyleSheet("QMenu{background:#161b22;color:#c9d1d9;border:1px solid #30363d;padding:4px;}"
                           "QMenu::item:selected{background:#21262d;}")
        for label,slot in [("显示主界面",self._open_main),("切换护眼",self._hk_toggle),
                            (None,None),("退出",self._quit_app)]:
            if label is None: menu.addSeparator()
            else:
                a=QAction(label,self); a.triggered.connect(slot); menu.addAction(a)
        # 桌宠开关（与设置页复选框同步）
        self.pet_action = QAction("显示桌宠", self, checkable=True)
        self.pet_action.setChecked(self.pet_enabled)
        self.pet_action.toggled.connect(self._on_pet_toggle)
        menu.insertAction(menu.actions()[2], self.pet_action)
        self.tray.setContextMenu(menu)
        self.tray.setToolTip(f"{APP_TITLE} — 运行中")
        self.tray.activated.connect(lambda r: self._open_main() if r==QSystemTrayIcon.DoubleClick else None)
        self.tray.show()

    def _quit_app(self):
        self._quitting = True
        self._save_settings()
        self._dim_mgr.hide()
        if self.pet is not None:
            self.pet.close()
        if hasattr(self, "_hk_listener"):
            self._hk_listener.stop()
        DisplayManager.reset()
        QApplication.quit()

    # ══════════════════════════════════════════
    #  电源事件（休眠唤醒）
    # ══════════════════════════════════════════
    def nativeEvent(self, event_type, message):
        WM_SETTINGCHANGE      = 0x001A
        WM_DISPLAYCHANGE      = 0x007E
        WM_POWERBROADCAST     = 0x0218
        PBT_APMRESUMESUSPEND  = 0x0007
        try:
            msg = ctypes.cast(int(message), ctypes.POINTER(ctypes.wintypes.MSG)).contents
            if msg.message in (WM_SETTINGCHANGE, WM_DISPLAYCHANGE):
                # #1 系统设置/分辨率变化 → 立即重应用
                QTimer.singleShot(300, self.apply_effect)
                # #3 屏幕布局变化 → 重建超暗遮罩
                QTimer.singleShot(400, self._on_screen_change)
            elif msg.message == WM_POWERBROADCAST and msg.wParam == PBT_APMRESUMESUSPEND:
                QTimer.singleShot(2500, self.apply_effect)
        except Exception:
            pass
        return False, 0

    # ══════════════════════════════════════════
    #  逻辑
    # ══════════════════════════════════════════
    def _nav(self, idx):
        for i,btn in enumerate(self.nav_btns): btn.setChecked(i==idx)
        self.pages.setCurrentIndex(idx)
        if idx == 2: self._refresh_stats()

    def on_slider_change(self):
        self.temp = self.temp_slider.value()
        self.bright = self.bright_slider.value() / 100
        self.temp_val.setText(f"{self.temp} K")
        self.bright_val.setText(f"{int(self.bright*100)}%")
        self._transition.stop(); self.apply_effect()
        self._schedule_save()

    def apply_preset(self, name):
        p = MODES[name]
        for n,btn in self.mode_btns.items(): btn.setStyleSheet(self._mode_qss(n==name))
        self._transition.start(self.temp, self.bright, p['temp'], p['bright'], 1500)
        self.temp = p['temp']; self.bright = p['bright']
        for sl,val in [(self.temp_slider,self.temp),(self.bright_slider,int(self.bright*100))]:
            sl.blockSignals(True); sl.setValue(val); sl.blockSignals(False)
        self.temp_val.setText(f"{self.temp} K")
        self.bright_val.setText(f"{int(self.bright*100)}%")
        self._save_settings()

    def toggle_master(self):
        self.is_enabled = self.toggle.isChecked()
        if self.is_enabled:
            self.toggle_label.setText("已开启")
            self.toggle_label.setStyleSheet(f"color:{self._accent};margin-right:8px;")
            self.apply_effect()
            if not self.guard_timer.isActive():   # #7 重新启动守护
                self.guard_timer.start(800)
        else:
            self.toggle_label.setText("已关闭")
            self.toggle_label.setStyleSheet("color:#484f58;margin-right:8px;")
            self._transition.stop()
            self.guard_timer.stop()               # #7 停止守护节省 CPU
            DisplayManager.reset()
        self._pet_state()
        self._save_settings()

    def apply_effect(self):
        if self.is_enabled: DisplayManager.apply(self.temp, self.bright)

    def _guard_apply(self):
        if self.is_enabled and not self._transition._timer.isActive():
            DisplayManager.apply(self.temp, self.bright)

    def apply_timer_settings(self):
        self.rest_interval_min = self.interval_spin.value()
        self.rest_duration_sec = self.duration_spin.value()
        self._next_rest_secs = self.rest_interval_min * 60
        self._warned_1min = False
        self.rest_timer.stop()
        self.rest_timer.start(self.rest_interval_min * 60 * 1000)
        self._save_settings()

    def _on_rest_trigger(self):
        if self._is_fullscreen():
            self.fullscreen_warn.setText("⚠ 检测到全屏应用，休息提醒已推迟")
            self.tray.showMessage(APP_TITLE,"检测到全屏，休息已推迟5分钟",
                                  QSystemTrayIcon.Information,3000)
            QTimer.singleShot(5*60*1000, self._on_rest_trigger); return
        self.fullscreen_warn.setText("")
        self.show_rest_overlay()

    def show_rest_overlay(self):
        if self.overlay is not None and self.overlay.isVisible():
            self.overlay.raise_()
            return
        self.overlay = EyeExerciseOverlay(self.rest_duration_sec,
                                          force_mode=self.force_rest)
        self.overlay.destroyed.connect(lambda: setattr(self, "overlay", None))
        self.overlay.show()
        self._next_rest_secs = self.rest_interval_min * 60
        self._warned_1min = False; self.break_count += 1
        if self.pet is not None:
            self.pet.set_countdown(self._next_rest_secs, self.rest_interval_min * 60)
            self.pet.set_state("resting")

    def _refresh_countdown(self):
        self._next_rest_secs = max(0, self._next_rest_secs-1)
        m = self._next_rest_secs//60; s = self._next_rest_secs%60
        self.next_rest_label.setText(f"{m:02d}:{s:02d}")
        if self.pet is not None:
            self.pet.set_countdown(self._next_rest_secs,
                                   self.rest_interval_min*60)
            self._pet_state()
        if self._next_rest_secs == 60 and not self._warned_1min:
            self._warned_1min = True
            self.tray.showMessage(APP_TITLE,"还有 1 分钟就该休息了 ☕",
                                  QSystemTrayIcon.Information,5000)
            if self.pet is not None:
                self.pet.say("还有 1 分钟就休息啦", 6000)

    def _update_stat(self):
        today_str = date.today().isoformat()
        if getattr(self, "_stat_date", today_str) != today_str:
            self.today_minutes = 0
            self.break_count = 0
            self.session_start = datetime.now()
            self._stat_date = today_str
        if self.is_enabled: self.today_minutes += 1
        self.week_data[today_str] = self.today_minutes
        self.today_stat.setText(f"今日 {self.today_minutes} 分钟")
        self.today_stat.setStyleSheet("color:#6e7681;font-size:11px;")

    def _refresh_stats(self):
        sess = int((datetime.now()-self.session_start).total_seconds()/60)
        self.stat_today.setText(str(self.today_minutes))
        self.stat_session.setText(str(sess))
        self.stat_breaks.setText(str(self.break_count))
        self.day_ring.setValue(min(100,int(self.today_minutes/480*100)))
        today = date.today()
        days,vals = [],[]
        for i in range(6,-1,-1):
            d = today - timedelta(days=i)
            days.append(d.strftime("%m/%d")); vals.append(self.week_data.get(d.isoformat(),0))
        self.bar_chart.set_data(vals,days)

    def _on_auto_toggle(self):
        self.auto_mode = self.auto_toggle.isChecked()
        if self.auto_mode: self._auto_mode_tick()
        else: self.auto_status_lbl.setText("")
        self._schedule_save()

    def _auto_mode_tick(self):
        if not self.auto_mode or not self.is_enabled: return
        h = datetime.now().hour; m = datetime.now().minute
        t0 = AUTO_CURVE[h]; t1 = AUTO_CURVE[(h+1)%24]
        target = int(t0 + (t1-t0)*m/60)
        self.auto_status_lbl.setText(f"自动 {target}K")
        if abs(target-self.temp) > 50:
            self._transition.start(self.temp,self.bright,target,self.bright,3000)
            self.temp = target
            self.temp_slider.blockSignals(True); self.temp_slider.setValue(target)
            self.temp_slider.blockSignals(False); self.temp_val.setText(f"{target} K")

    def _on_dim_toggle(self):
        self.super_dim = self.dim_toggle.isChecked()
        self.dim_slider.setEnabled(self.super_dim)
        if self.super_dim:
            self._dim_mgr.show(self.super_dim_alpha)
        else:
            self._dim_mgr.hide()
        self._schedule_save()

    def _on_dim_alpha(self, val):
        self.super_dim_alpha = val
        if self.super_dim:
            self._dim_mgr.set_alpha(val)
        self._schedule_save()

    def _is_fullscreen(self) -> bool:
        """全屏检测：带进程名黑白名单，过滤伪全屏进程。(#4)"""
        try:
            import ctypes.wintypes as wt
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            if not hwnd:
                return False

            # 获取进程名
            pid = ctypes.wintypes.DWORD()
            ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            hproc = ctypes.windll.kernel32.OpenProcess(0x0410, False, pid.value)
            proc_name = ""
            if hproc:
                buf = ctypes.create_unicode_buffer(260)
                ctypes.windll.psapi.GetModuleBaseNameW(hproc, None, buf, 260)
                ctypes.windll.kernel32.CloseHandle(hproc)
                proc_name = buf.value.lower()

            # 白名单：强制推迟
            if proc_name in FULLSCREEN_FORCE_DEFER:
                return True
            # 黑名单：忽略（不推迟）
            if proc_name in FULLSCREEN_WHITELIST:
                return False

            # 尺寸判断
            rect = wt.RECT()
            ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
            scr = QApplication.primaryScreen().geometry()
            return (rect.right - rect.left >= scr.width() and
                    rect.bottom - rect.top >= scr.height())
        except Exception:
            return False

    def _on_screen_change(self, *args):
        """显示器热插拔：重应用 Gamma + 重建超暗遮罩。(#3)"""
        self.apply_effect()
        if self.super_dim:
            self._dim_mgr.rebuild()
        if self.pet is not None and self.pet.isVisible():
            self.pet.keep_on_screen()

    def _on_autostart_change(self, state):
        self.autostart = bool(state); self._set_autostart(self.autostart); self._save_settings()

    def _on_sound_toggle(self, state):
        self.sound_enabled = bool(state)
        self._schedule_save()

    def _on_force_rest_toggle(self, state):
        self.force_rest = bool(state)
        self._schedule_save()

    def _set_autostart(self, enabled):
        path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,path,0,winreg.KEY_SET_VALUE)
            if enabled:
                app_path = os.path.realpath(sys.argv[0])
                winreg.SetValueEx(key,APP_NAME,0,winreg.REG_SZ,f'"{app_path}"')
            else:
                try: winreg.DeleteValue(key,APP_NAME)
                except FileNotFoundError: pass
            winreg.CloseKey(key)
        except Exception: pass

    def _read_autostart(self):
        path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,path)
            winreg.QueryValueEx(key,APP_NAME); winreg.CloseKey(key); return True
        except Exception: return False

    def _reset_settings(self):
        self.temp=5000; self.bright=1.0
        self.rest_interval_min=45; self.rest_duration_sec=20
        self.auto_mode=False; self.super_dim=False; self.super_dim_alpha=80
        self.force_rest=False; self.sound_enabled=True
        self.temp_slider.setValue(5000); self.bright_slider.setValue(100)
        self.interval_spin.setValue(45); self.duration_spin.setValue(20)
        self.auto_toggle.setChecked(False)
        self.dim_toggle.setChecked(False); self.dim_slider.setValue(80); self.dim_slider.setEnabled(False)
        self.force_rest_cb.setChecked(False); self.sound_cb.setChecked(True)
        self._dim_mgr.hide()
        self._next_rest_secs = self.rest_interval_min * 60
        self._warned_1min = False
        self.pet_pos = None                 # 桌宠回到右下角默认位置
        self._hide_pet(); self._on_pet_toggle(True)
        self.apply_effect()
        self._save_settings()

    # ══════════════════════════════════════════
    #  持久化
    # ══════════════════════════════════════════
    _DEFAULTS = {
        "temp":5000,"bright":1.0,"is_enabled":True,"rest_interval":45,"rest_duration":20,
        "force_rest":False,
        "auto_mode":False,"autostart":False,"super_dim":False,"super_dim_alpha":80,
        "sound_enabled":True,"stat_date":"","today_minutes":0,"week_data":{},
        "pet_enabled":True,"pet_pos":[],
    }

    def load_settings(self):
        cfg = dict(self._DEFAULTS)
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE,"r",encoding="utf-8") as f:
                    raw = json.load(f)
                for k,dv in self._DEFAULTS.items():
                    v = raw.get(k,dv)
                    if not isinstance(v,type(dv)): v=dv
                    cfg[k] = v
            except Exception:
                pass  # 文件损坏 → 静默使用默认值
        self.temp=max(2000, min(8000, int(cfg["temp"])))
        self.bright=max(0.30, min(1.0, float(cfg["bright"])))
        self.is_enabled=cfg["is_enabled"]
        self.rest_interval_min=max(5, min(120, int(cfg["rest_interval"])))
        self.rest_duration_sec=max(10, min(300, int(cfg["rest_duration"])))
        self.force_rest=cfg["force_rest"]
        self.auto_mode=cfg["auto_mode"]; self.super_dim=cfg["super_dim"]
        self.super_dim_alpha=max(20, min(200, int(cfg["super_dim_alpha"])))
        self.sound_enabled=cfg["sound_enabled"]
        self.pet_enabled=cfg["pet_enabled"]
        pos=cfg["pet_pos"]
        self.pet_pos=([int(pos[0]), int(pos[1])]
                      if len(pos)==2 and all(isinstance(v,(int,float)) for v in pos)
                      else None)
        self.week_data={str(k): max(0, int(v)) for k,v in cfg["week_data"].items()
                        if isinstance(k, str) and isinstance(v, (int, float))}
        self._next_rest_secs=self.rest_interval_min*60
        today=date.today().isoformat()
        self._stat_date=today
        self.today_minutes=cfg["today_minutes"] if cfg["stat_date"]==today else 0
        self.autostart=self._read_autostart()

    def _save_settings(self):
        """原子写入：先写 .tmp 再 os.replace，防断电损坏。(#6)"""
        today=date.today().isoformat(); self.week_data[today]=self.today_minutes
        data={
            "temp":self.temp,"bright":self.bright,"is_enabled":self.is_enabled,
            "rest_interval":self.rest_interval_min,"rest_duration":self.rest_duration_sec,
            "force_rest":self.force_rest,
            "auto_mode":self.auto_mode,"super_dim":self.super_dim,
            "super_dim_alpha":self.super_dim_alpha,"sound_enabled":self.sound_enabled,
            "stat_date":today,"today_minutes":self.today_minutes,"week_data":self.week_data,
            "pet_enabled":self.pet_enabled,"pet_pos":self.pet_pos or [],
        }
        tmp = CONFIG_FILE + ".tmp"
        try:
            with open(tmp,"w",encoding="utf-8") as f:
                json.dump(data,f,ensure_ascii=False,indent=2)
            os.replace(tmp, CONFIG_FILE)   # 原子替换
        except Exception:
            try: os.remove(tmp)
            except Exception: pass

    def _schedule_save(self):
        if not hasattr(self, "_save_timer"):
            self._save_timer = QTimer(self)
            self._save_timer.setSingleShot(True)
            self._save_timer.timeout.connect(self._save_settings)
        self._save_timer.start(500)

    def closeEvent(self, event):
        if not self._quitting:
            self._save_settings()
            self.hide()
            event.ignore()
            return
        self._save_settings()
        self._dim_mgr.hide()
        if self.pet is not None:
            self.pet.close()
        DisplayManager.reset()
        super().closeEvent(event)


# ─────────────────────────────────────────────
# 🚀  入口
# ─────────────────────────────────────────────
if __name__ == "__main__":
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps,    True)
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setQuitOnLastWindowClosed(False)
    window = CareEyesApp()
    window.show()
    sys.exit(app.exec_())
