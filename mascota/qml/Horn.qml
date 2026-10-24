import QtQuick
import QtQuick3D

Model {
    property color tint: "#0b0e16"
    source: "#Cone"
    materials: PrincipledMaterial {
        baseColor: tint
        roughness: 0.25
        metalness: 0.2
    }
}
