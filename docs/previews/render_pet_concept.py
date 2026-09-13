import math
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", str(Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"))

from PyQt5.QtCore import QPointF, QRectF, Qt
from PyQt5.QtGui import (
    QColor, QFont, QFontDatabase, QGuiApplication, QImage, QLinearGradient, QPainter,
    QPainterPath, QPen, QPolygonF, QRadialGradient,
)


WIDTH = 1680
HEIGHT = 1120
INK = "#edf4ff"
MUTED = "#8295ac"
ACCENT = "#60d8ce"


def box(painter, left, top, width, height, fill, radius=18, stroke=None):
    painter.setPen(QPen(QColor(stroke), 1.2) if stroke else Qt.NoPen)
    painter.setBrush(QColor(fill) if isinstance(fill, str) else fill)
    painter.drawRoundedRect(QRectF(left, top, width, height), radius, radius)


def ellipse(painter, left, top, width, height, fill, stroke=None):
    painter.setPen(QPen(QColor(stroke), 1.2) if stroke else Qt.NoPen)
    painter.setBrush(QColor(fill) if isinstance(fill, str) else fill)
    painter.drawEllipse(QRectF(left, top, width, height))


def text(painter, left, top, width, height, content, size=18,
         color=INK, weight=QFont.Normal, align=Qt.AlignLeft):
    font = QFont("Microsoft YaHei UI")
    font.setPixelSize(size)
    font.setWeight(weight)
    painter.setFont(font)
    painter.setPen(QColor(color))
    painter.drawText(QRectF(left, top, width, height),
                     align | Qt.AlignVCenter, content)


def shape(painter, path, fill, stroke=None, stroke_width=1.5):
    painter.setPen(QPen(QColor(stroke), stroke_width,
                        Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
                   if stroke else Qt.NoPen)
    painter.setBrush(QColor(fill) if isinstance(fill, str) else fill)
    painter.drawPath(path)


def curve(painter, coordinates, color, width=2.0):
    path = QPainterPath(QPointF(*coordinates[0]))
    for segment in coordinates[1:]:
        if len(segment) == 6:
            path.cubicTo(*segment)
        else:
            path.lineTo(*segment)
    shape(painter, path, Qt.NoBrush, color, width)


def star(painter, center_x, center_y, radius, color):
    points = []
    for point_index in range(10):
        angle = point_index * math.pi / 5 - math.pi / 2
        point_radius = radius if point_index % 2 == 0 else radius * 0.47
        points.append(QPointF(center_x + math.cos(angle) * point_radius,
                              center_y + math.sin(angle) * point_radius))
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor(color))
    painter.drawPolygon(QPolygonF(points))


def sparkle(painter, center_x, center_y, radius, color):
    path = QPainterPath(QPointF(center_x, center_y - radius))
    path.quadTo(center_x + radius * 0.22, center_y - radius * 0.22,
                center_x + radius, center_y)
    path.quadTo(center_x + radius * 0.22, center_y + radius * 0.22,
                center_x, center_y + radius)
    path.quadTo(center_x - radius * 0.22, center_y + radius * 0.22,
                center_x - radius, center_y)
    path.quadTo(center_x - radius * 0.22, center_y - radius * 0.22,
                center_x, center_y - radius)
    shape(painter, path, color)


def check(painter, center_x, center_y, radius=10):
    ellipse(painter, center_x - radius, center_y - radius,
            radius * 2, radius * 2, ACCENT)
    curve(painter, [(center_x - 4, center_y), (center_x - 1, center_y + 3),
                    (center_x + 5, center_y - 4)], "#0e3439", 2)


def lock(painter, center_x, center_y, color=MUTED):
    curve(painter, [(center_x - 4, center_y),
                    (center_x - 4, center_y - 9, center_x + 4,
                     center_y - 9, center_x + 4, center_y)], color, 1.6)
    box(painter, center_x - 6, center_y - 1, 12, 10, color, 2)


