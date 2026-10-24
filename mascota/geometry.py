"""Geometría orgánica procedural con normales suaves para Qt Quick 3D."""
import math
import struct

from PySide6.QtCore import QByteArray
from PySide6.QtGui import QVector3D
from PySide6.QtQuick3D import QQuick3DGeometry


def curved_tube(controls, subdivisions=6, sides=12):
    """Malla cerrada alrededor de una curva Catmull–Rom con radio variable."""
    samples = []
    padded = [controls[0], *controls, controls[-1]]
    for i in range(1, len(padded) - 2):
        a, b, c, d = padded[i-1:i+3]
        for step in range(subdivisions):
            t = step / subdivisions
            values = tuple(.5 * (2*b[k] + (-a[k]+c[k])*t + (2*a[k]-5*b[k]+4*c[k]-d[k])*t*t + (-a[k]+3*b[k]-3*c[k]+d[k])*t*t*t) for k in range(4))
            samples.append(values[:3] + (max(.08, values[3]),))
    samples.append(controls[-1])
    positions = []
    faces = []
    for i, sample in enumerate(samples):
        previous = QVector3D(*samples[max(0, i-1)][:3])
        following = QVector3D(*samples[min(len(samples)-1, i+1)][:3])
        tangent = (following - previous).normalized()
        reference = QVector3D(0, 0, 1) if abs(tangent.z()) < .9 else QVector3D(0, 1, 0)
        u = QVector3D.crossProduct(tangent, reference).normalized()
        v = QVector3D.crossProduct(tangent, u).normalized()
        for side in range(sides):
            angle = side * math.tau / sides
            offset = (u * math.cos(angle) + v * math.sin(angle)) * sample[3]
            positions.append(QVector3D(*sample[:3]) + offset)
            if i:
                a = (i-1)*sides + side
                b = (i-1)*sides + (side+1) % sides
                c = i*sides + side
                d = i*sides + (side+1) % sides
                faces.extend(((a,b,c), (b,d,c)))
    for ring, reverse in ((0, True), (len(samples)-1, False)):
        center = len(positions)
        positions.append(QVector3D(*samples[ring][:3]))
        for side in range(sides):
            a, b = ring*sides+side, ring*sides+(side+1)%sides
            faces.append((center,b,a) if reverse else (center,a,b))
    return positions, faces


class OrganicGeometry(QQuick3DGeometry):
    def build(self, positions, faces):
        normals = [QVector3D() for _ in positions]
        for a, b, c in faces:
            normal = QVector3D.crossProduct(positions[b]-positions[a], positions[c]-positions[a])
            for vertex in (a,b,c):
                normals[vertex] += normal
        normals = [n.normalized() for n in normals]
        data = bytearray()
        for face in faces:
            for index in face:
                p, n = positions[index], normals[index]
                data += struct.pack("6f", p.x(), p.y(), p.z(), n.x(), n.y(), n.z())
        self.setStride(24)
        self.setVertexData(QByteArray(bytes(data)))
        self.setPrimitiveType(QQuick3DGeometry.PrimitiveType.Triangles)
        self.addAttribute(QQuick3DGeometry.Attribute.PositionSemantic, 0, QQuick3DGeometry.Attribute.F32Type)
        self.addAttribute(QQuick3DGeometry.Attribute.NormalSemantic, 12, QQuick3DGeometry.Attribute.F32Type)
        coordinates = [(p.x(), p.y(), p.z()) for p in positions]
        self.setBounds(QVector3D(*(min(p[k] for p in coordinates) for k in range(3))),
                       QVector3D(*(max(p[k] for p in coordinates) for k in range(3))))


class TailGeometry(OrganicGeometry):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.build(*curved_tube([(0,0,0,22),(-25,-7,-10,20),(-62,-6,-15,15),
                                (-98,5,-18,10),(-119,28,-12,6),(-115,51,-5,.4)]))


class CurvedHornGeometry(OrganicGeometry):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.build(*curved_tube([(0,0,0,14),(0,23,-4,11),(7,43,-13,6),(22,56,-22,.15)]))


class FlameGeometry(OrganicGeometry):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.build(*curved_tube([(0,0,0,5),(14,1,0,9),(34,7,0,7),
                                (52,10,0,4),(65,23,0,.1)]))


class WingFrameGeometry(OrganicGeometry):
    def __init__(self, parent=None):
        super().__init__(parent)
        paths = [
            [(0,0,0,4),(25,56,-4,3),(65,92,-10,2.6),(108,65,-10,2),(144,8,-6,.7)],
            [(65,92,-10,2.5),(78,42,1,1.8),(94,-27,0,.5)],
            [(65,92,-10,2.5),(52,21,4,1.8),(45,-52,7,.5)],
        ]
        points, faces = [], []
        for path in paths:
            p, f = curved_tube(path, sides=8)
            offset = len(points)
            points.extend(p)
            faces.extend(tuple(index+offset for index in face) for face in f)
        self.build(points, faces)


class WingGeometry(OrganicGeometry):
    def __init__(self, parent=None):
        super().__init__(parent)
        outline = []
        # Quadratic curves along the scalloped edge remove the old sawtooth shape.
        sections = [((0,0),(25,83),(65,92)), ((65,92),(113,87),(144,8)),
                    ((144,8),(101,32),(94,-27)), ((94,-27),(66,-2),(45,-52)),
                    ((45,-52),(26,-17),(0,0))]
        for a,b,c in sections:
            for j in range(8):
                t=j/8
                x=(1-t)**2*a[0]+2*(1-t)*t*b[0]+t*t*c[0]
                y=(1-t)**2*a[1]+2*(1-t)*t*b[1]+t*t*c[1]
                outline.append((x,y))
        points=[QVector3D(0,0,0)]
        rings=5
        count=len(outline)
        for ring in range(1,rings+1):
            r=ring/rings
            for x,y in outline:
                points.append(QVector3D(x*r,y*r,(-.07*x + 10*math.sin(math.pi*r))*r))
        faces=[]
        for j in range(count):
            faces.append((0,1+(j+1)%count,1+j))
        for ring in range(1,rings):
            for j in range(count):
                a=1+(ring-1)*count+j
                b=1+(ring-1)*count+(j+1)%count
                c=a+count
                d=b+count
                faces.extend(((a,d,b),(a,c,d)))
        self.build(points,faces)


def register_geometry():
    from PySide6.QtQml import qmlRegisterType
    for cls in (WingGeometry, TailGeometry, CurvedHornGeometry, WingFrameGeometry, FlameGeometry):
        qmlRegisterType(cls, "Mascota", 1, 0, cls.__name__)
