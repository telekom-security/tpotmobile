import QtQuick

Rectangle {
    id: control
    objectName: "touchControl"
    property string text: ""
    property bool highlighted: false
    property color accent: "#e20074"
    signal clicked()
    implicitWidth: 120
    implicitHeight: 60
    radius: 10
    color: handler.pressed ? "#302537" : highlighted ? accent : "#17131e"
    border.color: highlighted ? accent : "#49404e"
    opacity: enabled ? 1 : 0.4
    Text {
        anchors.centerIn: parent
        text: control.text
        color: "#ffffff"
        font.pixelSize: 18
        font.weight: Font.DemiBold
        textFormat: Text.PlainText
    }
    TapHandler {
        id: handler
        onTapped: control.clicked()
    }
}