def sprout(painter, center_x, center_y, scale=1.0):
    painter.save()
    painter.translate(center_x, center_y)
    painter.scale(scale, scale)
    curve(painter, [(0, 14), (1, 7, 0, -3, 3, -10)], "#499d75", 3)
    leaf = QPainterPath(QPointF(1, -1))
    leaf.cubicTo(-20, 0, -27, -11, -25, -18)
    leaf.cubicTo(-8, -20, 2, -12, 1, -1)
    shape(painter, leaf, "#90d3a2")
    leaf = QPainterPath(QPointF(2, -5))
    leaf.cubicTo(0, -21, 15, -30, 28, -27)
    leaf.cubicTo(30, -12, 18, -3, 2, -5)
    shape(painter, leaf, "#b0e4b2")
    painter.restore()


def scarf(painter, center_x, center_y, scale=1.0):
    painter.save()
    painter.translate(center_x, center_y)
    painter.scale(scale, scale)
    tail = QPainterPath(QPointF(-42, 2))
    tail.cubicTo(-42, 17, -36, 30, -31, 44)
    tail.quadTo(-19, 49, -6, 40)
    tail.lineTo(-19, 5)
    tail.closeSubpath()
    shape(painter, tail, "#3abdb5")
    fold = QPainterPath(QPointF(-66, -10))
    fold.cubicTo(-24, 7, 25, 6, 65, -9)
    fold.lineTo(59, 10)
    fold.cubicTo(18, 26, -25, 25, -60, 11)
    fold.closeSubpath()
    shape(painter, fold, "#77e0d2")
    curve(painter, [(-51, 1), (-18, 14, 20, 13, 52, 2)], "#b7f0e5", 2)
    curve(painter, [(-29, 31), (-13, 27)], "#91e3d5", 2)
    painter.restore()


def seagull(painter, center_x, center_y, scale=1.0, dressed=True):
    painter.save()
    painter.translate(center_x, center_y)
    painter.scale(scale, scale)
    ellipse(painter, -88, 115, 176, 17, QColor(0, 0, 0, 45))
    ellipse(painter, -61, 97, 44, 22, "#edae59")
    ellipse(painter, 18, 97, 44, 22, "#edae59")
    gradient = QLinearGradient(-60, -93, 65, 111)
    gradient.setColorAt(0, QColor("#ffffff"))
    gradient.setColorAt(0.45, QColor("#f1f5f9"))
    gradient.setColorAt(1, QColor("#c8d9e7"))
    body = QPainterPath(QPointF(-89, 10))
    body.cubicTo(-94, -57, -58, -94, -10, -96)
    body.cubicTo(14, -116, 27, -109, 22, -93)
    body.cubicTo(76, -86, 94, -42, 92, 17)
    body.cubicTo(102, 83, 66, 113, 1, 111)
    body.cubicTo(-67, 112, -101, 80, -89, 10)
    shape(painter, body, gradient, "#e2edf4", 1)
    ellipse(painter, -67, -20, 135, 121, QColor(255, 255, 255, 74))
    wing = QPainterPath(QPointF(-83, 12))
    wing.cubicTo(-102, 29, -102, 60, -74, 74)
    wing.cubicTo(-65, 55, -65, 33, -83, 12)
    shape(painter, wing, "#d0deea")
    wing = QPainterPath(QPointF(83, 12))
    wing.cubicTo(106, 21, 117, 7, 117, -13)
    wing.cubicTo(136, 12, 119, 49, 91, 57)
    wing.cubicTo(83, 50, 78, 29, 83, 12)
    shape(painter, wing, "#e4edf5", "#cedde7", 1)
    for eye_x in (-38, 36):
        ellipse(painter, eye_x - 8, -36, 16, 23, "#1b3143")
        ellipse(painter, eye_x - 5, -33, 5.5, 6.5, "#ffffff")
        ellipse(painter, eye_x + 1, -23, 2.5, 3.0, "#8395a7")
    ellipse(painter, -66, -12, 24, 13, QColor(240, 154, 153, 145))
    ellipse(painter, 44, -12, 24, 13, QColor(240, 154, 153, 145))
    beak = QPainterPath(QPointF(-15, -8))
    beak.quadTo(0, -18, 15, -8)
    beak.quadTo(11, 6, 0, 8)
    beak.quadTo(-11, 6, -15, -8)
    shape(painter, beak, "#f8ba62")
    curve(painter, [(-10, -5), (0, -1, 6, -3, 10, -5)], "#d68d42", 1.2)
    if dressed:
        scarf(painter, 0, 43)
        sprout(painter, 0, -114, 0.93)
    painter.restore()


