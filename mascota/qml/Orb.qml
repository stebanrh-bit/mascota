import QtQuick
import QtQuick3D

Model {
    property color tint: "#11141e"
    property real shine: 0.48
    source: "#Sphere"
    materials: PrincipledMaterial {
        baseColor: tint
        roughness: shine
        metalness: 0.06
    }
}
