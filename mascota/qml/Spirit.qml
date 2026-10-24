import QtQuick
import QtQuick3D

Node {
    id: spirit
    property real clock: 0
    property string mood: "idle"
    property color bodyColor: "#b7e9e8"
    property color eyeColor: "#153b55"
    y: Math.sin(clock * 2) * 12
    eulerRotation.z: Math.sin(clock) * 4
    Orb { scale: Qt.vector3d(1.8, 2.1, 1.2); tint: spirit.bodyColor; shine: .6 }
    Repeater3D {
        model: 5
        Orb {
            required property int index
            x: (index - 2) * 29; y: -75 + Math.sin(spirit.clock * 3 + index) * 5
            scale: Qt.vector3d(.50, .7, .7); tint: spirit.bodyColor
        }
    }
    Repeater3D {
        model: 2
        Node {
            required property int index
            readonly property real side: index === 0 ? -1 : 1
            Orb { x: side * 35; y: 23; z: 55; scale: Qt.vector3d(.27, spirit.mood === "sleeping" ? .06 : .40, .13); tint: spirit.eyeColor }
            Orb { x: side * 51; y: -2; z: 55; scale: Qt.vector3d(.23, .12, .08); tint: "#eaaec4" }
            Orb { x: side * 97; y: Math.sin(spirit.clock * 3) * 9; z: 0; scale: Qt.vector3d(.5, .33, .38); tint: spirit.bodyColor }
        }
    }
    Orb { y: -11; z: 61; scale: Qt.vector3d(.18, .13, .06); tint: spirit.eyeColor }
    Horn { y: 124; scale: Qt.vector3d(.3, .40, .3); tint: "#ffe3a0"; eulerRotation.z: -12 }
}
