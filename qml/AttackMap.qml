import QtQuick
import QtQuick.Shapes
import "Theme.js" as Theme

Item {
    id: map
    objectName: "attackMap"
    property bool compact: false
    property bool animationsEnabled: true
    property int nextFlight: 0
    readonly property int eventRevision: backend.state.eventsRevision
    readonly property var destinationEvent: backend.state.recentEvents.find(event => typeof event.destinationLatitude === "number" && typeof event.destinationLongitude === "number")
    signal selected(string identity)
    property int activeFlights: 0
    function recount() {
        let count = 0
        for (let i = 0; i < flights.count; ++i)
            if (flights.itemAt(i) && flights.itemAt(i).active)
                ++count
        activeFlights = count
    }
    function mercator(latitude) {
        return Math.log(Math.tan(Math.PI / 4 + latitude * Math.PI / 360))
    }
    function project(latitude, longitude) {
        const minimum = compact ? -60 : -64
        const clamped = Math.max(minimum, Math.min(80, latitude))
        const relative = (mercator(clamped) - mercator(minimum)) / (mercator(80) - mercator(minimum))
        return Qt.point((width - image.paintedWidth) / 2 + (longitude + 180) / 360 * image.paintedWidth,
                        (height - image.paintedHeight) / 2 + (1 - relative) * image.paintedHeight)
    }
    function stopAnimations() {
        for (let i = 0; i < flights.count; ++i)
            if (flights.itemAt(i))
                flights.itemAt(i).stop()
    }
    function layoutLabels() {
        const placed = []
        function place(label, anchorX, anchorY) {
            const x = Math.max(8, Math.min(width - label.width - 8, anchorX + 14))
            const step = label.height + 6
            let box
            for (let attempt = 0; attempt < 17; ++attempt) {
                const offset = attempt === 0 ? 0 : Math.ceil(attempt / 2) * step * (attempt % 2 ? 1 : -1)
                const y = Math.max(72, Math.min(height - 128 - label.height, anchorY - 4 + offset))
                box = {x: x, y: y, width: label.width, height: label.height}
                if (!placed.some(other => box.x < other.x + other.width + 6 && box.x + box.width + 6 > other.x && box.y < other.y + other.height + 6 && box.y + box.height + 6 > other.y))
                    break
            }
            label.x = box.x - label.parent.x
            label.y = box.y - label.parent.y
            placed.push(box)
        }
        if (sensor.visible)
            place(sensorLabel, sensor.x + 6, sensor.y + 6)
        for (let i = 0; i < Math.min(6, markers.count); ++i) {
            const marker = markers.itemAt(i)
            if (!marker || !marker.visible)
                continue
            const label = marker.labelItem
            place(label, marker.x + 24, marker.y + 24)
        }
    }
    function animateEvents(events) {
        if (!visible || !animationsEnabled || image.status !== Image.Ready)
            return
        let started = 0
        for (const event of events) {
            if (typeof event.latitude !== "number" || typeof event.longitude !== "number")
                continue
            const known = typeof event.destinationLatitude === "number" && typeof event.destinationLongitude === "number"
            const source = project(event.latitude, event.longitude)
            const target = known ? project(event.destinationLatitude, event.destinationLongitude) : source
            flights.itemAt(nextFlight).start(source, target, known, Theme.honeypotColor(event.honeypot))
            nextFlight = (nextFlight + 1) % 3
            if (++started === 3)
                break
        }
    }
    onVisibleChanged: if (!visible) stopAnimations()
    onAnimationsEnabledChanged: if (!animationsEnabled) stopAnimations()
    onEventRevisionChanged: Qt.callLater(layoutLabels)
    onWidthChanged: { stopAnimations(); Qt.callLater(layoutLabels) }
    onHeightChanged: { stopAnimations(); Qt.callLater(layoutLabels) }
    Rectangle { anchors.fill: parent; color: Theme.background }
    Image {
        id: image
        objectName: "worldMapImage"
        anchors.fill: parent
        fillMode: Image.PreserveAspectFit
        asynchronous: true
        source: map.compact ? "../images/map_800477.png" : "../images/map_1280794.png"
        onStatusChanged: if (status === Image.Ready) Qt.callLater(map.layoutLabels)
    }
    Repeater {
        id: markers
        model: backend.events
        delegate: Item {
            id: marker
            objectName: "mapMarker"
            required property string identity
            required property string honeypot
            required property var latitude
            required property var longitude
            required property int index
            property alias labelItem: markerLabel
            readonly property point location: visible ? map.project(latitude, longitude) : Qt.point(0, 0)
            visible: image.status === Image.Ready && typeof latitude === "number" && typeof longitude === "number"
            x: location.x - 24; y: location.y - 24
            width: 48; height: 48
            Shape {
                anchors.fill: parent
                visible: markerLabel.visible
                ShapePath {
                    strokeColor: Theme.honeypotColor(marker.honeypot)
                    strokeWidth: 1
                    fillColor: "transparent"
                    startX: 24; startY: 24
                    PathLine {
                        x: Math.max(markerLabel.x, Math.min(24, markerLabel.x + markerLabel.width))
                        y: Math.max(markerLabel.y, Math.min(24, markerLabel.y + markerLabel.height))
                    }
                }
            }
            Rectangle { anchors.centerIn: parent; width: 10; height: 10; radius: 5; color: Theme.honeypotColor(marker.honeypot) }
            Text {
                id: markerLabel
                objectName: "mapLabel"
                x: 38; y: 20
                width: Math.min(implicitWidth, map.width - 16)
                elide: Text.ElideRight
                visible: marker.index < 6
                text: marker.honeypot
                color: Theme.text; style: Text.Outline; styleColor: Theme.background
                font.pixelSize: map.compact ? 18 : 22
                textFormat: Text.PlainText
            }
            TapHandler { onTapped: map.selected(marker.identity) }
        }
    }
    Item {
        id: sensor
        readonly property point location: visible ? map.project(map.destinationEvent.destinationLatitude, map.destinationEvent.destinationLongitude) : Qt.point(0, 0)
        visible: image.status === Image.Ready && !!map.destinationEvent
        x: location.x - 6; y: location.y - 6
        width: 12; height: 12
        Rectangle { anchors.fill: parent; color: "#fff" }
        Shape {
            anchors.fill: parent
            ShapePath {
                strokeColor: "#fff"; strokeWidth: 1; fillColor: "transparent"
                startX: 6; startY: 6
                PathLine {
                    x: Math.max(sensorLabel.x, Math.min(6, sensorLabel.x + sensorLabel.width))
                    y: Math.max(sensorLabel.y, Math.min(6, sensorLabel.y + sensorLabel.height))
                }
            }
        }
        Text {
            id: sensorLabel
            x: 20; y: 28
            width: Math.min(implicitWidth, map.width - 16)
            elide: Text.ElideRight
            text: backend.state.fixture ? "Sensor / fixture" : "Sensor"
            color: Theme.text; style: Text.Outline; styleColor: Theme.background
            font.pixelSize: map.compact ? 18 : 22
        }
    }
    Repeater {
        id: flights
        model: 3
        delegate: AttackFlight { width: map.width; height: map.height; onActiveChanged: map.recount() }
    }
    Connections {
        target: backend
        function onPings(events) { map.animateEvents(events) }
    }
    Text {
        anchors.centerIn: parent
        visible: image.status === Image.Error
        text: "Map asset unavailable; see application log."
        color: "#ff725f"; font.pixelSize: 18
    }
}
