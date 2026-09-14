from PyQt5.QtCore import QPointF, QRectF, Qt
from PyQt5.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPen


def _box(painter, left, top, width, height, fill, radius=18, stroke=None):
    painter.setPen(QPen(QColor(stroke), 1.2) if stroke else Qt.NoPen)
    painter.setBrush(QColor(fill) if isinstance(fill, str) else fill)
    painter.drawRoundedRect(QRectF(left, top, width, height), radius, radius)


def _ellipse(painter, left, top, width, height, fill, stroke=None):
    painter.setPen(QPen(QColor(stroke), 1.2) if stroke else Qt.NoPen)
    painter.setBrush(QColor(fill) if isinstance(fill, str) else fill)
    painter.drawEllipse(QRectF(left, top, width, height))


def _shape(painter, path, fill, stroke=None, stroke_width=1.5):
    painter.setPen(QPen(QColor(stroke), stroke_width,
                        Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
                   if stroke else Qt.NoPen)
    painter.setBrush(QColor(fill) if isinstance(fill, str) else fill)
    painter.drawPath(path)


def _curve(painter, coordinates, color, width=2.0):
    path = QPainterPath(QPointF(*coordinates[0]))
    for segment in coordinates[1:]:
        if len(segment) == 6:
            path.cubicTo(*segment)
        else:
            path.lineTo(*segment)
    _shape(painter, path, Qt.NoBrush, color, width)


def _sprout(painter, center_x, center_y, scale=1.0):
    painter.save()
    painter.translate(center_x, center_y)
    painter.scale(scale, scale)
    _curve(painter, [(0, 14), (1, 7, 0, -3, 3, -10)], "#499d75", 3)
    leaf = QPainterPath(QPointF(1, -1))
    leaf.cubicTo(-20, 0, -27, -11, -25, -18)
    leaf.cubicTo(-8, -20, 2, -12, 1, -1)
    _shape(painter, leaf, "#90d3a2")
    leaf = QPainterPath(QPointF(2, -5))
    leaf.cubicTo(0, -21, 15, -30, 28, -27)
    leaf.cubicTo(30, -12, 18, -3, 2, -5)
    _shape(painter, leaf, "#b0e4b2")
    painter.restore()


def _scarf(painter, center_x, center_y, scale=1.0):
    painter.save()
    painter.translate(center_x, center_y)
    painter.scale(scale, scale)
    tail = QPainterPath(QPointF(-42, 2))
    tail.cubicTo(-42, 17, -36, 30, -31, 44)
    tail.quadTo(-19, 49, -6, 40)
    tail.lineTo(-19, 5)
    tail.closeSubpath()
    _shape(painter, tail, "#3abdb5")
    fold = QPainterPath(QPointF(-66, -10))
    fold.cubicTo(-24, 7, 25, 6, 65, -9)
    fold.lineTo(59, 10)
    fold.cubicTo(18, 26, -25, 25, -60, 11)
    fold.closeSubpath()
    _shape(painter, fold, "#77e0d2")
    _curve(painter, [(-51, 1), (-18, 14, 20, 13, 52, 2)], "#b7f0e5", 2)
    _curve(painter, [(-29, 31), (-13, 27)], "#91e3d5", 2)
    painter.restore()


def _seagull(painter, center_x, center_y, scale=1.0, dressed=True):
    painter.save()
    painter.translate(center_x, center_y)
    painter.scale(scale, scale)
    _ellipse(painter, -88, 115, 176, 17, QColor(0, 0, 0, 45))
    _ellipse(painter, -61, 97, 44, 22, "#edae59")
    _ellipse(painter, 18, 97, 44, 22, "#edae59")
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
    _shape(painter, body, gradient, "#e2edf4", 1)
    _ellipse(painter, -67, -20, 135, 121, QColor(255, 255, 255, 74))
    wing = QPainterPath(QPointF(-83, 12))
    wing.cubicTo(-102, 29, -102, 60, -74, 74)
    wing.cubicTo(-65, 55, -65, 33, -83, 12)
    _shape(painter, wing, "#d0deea")
    wing = QPainterPath(QPointF(83, 12))
    wing.cubicTo(106, 21, 117, 7, 117, -13)
    wing.cubicTo(136, 12, 119, 49, 91, 57)
    wing.cubicTo(83, 50, 78, 29, 83, 12)
    _shape(painter, wing, "#e4edf5", "#cedde7", 1)
    for eye_x in (-38, 36):
        _ellipse(painter, eye_x - 8, -36, 16, 23, "#1b3143")
        _ellipse(painter, eye_x - 5, -33, 5.5, 6.5, "#ffffff")
        _ellipse(painter, eye_x + 1, -23, 2.5, 3.0, "#8395a7")
    _ellipse(painter, -66, -12, 24, 13, QColor(240, 154, 153, 145))
    _ellipse(painter, 44, -12, 24, 13, QColor(240, 154, 153, 145))
    beak = QPainterPath(QPointF(-15, -8))
    beak.quadTo(0, -18, 15, -8)
    beak.quadTo(11, 6, 0, 8)
    beak.quadTo(-11, 6, -15, -8)
    _shape(painter, beak, "#f8ba62")
    _curve(painter, [(-10, -5), (0, -1, 6, -3, 10, -5)], "#d68d42", 1.2)
    if dressed:
        _scarf(painter, 0, 43)
        _sprout(painter, 0, -114, 0.93)
    painter.restore()


def _cat(painter, center_x, center_y, scale=1.0):
    painter.save()
    painter.translate(center_x, center_y)
    painter.scale(scale, scale)
    _ellipse(painter, -87, 112, 174, 18, QColor(0, 0, 0, 40))
    _curve(painter, [(65, 72), (120, 93, 133, 34, 110, 28)], "#dba46f", 24)
    _ellipse(painter, -61, 94, 48, 27, "#dca36e")
    _ellipse(painter, 14, 94, 48, 27, "#dca36e")
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
    _shape(painter, body, gradient)
    for direction in (-1, 1):
        ear = QPainterPath(QPointF(direction * 64, -91))
        ear.lineTo(direction * 44, -66)
        ear.lineTo(direction * 68, -56)
        ear.closeSubpath()
        _shape(painter, ear, "#e9ac9a")
    _ellipse(painter, -63, -29, 126, 124, "#fff0d9")
    for stripe_x in (-22, 0, 22):
        _box(painter, stripe_x - 5, -70, 10, 23 if stripe_x else 30,
            "#d4a16e", 5)
    for eye_x in (-35, 35):
        _ellipse(painter, eye_x - 8, -25, 16, 22, "#493b39")
        _ellipse(painter, eye_x - 5, -23, 5, 6, "#ffffff")
    _ellipse(painter, -65, -3, 23, 12, "#efb6a5")
    _ellipse(painter, 43, -3, 23, 12, "#efb6a5")
    nose = QPainterPath(QPointF(-7, -3))
    nose.quadTo(0, -8, 7, -3)
    nose.lineTo(0, 4)
    nose.closeSubpath()
    _shape(painter, nose, "#b7736b")
    _curve(painter, [(0, 4), (-1, 15, -13, 16, -16, 10)], "#745248", 2)
    _curve(painter, [(0, 4), (1, 15, 13, 16, 16, 10)], "#745248", 2)
    _scarf(painter, 0, 60, 0.8)
    _ellipse(painter, -8, 77, 16, 16, "#f6d274")
    painter.restore()


def _robot(painter, center_x, center_y, scale=1.0):
    painter.save()
    painter.translate(center_x, center_y)
    painter.scale(scale, scale)
    painter.setRenderHint(QPainter.Antialiasing, False)
    _box(painter, -7, -117, 14, 30, "#5c93a9", 0)
    _box(painter, -13, -127, 26, 20, "#b8a6f1", 0)
    _box(painter, -90, -68, 18, 56, "#50809a", 0)
    _box(painter, 72, -68, 18, 56, "#50809a", 0)
    _box(painter, -74, -92, 148, 114, "#addef0", 0)
    _box(painter, -65, -83, 129, 9, "#e1f7ff", 0)
    _box(painter, -60, -69, 120, 71, "#213b52", 0)
    _box(painter, -45, -49, 22, 21, "#87eee1", 0)
    _box(painter, 24, -49, 22, 21, "#87eee1", 0)
    _box(painter, -15, -18, 30, 6, "#87eee1", 0)
    _box(painter, -53, 30, 106, 70, "#84bfda", 0)
    _box(painter, -38, 43, 76, 41, "#527d99", 0)
    for pixel_x, pixel_y in [(-15, 51), (5, 51), (-15, 61),
                              (-5, 61), (5, 61), (-5, 71)]:
        _box(painter, pixel_x, pixel_y, 10, 10, "#fac2c0", 0)
    _box(painter, -82, 36, 20, 51, "#add9ec", 0)
    _box(painter, 62, 36, 20, 51, "#add9ec", 0)
    _box(painter, -57, 103, 43, 20, "#51839e", 0)
    _box(painter, 14, 103, 43, 20, "#51839e", 0)
    painter.restore()
