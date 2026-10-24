"""Membrana de ala 3D triangulada, con normales para iluminación real."""
import struct

from PySide6.QtCore import QByteArray
from PySide6.QtGui import QVector3D
from PySide6.QtQuick3D import QQuick3DGeometry


class WingGeometry(QQuick3DGeometry):
    def __init__(self, parent=None):
        super().__init__(parent)
        # Coordinates are local to the shoulder. The scalloped edge forms a bat wing.
        points = [(0, 0, 0), (28, 70, -5), (68, 96, -12), (110, 60, -18),
                  (144, 8, -10), (105, 22, -5), (94, -27, 0), (60, -6, 4),
                  (45, -52, 9), (22, -24, 5), (8, -62, 8)]
        vertices = bytearray()
        for i in range(1, len(points) - 1):
            triangle = (points[0], points[i], points[i + 1])
            a, b, c = (QVector3D(*p) for p in triangle)
            normal = QVector3D.crossProduct(b - a, c - a).normalized()
            for p in triangle:
                vertices += struct.pack("6f", *p, normal.x(), normal.y(), normal.z())
        self.setStride(24)
        self.setVertexData(QByteArray(bytes(vertices)))
        self.setPrimitiveType(QQuick3DGeometry.PrimitiveType.Triangles)
        self.addAttribute(QQuick3DGeometry.Attribute.PositionSemantic, 0, QQuick3DGeometry.Attribute.F32Type)
        self.addAttribute(QQuick3DGeometry.Attribute.NormalSemantic, 12, QQuick3DGeometry.Attribute.F32Type)
        self.setBounds(QVector3D(0, -62, -18), QVector3D(144, 96, 9))