def cat(painter, center_x, center_y, scale=1.0):
    painter.save()
    painter.translate(center_x, center_y)
    painter.scale(scale, scale)
    ellipse(painter, -87, 112, 174, 18, QColor(0, 0, 0, 40))
    curve(painter, [(65, 72), (120, 93, 133, 34, 110, 28)], "#dba46f", 24)
    ellipse(painter, -61, 94, 48, 27, "#dca36e")
    ellipse(painter, 14, 94, 48, 27, "#dca36e")
    gradient = QLinearGradient(-55, -75, 75, 105)
    gradient.setColorAt(0, QColor("#ffe9cc"))
    gradient.setColorAt(1, QColor("#dfb386"))
    body = QPainterPath(QPointF(-80, -33))
    body.lineTo(-79, -104)
    body.quadTo(-72, -119, -34, -76)
    body.quadTo(0, -89, 35, -76)
    body.quadTo(73, -119, 79, -104)
    body.lineTo(80, -33)
    body.cubicTo(109, 43, 87, 112, 0, 111)
    body.cubicTo(-87, 112, -109, 43, -80, -33)
    shape(painter, body, gradient)
    for direction in (-1, 1):
        ear = QPainterPath(QPointF(direction * 64, -91))
        ear.lineTo(direction * 44, -66)
        ear.lineTo(direction * 68, -56)
        ear.closeSubpath()
        shape(painter, ear, "#e9ac9a")
    ellipse(painter, -63, -29, 126, 124, "#fff0d9")
    for stripe_x in (-22, 0, 22):
        box(painter, stripe_x - 5, -70, 10, 23 if stripe_x else 30,
            "#d4a16e", 5)
    for eye_x in (-35, 35):
        ellipse(painter, eye_x - 8, -25, 16, 22, "#493b39")
        ellipse(painter, eye_x - 5, -23, 5, 6, "#ffffff")
    ellipse(painter, -65, -3, 23, 12, "#efb6a5")
    ellipse(painter, 43, -3, 23, 12, "#efb6a5")
    nose = QPainterPath(QPointF(-7, -3))
    nose.quadTo(0, -8, 7, -3)
    nose.lineTo(0, 4)
    nose.closeSubpath()
    shape(painter, nose, "#b7736b")
    curve(painter, [(0, 4), (-1, 15, -13, 16, -16, 10)], "#745248", 2)
    curve(painter, [(0, 4), (1, 15, 13, 16, 16, 10)], "#745248", 2)
    scarf(painter, 0, 60, 0.8)
    ellipse(painter, -8, 77, 16, 16, "#f6d274")
    painter.restore()


def robot(painter, center_x, center_y, scale=1.0):
    painter.save()
    painter.translate(center_x, center_y)
    painter.scale(scale, scale)
    painter.setRenderHint(QPainter.Antialiasing, False)
    box(painter, -7, -117, 14, 30, "#5c93a9", 0)
    box(painter, -13, -127, 26, 20, "#b8a6f1", 0)
    box(painter, -90, -68, 18, 56, "#50809a", 0)
    box(painter, 72, -68, 18, 56, "#50809a", 0)
    box(painter, -74, -92, 148, 114, "#addef0", 0)
    box(painter, -65, -83, 129, 9, "#e1f7ff", 0)
    box(painter, -60, -69, 120, 71, "#213b52", 0)
    box(painter, -45, -49, 22, 21, "#87eee1", 0)
    box(painter, 24, -49, 22, 21, "#87eee1", 0)
    box(painter, -15, -18, 30, 6, "#87eee1", 0)
    box(painter, -53, 30, 106, 70, "#84bfda", 0)
    box(painter, -38, 43, 76, 41, "#527d99", 0)
    for pixel_x, pixel_y in [(-15, 51), (5, 51), (-15, 61),
                              (-5, 61), (5, 61), (-5, 71)]:
        box(painter, pixel_x, pixel_y, 10, 10, "#fac2c0", 0)
    box(painter, -82, 36, 20, 51, "#add9ec", 0)
    box(painter, 62, 36, 20, 51, "#add9ec", 0)
    box(painter, -57, 103, 43, 20, "#51839e", 0)
    box(painter, 14, 103, 43, 20, "#51839e", 0)
    painter.restore()


