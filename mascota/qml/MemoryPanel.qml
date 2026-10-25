import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: panel
    required property var store
    required property var companion
    required property bool busy
    required property Item dialogParent
    readonly property bool dialogOpen: editor.visible || deleteDialog.visible

    function openEditor(memoryId, text) {
        if (busy || !store.available) return
        editor.memoryId = memoryId
        editor.owner = companion.characterId
        editor.errorText = ""
        memoryText.text = text
        editor.open()
    }
    function closeDialog() { editor.close(); deleteDialog.close() }

    ColumnLayout {
        anchors.fill: parent
        spacing: 12
        Text {
            Layout.fillWidth: true
            text: "Recuerdos de " + companion.characterName
            textFormat: Text.PlainText
            color: "#e5efff"; font.pixelSize: 21; font.weight: Font.DemiBold
            elide: Text.ElideRight
        }
        Text {
            Layout.fillWidth: true
            text: "Tú eliges qué guardar. Estos datos quedan en este equipo y se conservan al cerrar la aplicación. Cada personaje tiene sus propios recuerdos."
            color: "#96abc5"; font.pixelSize: 12; wrapMode: Text.WordWrap
        }
        RowLayout {
            Layout.fillWidth: true
            Switch {
                objectName: "useMemories"
                text: "Usar recuerdos"
                checked: store.enabled
                enabled: store.available && !panel.busy
                palette.windowText: "#d0ddef"
                onToggled: store.setEnabled(checked, companion.characterId)
            }
            Text { Layout.fillWidth: true; horizontalAlignment: Text.AlignRight; text: store.count + "/12"; color: "#8098b7"; font.pixelSize: 12 }
            PetButton { text: "Detener"; visible: panel.busy; onClicked: chat.cancel() }
        }
        ListView {
            id: memoryList
            objectName: "memoryList"
            Layout.fillWidth: true
            Layout.fillHeight: true
            model: store.entries
            clip: true; spacing: 10
            boundsBehavior: Flickable.StopAtBounds
            ScrollBar.vertical: ScrollBar {}
            delegate: Rectangle {
                required property int memoryId
                required property string body
                objectName: "memoryCard" + memoryId
                width: memoryList.width
                height: note.implicitHeight + buttons.implicitHeight + 34
                radius: 14; color: "#192435"; border.color: "#2b3c53"
                Text {
                    id: note
                    x: 12; y: 12; width: parent.width - 24
                    text: body; textFormat: Text.PlainText; wrapMode: Text.WordWrap
                    color: "#e4edf9"; font.pixelSize: 14
                }
                Row {
                    id: buttons
                    x: 12; y: note.y + note.height + 10
                    spacing: 8
                    PetButton {
                        objectName: "editMemory" + memoryId
                        text: "Editar"; enabled: store.available && !panel.busy
                        onClicked: panel.openEditor(memoryId, body)
                    }
                    PetButton {
                        objectName: "deleteMemory" + memoryId
                        text: "Eliminar"; enabled: store.available && !panel.busy
                        onClicked: {
                            deleteDialog.memoryId = memoryId
                            deleteDialog.owner = companion.characterId
                            deleteDialog.note = body
                            deleteDialog.errorText = ""
                            deleteDialog.open()
                        }
                    }
                }
            }
            Text {
                anchors.centerIn: parent
                width: parent.width - 32
                visible: store.count === 0
                text: store.available ? "Aún no hay recuerdos. Puedes añadir uno aquí o pulsar Recordar junto a uno de tus mensajes." : "La memoria no está disponible. Tus archivos se conservan; pulsa Actualizar para volver a intentarlo."
                wrapMode: Text.WordWrap; horizontalAlignment: Text.AlignHCenter
                color: "#8ea5c2"; font.pixelSize: 14
            }
        }
        RowLayout {
            Layout.fillWidth: true
            PetButton { objectName: "addMemory"; text: "Nuevo recuerdo"; enabled: store.available && !panel.busy && store.count < 12; onClicked: panel.openEditor(-1, "") }
            Item { Layout.fillWidth: true }
            PetButton { objectName: "refreshMemories"; text: "Actualizar"; onClicked: store.refresh() }
        }
        Text {
            Layout.fillWidth: true
            text: store.status; textFormat: Text.PlainText; wrapMode: Text.WordWrap
            color: store.available ? "#91abc8" : "#efbb84"; font.pixelSize: 12
        }
    }

    Popup {
        id: editor
        objectName: "memoryEditor"
        parent: panel.dialogParent
        property int memoryId: -1
        property string owner: ""
        property string errorText: ""
        x: (parent.width-width)/2; y: Math.max(20, (parent.height-height)/2)
        width: Math.min(420, parent.width-32); height: 365
        modal: true; dim: false; focus: true
        background: Rectangle { color: "#192435"; radius: 18; border.color: "#466184" }
        onOpened: memoryText.forceActiveFocus()
        ColumnLayout {
            anchors.fill: parent; anchors.margins: 12
            spacing: 10
            Text { text: editor.memoryId < 0 ? "Guardar un recuerdo" : "Editar recuerdo"; color: "#f0f6ff"; font.pixelSize: 19; font.weight: Font.DemiBold }
            Text {
                Layout.fillWidth: true
                text: editor.memoryId < 0 ? "Este dato quedará guardado para " + companion.characterName + "." : "Al guardar cambios empezará una charla nueva. Los mensajes anteriores seguirán visibles."
                textFormat: Text.PlainText; wrapMode: Text.WordWrap; color: "#9cb0ca"; font.pixelSize: 12
            }
            Rectangle {
                Layout.fillWidth: true; Layout.fillHeight: true
                radius: 10; color: "#0e1725"; border.color: "#3c587a"
                ScrollView {
                    anchors.fill: parent; anchors.margins: 10
                    TextArea {
                        id: memoryText
                        objectName: "memoryText"
                        textFormat: TextEdit.PlainText; wrapMode: TextEdit.Wrap
                        color: "#eff5ff"; selectionColor: "#356ba4"; font.pixelSize: 14
                        placeholderText: "Ejemplo: Mi color favorito es el azul."
                        placeholderTextColor: "#748ba9"
                        background: null
                    }
                }
            }
            Text { text: memoryText.length + "/240"; color: memoryText.length > 240 ? "#e8b285" : "#819ab8"; font.pixelSize: 11 }
            Text {
                Layout.fillWidth: true
                text: memoryText.length > 240 ? "Resume este dato antes de guardarlo." : editor.errorText
                color: "#e8b285"; font.pixelSize: 12; wrapMode: Text.WordWrap
                visible: text.length > 0
            }
            RowLayout {
                Layout.fillWidth: true
                Item { Layout.fillWidth: true }
                PetButton { objectName: "cancelMemoryEditor"; text: "Cancelar"; onClicked: editor.close() }
                PetButton {
                    objectName: "saveMemory"
                    text: "Guardar"
                    enabled: store.available && !panel.busy && memoryText.text.trim().length > 0 && memoryText.length <= 240
                    onClicked: {
                        if (store.save(editor.memoryId, memoryText.text, editor.owner)) editor.close()
                        else editor.errorText = store.status
                    }
                }
            }
        }
    }
    Popup {
        id: deleteDialog
        objectName: "deleteMemoryDialog"
        parent: panel.dialogParent
        property int memoryId: -1
        property string owner: ""
        property string note: ""
        property string errorText: ""
        x: (parent.width-width)/2; y: Math.max(20, (parent.height-height)/2)
        width: Math.min(420, parent.width-32); height: 355
        modal: true; dim: false; focus: true
        background: Rectangle { color: "#192435"; radius: 18; border.color: "#806047" }
        ColumnLayout {
            anchors.fill: parent; anchors.margins: 12
            spacing: 12
            Text { text: "¿Eliminar este recuerdo?"; color: "#f0f6ff"; font.pixelSize: 19; font.weight: Font.DemiBold }
            Text { Layout.fillWidth: true; text: deleteDialog.note; textFormat: Text.PlainText; color: "#cbd9ec"; font.pixelSize: 14; wrapMode: Text.WordWrap }
            Text { Layout.fillWidth: true; text: "Empezará una charla nueva para dejar de usar el dato guardado. Los mensajes anteriores seguirán visibles."; color: "#a5b6ce"; font.pixelSize: 12; wrapMode: Text.WordWrap }
            Text { Layout.fillWidth: true; text: deleteDialog.errorText; visible: text.length > 0; color: "#e8b285"; wrapMode: Text.WordWrap; font.pixelSize: 12 }
            Item { Layout.fillHeight: true }
            RowLayout {
                Layout.fillWidth: true
                Item { Layout.fillWidth: true }
                PetButton { objectName: "cancelDeleteMemory"; text: "Cancelar"; onClicked: deleteDialog.close() }
                PetButton {
                    objectName: "confirmDeleteMemory"
                    text: "Eliminar"
                    enabled: store.available && !panel.busy
                    onClicked: {
                        if (store.remove(deleteDialog.memoryId, deleteDialog.owner)) deleteDialog.close()
                        else deleteDialog.errorText = store.status
                    }
                }
            }
        }
    }
    Connections {
        target: companion
        function onChanged() {
            if (editor.visible && editor.owner !== companion.characterId) editor.close()
            if (deleteDialog.visible && deleteDialog.owner !== companion.characterId) deleteDialog.close()
        }
    }
}
