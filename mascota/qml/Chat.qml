import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: root
    width: 500; height: 700
    color: "#0d1420"
    property bool configuring: false
    property bool settingsDirty: endpointField.text.trim() !== chat.endpoint || modelField.text.trim() !== chat.modelName
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 20
        spacing: 14
        RowLayout {
            Layout.fillWidth: true
            Rectangle {
                width: 44; height: 44; radius: 16
                color: pet.accentColor
                Text { anchors.centerIn: parent; text: pet.characterName.charAt(0).toUpperCase(); color: "white"; font.pixelSize: 23; font.bold: true }
            }
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 3
                Text { text: "TU COMPAÑERO · IA LOCAL"; color: "#8096b5"; font.pixelSize: 10; font.letterSpacing: 1.4 }
                Text { text: pet.characterName; textFormat: Text.PlainText; color: "#edf5ff"; font.pixelSize: 22; font.weight: Font.DemiBold }
            }
            PetButton {
                objectName: "configureChat"
                text: root.configuring ? "Volver" : "Configurar"
                onClicked: {
                    root.configuring = !root.configuring
                    if (root.configuring) { endpointField.text = chat.endpoint; modelField.text = chat.modelName }
                }
            }
        }
        Rectangle { Layout.fillWidth: true; height: 1; color: "#243248" }
        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: root.configuring ? 1 : 0
            ColumnLayout {
                spacing: 10
                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    ListView {
                        id: messages
                        objectName: "chatMessages"
                        anchors.fill: parent
                        model: chat.conversation
                        clip: true
                        spacing: 12
                        boundsBehavior: Flickable.StopAtBounds
                        property bool followTail: true
                        onMovementStarted: followTail = false
                        onMovementEnded: followTail = atYEnd
                        onCountChanged: { followTail = true; Qt.callLater(positionViewAtEnd) }
                        ScrollBar.vertical: ScrollBar {}
                        delegate: Item {
                            required property string speaker
                            required property string body
                            required property string messageState
                            width: messages.width
                            height: bubble.height
                            Rectangle {
                                id: bubble
                                x: speaker === "user" ? messages.width - width : 0
                                width: messages.width * .91
                                height: contents.implicitHeight + 24
                                radius: 15
                                color: speaker === "user" ? "#173b65" : "#192435"
                                border.color: messageState === "error" ? "#b98348" : "#2b3c53"
                                Column {
                                    id: contents
                                    x: 12; y: 12; width: parent.width - 24
                                    spacing: 6
                                    Text {
                                        text: speaker === "user" ? "TÚ" : pet.characterName.toUpperCase()
                                        textFormat: Text.PlainText
                                        color: "#91abcb"; font.pixelSize: 10; font.letterSpacing: 1
                                    }
                                    TextArea {
                                        width: parent.width
                                        text: body.length ? body : "Pensando…"
                                        textFormat: TextEdit.PlainText
                                        readOnly: true
                                        selectByMouse: true
                                        wrapMode: TextEdit.Wrap
                                        padding: 0
                                        color: messageState === "error" ? "#f2c896" : "#e4edf9"
                                        selectionColor: "#356ba4"
                                        font.pixelSize: 14
                                        background: null
                                    }
                                }
                            }
                        }
                    }
                    Connections {
                        target: chat.conversation
                        function onDataChanged() { if (messages.followTail) Qt.callLater(messages.positionViewAtEnd) }
                    }
                    Column {
                        anchors.centerIn: parent
                        width: parent.width - 28
                        spacing: 12
                        visible: messages.count === 0
                        Text {
                            width: parent.width
                            text: "Una charla con " + pet.characterName
                            textFormat: Text.PlainText
                            horizontalAlignment: Text.AlignHCenter
                            wrapMode: Text.WordWrap
                            color: "#e3edfb"; font.pixelSize: 21; font.weight: Font.DemiBold
                        }
                        Text {
                            width: parent.width
                            text: chat.ready ? "Pregúntame algo, cuéntame tu día o comparte una idea." : "Abre Configurar para conectar la IA de tu equipo. No necesitas una suscripción."
                            wrapMode: Text.WordWrap
                            horizontalAlignment: Text.AlignHCenter
                            color: "#92a6c0"; font.pixelSize: 13
                        }
                        Text {
                            width: parent.width
                            text: "El historial se conserva durante esta sesión."
                            horizontalAlignment: Text.AlignHCenter
                            color: "#617995"; font.pixelSize: 11
                        }
                    }
                }
                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: 104
                    radius: 15; color: "#141f30"; border.color: input.activeFocus ? "#418cde" : "#304057"
                    ScrollView {
                        anchors.fill: parent; anchors.margins: 12
                        TextArea {
                            id: input
                            objectName: "chatInput"
                            placeholderText: "Escribe a tu compañero…"
                            placeholderTextColor: "#748ba9"
                            textFormat: TextEdit.PlainText
                            color: "#eff5ff"; selectionColor: "#356ba4"
                            wrapMode: TextEdit.Wrap
                            font.pixelSize: 14
                            background: null
                            Keys.onReturnPressed: function(event) {
                                if (!(event.modifiers & Qt.ShiftModifier)) {
                                    event.accepted = true
                                    if (chat.send(text)) text = ""
                                } else event.accepted = false
                            }
                        }
                    }
                }
                RowLayout {
                    Layout.fillWidth: true
                    PetButton { objectName: "clearChat"; text: "Vaciar"; enabled: !chat.busy; onClicked: chat.clear() }
                    Text { Layout.fillWidth: true; text: input.length + "/2000"; horizontalAlignment: Text.AlignRight; color: input.length > 2000 ? "#e1a978" : "#748ba9"; font.pixelSize: 11 }
                    PetButton {
                        objectName: "sendChat"
                        text: chat.busy ? "Detener" : "Enviar"
                        enabled: chat.busy || (chat.ready && input.text.trim().length > 0 && input.length <= 2000)
                        onClicked: { if (chat.busy) chat.cancel(); else if (chat.send(input.text)) input.text = "" }
                    }
                }
            }
            ScrollView {
                objectName: "chatSettings"
                clip: true
                contentWidth: availableWidth
                ColumnLayout {
                    width: parent.width
                    spacing: 13
                    Text { text: "Conecta tu IA local"; color: "#e4efff"; font.pixelSize: 21; font.weight: Font.DemiBold }
                    Text {
                        Layout.fillWidth: true
                        text: "1. Instala y abre <a href='https://ollama.com/download/windows'>Ollama para Windows</a>."
                        textFormat: Text.RichText
                        linkColor: "#75b9ff"; color: "#bbcce2"; font.pixelSize: 13; wrapMode: Text.WordWrap
                        onLinkActivated: function(link) { Qt.openUrlExternally(link) }
                    }
                    Text { Layout.fillWidth: true; text: "2. Guarda la configuración y comprueba la conexión."; color: "#bbcce2"; font.pixelSize: 13; wrapMode: Text.WordWrap }
                    Label { text: "Modelo"; color: "#92a6c0" }
                    TextField {
                        id: modelField
                        objectName: "modelField"
                        Layout.fillWidth: true
                        text: chat.modelName
                        enabled: !chat.busy
                        maximumLength: 128
                        color: "#eff5ff"; selectionColor: "#356ba4"
                        background: Rectangle { radius: 9; color: "#182538"; border.color: "#35465e" }
                    }
                    ComboBox {
                        Layout.fillWidth: true
                        visible: chat.availableModels.length > 0
                        model: chat.availableModels
                        enabled: !chat.busy
                        onActivated: modelField.text = currentText
                    }
                    CheckBox { id: advanced; text: "Conexión avanzada"; palette.windowText: "#bbcce2"; enabled: !chat.busy }
                    TextField {
                        id: endpointField
                        objectName: "endpointField"
                        Layout.fillWidth: true
                        visible: advanced.checked
                        text: chat.endpoint
                        enabled: !chat.busy
                        color: "#eff5ff"; selectionColor: "#356ba4"
                        background: Rectangle { radius: 9; color: "#182538"; border.color: "#35465e" }
                    }
                    PetButton {
                        objectName: "probeChat"
                        text: "Guardar y comprobar"
                        enabled: !chat.busy
                        onClicked: {
                            if (chat.configure(endpointField.text, modelField.text)) {
                                endpointField.text = chat.endpoint
                                modelField.text = chat.modelName
                                chat.checkConnection()
                            }
                        }
                    }
                    Text { Layout.fillWidth: true; visible: root.settingsDirty; text: "Guarda los cambios antes de descargar el modelo elegido."; color: "#d5bd92"; font.pixelSize: 12; wrapMode: Text.WordWrap }
                    Text { Layout.fillWidth: true; text: "3. Si todavía no tienes el modelo, descárgalo aquí."; color: "#bbcce2"; font.pixelSize: 13; wrapMode: Text.WordWrap }
                    Text {
                        Layout.fillWidth: true
                        text: "qwen2.5:0.5b es una opción ligera (aprox. 400 MB). La descarga requiere Internet y se hace a través de Ollama."
                        color: "#8198b5"; font.pixelSize: 12; wrapMode: Text.WordWrap
                    }
                    RowLayout {
                        PetButton { objectName: "downloadChatModel"; text: "Descargar modelo"; enabled: chat.connected && !chat.busy && !root.settingsDirty; onClicked: chat.downloadModel() }
                        PetButton { text: "Detener"; visible: chat.busy; onClicked: chat.cancel() }
                    }
                    ProgressBar {
                        Layout.fillWidth: true
                        visible: chat.operation === "pull"
                        from: 0; to: 100; value: chat.progress
                        indeterminate: chat.progress < 0
                    }
                    Text { Layout.fillWidth: true; text: "Cuando esté listo, pulsa Volver para conversar. Las respuestas de la IA pueden contener errores."; color: "#8198b5"; font.pixelSize: 12; wrapMode: Text.WordWrap }
                    Item { Layout.preferredHeight: 12 }
                }
            }
        }
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: statusLabel.implicitHeight + 24
            color: "#141f30"; radius: 12
            Text {
                id: statusLabel
                objectName: "chatStatus"
                x: 12; y: 12; width: parent.width - 24
                text: chat.status
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
                color: chat.ready ? "#9edbc4" : "#bdcce0"
                font.pixelSize: 12
            }
        }
    }
    Shortcut { sequence: "Escape"; onActivated: { if (root.configuring) root.configuring = false; else chatWindow.close() } }
}