def sleep_cap(painter, center_x, center_y):
    cap = QPainterPath(QPointF(center_x - 27, center_y + 10))
    cap.cubicTo(center_x - 15, center_y - 34, center_x + 17,
                center_y - 34, center_x + 31, center_y - 10)
    cap.quadTo(center_x + 5, center_y - 20, center_x + 24, center_y + 10)
    cap.closeSubpath()
    shape(painter, cap, "#73799f")
    box(painter, center_x - 31, center_y + 4, 59, 13, "#a3acc8", 6)
    ellipse(painter, center_x + 25, center_y - 13, 12, 12, "#b8bfd5")
    star(painter, center_x - 1, center_y - 8, 7, "#c4bd96")


def draw_preview(painter):
    backdrop = QLinearGradient(0, 0, WIDTH, HEIGHT)
    backdrop.setColorAt(0, QColor("#152536"))
    backdrop.setColorAt(0.65, QColor("#09101c"))
    backdrop.setColorAt(1, QColor("#142632"))
    painter.fillRect(QRectF(0, 0, WIDTH, HEIGHT), backdrop)
    box(painter, 42, 48, 1596, 1009, QColor(0, 0, 0, 55), 30)
    box(painter, 48, 40, 1584, 1004, "#0c1523", 26, "#2a3c4e")
    box(painter, 49, 41, 1582, 84, "#0f1a2a", 25)
    box(painter, 49, 97, 1582, 28, "#0f1a2a", 0)
    curve(painter, [(49, 125), (1631, 125)], "#253245", 1)
    ellipse(painter, 86, 67, 30, 30, "#122f42", "#4bc0e4")
    ellipse(painter, 95, 76, 12, 12, "#70e1dc")
    text(painter, 130, 58, 230, 47, "CareEyes", 25, INK, QFont.DemiBold)
    text(painter, 266, 74, 60, 24, "PRO", 12, MUTED, QFont.DemiBold)
    for nav_index, label in enumerate(("护眼", "休息", "统计", "桌宠", "设置")):
        nav_x = 560 + nav_index * 113
        if label == "桌宠":
            box(painter, nav_x, 59, 86, 45, "#17333d", 12)
        text(painter, nav_x, 60, 86, 43, label, 17,
             ACCENT if label == "桌宠" else MUTED,
             QFont.DemiBold if label == "桌宠" else QFont.Normal,
             Qt.AlignCenter)
    text(painter, 1320, 67, 156, 28, "今天已休息 4 次", 15, "#9fb0c3")
    curve(painter, [(1515, 82), (1529, 82)], "#708297", 1.6)
    curve(painter, [(1569, 76), (1581, 88)], "#708297", 1.6)
    curve(painter, [(1581, 76), (1569, 88)], "#708297", 1.6)

    text(painter, 96, 159, 910, 56, "给休息，找个小搭子。", 36, INK, QFont.DemiBold)
    text(painter, 98, 221, 950, 29, "认真工作，也好好休息。让每一次放松，都变成一点小小的成长。", 17, MUTED)
    box(painter, 1382, 184, 202, 44, "#132a30", 22, "#254147")
    ellipse(painter, 1400, 201, 9, 9, ACCENT)
    text(painter, 1420, 190, 146, 30, "桌宠已开启", 15, "#a3e1d7", align=Qt.AlignCenter)

    hero_gradient = QLinearGradient(96, 274, 946, 906)
    hero_gradient.setColorAt(0, QColor("#192d3d"))
    hero_gradient.setColorAt(0.53, QColor("#17283a"))
    hero_gradient.setColorAt(1, QColor("#142132"))
    box(painter, 96, 274, 850, 632, hero_gradient, 24, "#2b4252")
    text(painter, 128, 297, 200, 31, "正在陪伴你", 16, "#b4c6d5")
    box(painter, 808, 299, 105, 29, "#213748", 14)
    text(painter, 808, 301, 105, 25, "桌面预览", 12, "#a0b5c5", align=Qt.AlignCenter)
    halo = QRadialGradient(522, 624, 270)
    halo.setColorAt(0, QColor(111, 212, 211, 29))
    halo.setColorAt(0.7, QColor(81, 136, 155, 13))
    halo.setColorAt(1, QColor(48, 74, 94, 0))
    ellipse(painter, 230, 341, 585, 564, halo)
    ellipse(painter, 336, 439, 375, 343, QColor(98, 164, 179, 8), "#284353")
    ellipse(painter, 308, 411, 430, 399, QColor(0, 0, 0, 0), "#243c4d")
    box(painter, 302, 357, 438, 58, "#28434c", 20, "#3c5c62")
    text(painter, 309, 361, 424, 49, "再忙，也要给眼睛放个小假。", 19,
         "#d8eee8", align=Qt.AlignCenter)
    pointer = QPainterPath(QPointF(506, 414))
    pointer.lineTo(522, 427)
    pointer.lineTo(534, 414)
    shape(painter, pointer, "#28434c")
    sparkle(painter, 321, 531, 13, "#a2d9d2")
    sparkle(painter, 732, 621, 10, "#8eb5c8")
    sparkle(painter, 660, 460, 8, "#d2c796")
    ellipse(painter, 699, 505, 6, 6, "#608193")
    ellipse(painter, 328, 683, 5, 5, "#608193")
    seagull(painter, 515, 625, 1.38)
    box(painter, 437, 804, 159, 5, "#294154", 2)
    box(painter, 437, 804, 71, 5, ACCENT, 2)
    text(painter, 128, 826, 155, 41, "小海鸥", 26, INK, QFont.DemiBold)
    box(painter, 235, 834, 57, 25, "#244146", 12)
    text(painter, 235, 834, 57, 25, "Lv. 3", 12, "#a1e1d4", QFont.DemiBold, Qt.AlignCenter)
    text(painter, 129, 867, 500, 26, "不催你努力，只提醒你歇会儿。", 15, "#92a9ba")
    box(painter, 716, 839, 198, 44, ACCENT, 13)
    check(painter, 744, 861, 9)
    text(painter, 755, 844, 140, 33, "正在使用", 16, "#0c343b", QFont.DemiBold, Qt.AlignCenter)

    box(painter, 970, 274, 614, 244, "#111d2d", 22, "#263649")
    text(painter, 994, 290, 300, 35, "选择你的搭子", 19, INK, QFont.DemiBold)
    text(painter, 1447, 294, 113, 29, "3 款外观", 13, MUTED, align=Qt.AlignRight)
    for card_x, label, renderer, selected in [
        (994, "小海鸥", seagull, True),
        (1188, "奶油猫", cat, False),
        (1382, "像素机器人", robot, False),
    ]:
        box(painter, card_x, 342, 178, 152,
            "#1b333e" if selected else "#192537", 14,
            ACCENT if selected else "#29384a")
        renderer(painter, card_x + 89, 407, 0.37)
        text(painter, card_x + 5, 460, 168, 25, label, 15,
             "#c5f0e7" if selected else "#b2bfd0", align=Qt.AlignCenter)
        if selected:
            check(painter, card_x + 158, 361, 8)

    box(painter, 970, 540, 614, 230, "#111d2d", 22, "#263649")
    text(painter, 994, 558, 300, 34, "今天，穿什么？", 19, INK, QFont.DemiBold)
    text(painter, 994, 595, 560, 25, "完成休息解锁配饰，不用一直盯着屏幕。", 14, MUTED)
    for card_x, label, icon_name, equipped in [
        (994, "薄荷围巾", "scarf", True),
        (1138, "头顶小芽", "sprout", True),
        (1282, "星星别针", "star", False),
        (1426, "晚安帽", "cap", False),
    ]:
        box(painter, card_x, 633, 134, 113,
            "#1a303a" if equipped else "#172232", 13,
            "#365958" if equipped else "#273345")
        center_x = card_x + 67
        if icon_name == "scarf":
            scarf(painter, center_x, 674, 0.47)
        elif icon_name == "sprout":
            sprout(painter, center_x, 679, 0.9)
        elif icon_name == "star":
            star(painter, center_x, 676, 25, "#8b826a")
            star(painter, center_x - 2, 674, 16, "#b0a387")
        else:
            sleep_cap(painter, center_x, 675)
        text(painter, card_x + 4, 714, 126, 22, label, 13,
             "#a8cfc7" if equipped else "#7d8aa0", align=Qt.AlignCenter)
        if equipped:
            check(painter, card_x + 118, 649, 6.5)
        else:
            lock(painter, card_x + 118, 648, "#68768c")

    box(painter, 970, 792, 614, 114, "#17232e", 20, "#34404b")
    box(painter, 994, 815, 68, 68, "#32343a", 17)
    star(painter, 1028, 849, 24, "#d9bd76")
    star(painter, 1026, 847, 15, "#eddaa4")
    text(painter, 1080, 807, 241, 27, "下一个礼物 · 星星别针", 15, "#e4d7b6", QFont.DemiBold)
    text(painter, 1330, 807, 230, 27, "再休息 2 次解锁", 14, "#b3ac99", align=Qt.AlignRight)
    box(painter, 1080, 850, 378, 6, "#35414b", 3)
    box(painter, 1080, 850, 252, 6, "#d1bf87", 3)
    text(painter, 1475, 839, 85, 27, "4 / 6", 14, "#d1c7ad", align=Qt.AlignRight)
    text(painter, 1080, 870, 478, 21, "休息结束后领取，小搭子一直都在。", 12, "#8e9caa")

    box(painter, 96, 930, 1488, 74, "#111e2c", 18, "#26374a")
    ellipse(painter, 124, 951, 30, 30, Qt.transparent, "#73a2ad")
    curve(painter, [(139, 957), (139, 966), (145, 970)], "#8cbbc2", 1.8)
    text(painter, 168, 949, 117, 33, "下次休息", 15, "#a0b3c7")
    text(painter, 275, 942, 142, 45, "18:42", 29, INK, QFont.DemiBold)
    curve(painter, [(425, 952), (425, 982)], "#314052", 1)
    text(painter, 451, 947, 355, 37, "认真工作，按时放松。", 15, MUTED)
    text(painter, 972, 950, 485, 32, "戳一戳回应  ·  拖动贴边  ·  不抢焦点", 14,
         "#92a8ba", align=Qt.AlignRight)
    box(painter, 1483, 946, 79, 41, "#213245", 11)
    text(painter, 1483, 948, 79, 37, "暂停", 14, "#becbd8", align=Qt.AlignCenter)
    text(painter, 63, 1066, 720, 30, "CARE EYES  /  PET STUDIO", 12, "#697e92", QFont.DemiBold)
    text(painter, 1180, 1066, 440, 30, "桌宠 2.0  ·  概念预览，非已上线功能", 12,
         "#697e92", align=Qt.AlignRight)


def main():
    application = QGuiApplication.instance() or QGuiApplication(sys.argv[:1])
    fonts_directory = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
    for filename in ("msyh.ttc", "msyhbd.ttc", "segoeui.ttf"):
        font_path = fonts_directory / filename
        if font_path.exists():
            QFontDatabase.addApplicationFont(str(font_path))
    image = QImage(WIDTH * 2, HEIGHT * 2, QImage.Format_ARGB32_Premultiplied)
    image.fill(Qt.transparent)
    painter = QPainter(image)
    painter.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing |
                           QPainter.SmoothPixmapTransform)
    painter.scale(2, 2)
    draw_preview(painter)
    painter.end()
    output = Path(__file__).resolve().parents[1] / "images" / "pet-2-concept-v1.png"
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise FileExistsError(f"Preview already exists: {output}")
    final_image = image.scaled(WIDTH, HEIGHT, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
    if not final_image.save(str(output), "PNG"):
        raise RuntimeError(f"Could not save preview: {output}")
    print(f"Saved {output} ({final_image.width()} x {final_image.height()})")
    application.quit()


if __name__ == "__main__":
    main()
