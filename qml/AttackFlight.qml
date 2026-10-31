import QtQuick
import QtQuick.Shapes
import "Theme.js" as Theme

Item {
    id: flight
    objectName: "attackFlight"
    property point origin: Qt.point(0, 0)
    property point destination: Qt.point(0, 0)
    property point control: Qt.point(0, 0)
    property bool destinationKnown: false
    property bool active: false
    property real progress: 0
    property color accent: Theme.magenta
    readonly property real travel: Math.min(1, progress / .75)
    readonly property real beamX: (1 - travel) * (1 - travel) * origin.x + 2 * (1 - travel) * travel * control.x + travel * travel * destination.x
    readonly property real beamY: (1 - travel) * (1 - travel) * origin.y + 2 * (1 - travel) * travel * control.y + travel * travel * destination.y
    visible: active
    function start(source, target, known, color) {
        motion.stop()
        origin = source
        destination = target
        destinationKnown = known
        control = Qt.point((source.x + target.x) / 2,
                           Math.min(source.y, target.y) - Math.min(130, Math.abs(source.x - target.x) * .3 + 30))
        accent = color
        progress = 0
        active = true
        motion.start()
    }
    function stop() { motion.stop(); active = false; progress = 0 }
    Shape {
        anchors.fill: parent
        visible: flight.destinationKnown
        opacity: Math.min(1, flight.progress * 8) * (1 - flight.progress) * .5
        ShapePath {
            strokeColor: flight.accent
            strokeWidth: 2
            fillColor: "transparent"
            startX: flight.origin.x
            startY: flight.origin.y
            PathQuad {
                x: flight.destination.x; y: flight.destination.y
                controlX: flight.control.x; controlY: flight.control.y
            }
        }
    }
    Rectangle {
        objectName: "attackBeam"
        x: flight.beamX - width / 2; y: flight.beamY - height / 2
        width: 8; height: 8; radius: 4
        color: flight.accent
        visible: flight.destinationKnown && flight.progress < .78
    }
    Rectangle {
        x: flight.origin.x - width / 2; y: flight.origin.y - height / 2
        width: 12 + flight.progress * 56; height: width; radius: width / 2
        color: "transparent"; border.color: flight.accent; border.width: 2
        opacity: 1 - flight.progress
    }
    Rectangle {
        readonly property real arrival: Math.max(0, (flight.progress - .65) / .35)
        x: flight.destination.x - width / 2; y: flight.destination.y - height / 2
        width: 12 + arrival * 56; height: width; radius: width / 2
        visible: flight.destinationKnown && flight.progress >= .65
        color: "transparent"; border.color: flight.accent; border.width: 2
        opacity: 1 - arrival
    }
    NumberAnimation {
        id: motion
        target: flight; property: "progress"
        from: 0; to: 1; duration: 1350
        onFinished: flight.active = false
    }
    Component.onDestruction: motion.stop()
}
