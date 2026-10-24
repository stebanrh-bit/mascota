import QtQuick
import QtQuick3D
import Mascota 1.0

Node {
    id: dragon
    property real clock: 0
    property string mood: "idle"
    property color bodyColor: "#11141e"
    property color bellyColor: "#242938"
    property color accentColor: "#1368dd"
    property color eyeColor: "#50d9ff"
    readonly property bool asleep: mood === "sleeping"
    readonly property real step: mood === "walking" ? Math.sin(clock * 9) : 0
    readonly property real flap: Math.sin(clock * (mood === "flying" ? 13 : 2))

    // A slight breathing movement keeps the baby alive even at rest.
    y: asleep ? -10 : Math.sin(clock * 2.3) * 2
    eulerRotation.y: mood === "happy" ? Math.sin(clock * 7) * 9 : 0
    eulerRotation.z: mood === "walking" ? step * 2 : 0

    Orb { y: -20; scale: Qt.vector3d(1.23, 1.4, .9); tint: dragon.bodyColor }
    Orb { y: -24; z: 38; scale: Qt.vector3d(.82, 1.05, .28); tint: dragon.bellyColor }
    // Belly segments are small and dark: black remains the dominant color.
    Repeater3D {
        model: 4
        Orb {
            required property int index
            y: 14 - index * 20; z: 49
            scale: Qt.vector3d(.67 - Math.abs(index - 1.5) * .065, .10, .09)
            tint: Qt.lighter(dragon.bellyColor, 1.18)
        }
    }
    // Large baby feet and tiny blue-tipped claws.
    Repeater3D {
        model: 2
        Node {
            required property int index
            readonly property real side: index === 0 ? -1 : 1
            x: side * 41; y: -87 + side * dragon.step * 7; z: 25
            Orb { scale: Qt.vector3d(.55, .38, .77); tint: dragon.bodyColor }
            Repeater3D {
                model: 3
                Horn {
                    required property int index
                    x: (index - 1) * 14; y: -3; z: 35
                    scale: Qt.vector3d(.10, .20, .12)
                    eulerRotation.x: 85
                    tint: "#829caf"
                }
            }
        }
    }
    Repeater3D {
        model: 2
        Node {
            required property int index
            readonly property real side: index === 0 ? -1 : 1
            x: side * 56; y: -3; z: 22
            eulerRotation.z: side * (dragon.mood === "happy" ? 36 : -12)
            Orb { scale: Qt.vector3d(.32, .59, .37); tint: dragon.bodyColor }
            Orb { y: -20; z: 12; scale: Qt.vector3d(.34, .27, .32); tint: dragon.bodyColor }
        }
    }
    // Curling tail: a chain of shaded 3D volumes, swaying from the hip.
    Node {
        x: -35; y: -66; z: -35
        eulerRotation.y: Math.sin(dragon.clock * 2) * 7
        Repeater3D {
            model: 9
            Node {
                required property int index
                x: -index * 11
                y: index * index * 1.1
                z: -Math.sin(index * .35) * 22
                Orb {
                    scale: Qt.vector3d(.43 - index * .035, .40 - index * .032, .45 - index * .035)
                    tint: dragon.bodyColor
                }
                Horn {
                    y: 15 - index
                    scale: Qt.vector3d(.12 - index * .008, .24 - index * .014, .13 - index * .009)
                    tint: dragon.accentColor
                }
            }
        }
    }
    // Jointed wings: independently animated, not a flat image of the pet.
    Repeater3D {
        model: 2
        Node {
            required property int index
            readonly property real side: index === 0 ? -1 : 1
            x: side * 44; y: 10; z: -30
            scale.x: side
            eulerRotation.y: (dragon.asleep ? 64 : 12) + dragon.flap * (dragon.mood === "flying" ? 28 : 5)
            eulerRotation.z: dragon.asleep ? -20 : 0
            Model {
                geometry: WingGeometry {}
                materials: PrincipledMaterial {
                    baseColor: dragon.accentColor
                    roughness: .49
                    metalness: .16
                    cullMode: Material.NoCulling
                }
            }
            Model {
                source: "#Cylinder"
                x: 36; y: 43; z: -7
                scale: Qt.vector3d(.065, 1.12, .065)
                eulerRotation.z: -34
                materials: PrincipledMaterial { baseColor: dragon.bodyColor; roughness: .3 }
            }
            Model {
                source: "#Cylinder"
                x: 91; y: 58; z: -14
                scale: Qt.vector3d(.05, .88, .05)
                eulerRotation.z: 44
                materials: PrincipledMaterial { baseColor: dragon.bodyColor; roughness: .3 }
            }
            Horn { x: 68; y: 98; z: -12; scale: Qt.vector3d(.11, .25, .12); tint: dragon.bodyColor }
        }
    }
    // The oversize head and muzzle keep the silhouette unmistakably baby-like.
    Node {
        id: head
        y: 74; z: 14
        eulerRotation.x: dragon.asleep ? 17 : -3 + Math.sin(dragon.clock * 1.3) * 2
        eulerRotation.z: dragon.mood === "held" ? -12 : 0
        Orb { scale: Qt.vector3d(1.58, 1.27, 1.14); tint: dragon.bodyColor }
        Orb { y: -25; z: 48; scale: Qt.vector3d(1.05, .61, .65); tint: dragon.bodyColor }
        Orb { y: -37; z: 62; scale: Qt.vector3d(.63, .17, .35); tint: "#090b12" }
        Repeater3D {
            model: 2
            Node {
                required property int index
                readonly property real side: index === 0 ? -1 : 1
                x: side * 45; y: 8; z: 46
                // Black sockets, luminous irises, slit pupils, catchlights.
                Orb { scale: Qt.vector3d(.57, dragon.asleep ? .075 : .68, .25); tint: "#05070b" }
                Node {
                    visible: !dragon.asleep
                    Orb { z: 9; scale: Qt.vector3d(.43, .53, .21); tint: "#b9ced7"; shine: .12 }
                    Orb { z: 19; scale: Qt.vector3d(.36, .48, .14); tint: dragon.eyeColor; shine: .18 }
                    Orb { z: 24; scale: Qt.vector3d(.10, .34, .06); tint: "#02060c"; shine: .1 }
                    Orb { x: -7; y: 12; z: 28; scale: Qt.vector3d(.09, .11, .055); tint: "#ffffff"; shine: .05 }
                }
                Orb {
                    y: 26; z: 5
                    scale: Qt.vector3d(.59, .11, .25)
                    eulerRotation.z: side * 15
                    tint: dragon.bodyColor
                }
                Horn {
                    x: side * 9; y: 59; z: -58
                    scale: Qt.vector3d(.32, .64, .33)
                    eulerRotation.z: -side * 22
                    eulerRotation.x: -24
                    tint: "#090c13"
                }
            }
        }
        // Forehead ridge with restrained blue accents.
        Repeater3D {
            model: 3
            Horn {
                required property int index
                y: 60 - index * 3; z: -15 - index * 24
                scale: Qt.vector3d(.15, .26, .18)
                eulerRotation.x: -25
                tint: dragon.accentColor
            }
        }
        Repeater3D {
            model: 2
            Node {
                required property int index
                readonly property real side: index === 0 ? -1 : 1
                Orb { x: side * 22; y: -10; z: 75; scale: Qt.vector3d(.09, .06, .04); tint: "#05070c" }
                Horn {
                    x: side * 34; y: -40; z: 77
                    scale: Qt.vector3d(.12, .24, .12)
                    eulerRotation.z: 180
                    tint: "#ecedf0"
                }
            }
        }
    }
}
