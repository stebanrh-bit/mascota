import QtQuick
import QtQuick3D
import Mascota 1.0

Node {
    id: flame
    property real clock: 0
    property real strength: 1
    scale: Qt.vector3d(strength, strength, strength)
    eulerRotation.z: Math.sin(clock * 14) * 4
    Model {
        geometry: FlameGeometry {}
        materials: PrincipledMaterial {
            baseColor: "#167aff"
            lighting: PrincipledMaterial.NoLighting
            opacity: .82
        }
    }
    Model {
        z: 5
        scale: Qt.vector3d(.7,.55,.6)
        geometry: FlameGeometry {}
        materials: PrincipledMaterial {
            baseColor: "#b0f1ff"
            lighting: PrincipledMaterial.NoLighting
        }
    }
    Repeater3D {
        model: 2
        Model {
            required property int index
            x: 22 + index * 12
            y: -5 + index * 5
            z: 2
            eulerRotation.z: -32 - index * 10
            scale: Qt.vector3d(.4,.28,.35)
            geometry: FlameGeometry {}
            materials: PrincipledMaterial {
                baseColor: "#52cfff"
                lighting: PrincipledMaterial.NoLighting
                opacity: .7
            }
        }
    }
}
