import QtQuick
import QtQuick.Controls

Button {
    id: control
    font.pixelSize: 12
    padding: 12
    opacity: enabled ? 1 : .4
    contentItem: Text {
        text: control.text
        color: control.hovered ? "#ffffff" : "#c9d5e7"
        font: control.font
        horizontalAlignment: Text.AlignHCenter
    }
    background: Rectangle {
        color: control.hovered ? "#244d84" : "#ed182233"
        radius: 15
        border.color: control.hovered ? "#499afa" : "#35425c"
    }
}
