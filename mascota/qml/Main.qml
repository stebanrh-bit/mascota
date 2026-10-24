import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick3D

Item {
    id: root
    width: 460
    height: 520
    property real clock: 0
    property real orbit: -16
    property bool showControls: hover.hovered || menu.visible
    NumberAnimation on clock { from: 0; to: Math.PI * 2000; duration: Math.PI * 2000000; loops: Animation.Infinite }
    HoverHandler { id: hover }

    View3D {
        id: viewport
        anchors.fill: parent
        anchors.bottomMargin: 90
        environment: SceneEnvironment {
            backgroundMode: SceneEnvironment.Transparent
            antialiasingMode: SceneEnvironment.MSAA
            antialiasingQuality: SceneEnvironment.High
        }
        OrthographicCamera {
            position: Qt.vector3d(0, 62, 640)
            eulerRotation.x: -5
            horizontalMagnification: .94
            verticalMagnification: .94
        }
        DirectionalLight {
            eulerRotation: Qt.vector3d(-32, -35, 0)
            brightness: 1.1
            ambientColor: "#535d73"
        }
        DirectionalLight { eulerRotation: Qt.vector3d(-15, 140, 0); color: "#549eff"; brightness: .5 }
        Node {
            eulerRotation.y: root.orbit
            y: -4
            Dragon {
                visible: pet.characterKind === "dragon"
                clock: root.clock
                mood: pet.petState
                bodyColor: pet.bodyColor
                bellyColor: pet.bellyColor
                accentColor: pet.accentColor
                eyeColor: pet.eyeColor
            }
            Spirit {
                visible: pet.characterKind === "spirit"
                clock: root.clock
                mood: pet.petState
                bodyColor: pet.bodyColor
                eyeColor: pet.eyeColor
            }
        }
    }
    MouseArea {
        id: touch
        objectName: "petTouch"
        anchors.fill: viewport
        acceptedButtons: Qt.LeftButton | Qt.RightButton
        cursorShape: pressed ? Qt.ClosedHandCursor : Qt.OpenHandCursor
        property point origin
        property point lastGlobal
        property bool moved: false
        onPressed: function(mouse) {
            if (mouse.button === Qt.RightButton) { menu.open(); return }
            origin = mapToGlobal(mouse.x, mouse.y)
            lastGlobal = origin
            moved = false
            pet.setDragging(true)
        }
        onPositionChanged: function(mouse) {
            if (!(pressedButtons & Qt.LeftButton)) return
            const current = mapToGlobal(mouse.x, mouse.y)
            if (Math.abs(current.x-origin.x) + Math.abs(current.y-origin.y) > 6) moved = true
            if (moved) {
                pet.moveBy(Math.round(current.x-lastGlobal.x), Math.round(current.y-lastGlobal.y))
                lastGlobal = current
            }
        }
        onReleased: function(mouse) {
            if (mouse.button !== Qt.LeftButton) return
            pet.setDragging(false)
            if (!moved) pet.pet()
        }
        onCanceled: pet.setDragging(false)
        onWheel: function(wheel) { root.orbit += wheel.angleDelta.y / 12 }
    }
    Column {
        id: caption
        objectName: "caption"
        z: 10
        layer.enabled: true
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: toolbar.top
        anchors.bottomMargin: 12
        spacing: 5
        Rectangle {
            anchors.horizontalCenter: parent.horizontalCenter
            width: nameLabel.implicitWidth + 32; height: 30
            radius: 15; color: "#ee121823"; border.color: "#39435a"
            Text {
                id: nameLabel
                objectName: "nameLabel"
                anchors.centerIn: parent
                text: pet.characterName.toUpperCase()
                color: "#f2f6ff"; font.pixelSize: 11; font.letterSpacing: 2.5; font.weight: Font.DemiBold
            }
        }
        Rectangle {
            width: status.implicitWidth + 24; height: 26
            anchors.horizontalCenter: parent.horizontalCenter
            radius: 13; color: "#d9101520"
            Text { id: status; objectName: "statusLabel"; anchors.centerIn: parent; text: pet.message; color: "#cbd8ed"; font.pixelSize: 11 }
        }
    }
    Row {
        id: toolbar
        z: 10
        anchors.bottom: parent.bottom; anchors.bottomMargin: 12
        anchors.horizontalCenter: parent.horizontalCenter
        spacing: 7
        opacity: root.showControls ? 1 : .55
        Behavior on opacity { NumberAnimation { duration: 180 } }
        Repeater {
            model: ["Acariciar", pet.petState === "sleeping" ? "Despertar" : "Dormir", "Personajes"]
            delegate: Button {
                required property string modelData
                required property int index
                objectName: "action" + index
                text: modelData
                font.pixelSize: 12
                padding: 12
                contentItem: Text { text: parent.text; color: parent.hovered ? "#ffffff" : "#c9d5e7"; font: parent.font; horizontalAlignment: Text.AlignHCenter }
                background: Rectangle { color: parent.hovered ? "#244d84" : "#ed182233"; radius: 15; border.color: parent.hovered ? "#499afa" : "#35425c" }
                onClicked: {
                    if (index === 0) pet.pet()
                    else if (index === 1) pet.toggleSleep()
                    else menu.open()
                }
            }
        }
    }
    Menu {
        id: menu
        objectName: "characterMenu"
        x: (root.width - width) / 2
        y: 65
        width: 272
        modal: true
        dim: false
        onOpened: pet.setMenuOpen(true)
        onClosed: pet.setMenuOpen(false)
        palette.window: "#151e2b"
        palette.text: "#e7efff"
        palette.windowText: "#e7efff"
        palette.buttonText: "#e7efff"
        palette.highlight: "#245b96"
        background: Rectangle { color: "#f917202e"; radius: 18; border.color: "#3a4f6c" }
        MenuItem { text: "ELIGE TU COMPAÑERO"; enabled: false; font.pixelSize: 10; font.letterSpacing: 1.5 }
        MenuItem { objectName: "chooseSombra"; text: "Sombra · dragón negro y azul"; checkable: true; checked: pet.characterId === "sombra"; onTriggered: pet.selectCharacter("sombra") }
        MenuItem { objectName: "chooseBrote"; text: "Brote · dragón del bosque"; checkable: true; checked: pet.characterId === "brote"; onTriggered: pet.selectCharacter("brote") }
        MenuItem { objectName: "chooseNimbo"; text: "Nimbo · espíritu de las nubes"; checkable: true; checked: pet.characterId === "nimbo"; onTriggered: pet.selectCharacter("nimbo") }
        MenuSeparator {}
        MenuItem { text: "Volar un ratito"; onTriggered: pet.fly() }
        MenuItem { text: "Pasear por el escritorio"; checkable: true; checked: pet.roaming; onTriggered: pet.toggleRoaming() }
        MenuItem { text: "Volver al centro"; onTriggered: pet.centerOnScreen() }
        MenuSeparator {}
        MenuItem { text: "Salir"; onTriggered: Qt.quit() }
    }
    Shortcut { sequence: "Escape"; onActivated: { if (menu.visible) menu.close(); else Qt.quit() } }
}
