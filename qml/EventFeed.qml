import QtQuick
import "Theme.js" as Theme

GridView {
    id: feed
    objectName: "eventFeed"
    property bool compact: false
    property bool expanded: false
    signal selected(string identity)
    readonly property int columns: expanded && !compact ? 2 : 1
    cellWidth: width / columns
    cellHeight: expanded ? compact ? 96 : 158 : 99
    clip: true
    model: backend.events
    delegate: Rectangle {
        id: row
        objectName: "eventCard"
        required property string identity
        required property string timestamp
        required property string honeypot
        required property string country
        required property string countryCode
        required property string sourceIp
        required property string protocol
        required property string reputation
        required property string command
        width: feed.cellWidth - (feed.columns === 2 ? 10 : 0)
        height: feed.cellHeight - 8
        radius: 8
        readonly property color accent: Theme.honeypotColor(honeypot)
        readonly property bool chosen: backend.selected.identity === identity
        color: backend.selected.identity === identity ? "#241825" : "#191621"
        border.color: chosen ? accent : Qt.rgba(accent.r, accent.g, accent.b, .4)
        border.width: chosen ? 2 : 1
        Image {
            id: flag
            x: 12; anchors.verticalCenter: parent.verticalCenter
            width: feed.expanded ? 60 : 54; height: width * 2 / 3
            source: row.countryCode ? "../flags/" + row.countryCode + ".png" : ""
            sourceSize: Qt.size(120, 80)
            fillMode: Image.PreserveAspectFit
            asynchronous: true
            visible: status === Image.Ready
        }
        Item {
            x: flag.visible ? flag.x + flag.width + 12 : 14
            anchors.verticalCenter: parent.verticalCenter
            width: parent.width - x - 12
            height: feed.expanded && !feed.compact ? 110 : 74
            Text {
                width: parent.width - clock.width - 10
                text: row.honeypot + " / " + row.protocol
                color: Theme.honeypotColor(row.honeypot)
                font.pixelSize: feed.expanded ? 20 : 19
                font.weight: Font.DemiBold
                elide: Text.ElideRight
                textFormat: Text.PlainText
            }
            Text {
                id: clock
                objectName: "eventTimestamp"
                anchors.right: parent.right
                text: Theme.time(row.timestamp)
                color: "#d1bdce"; font.family: uiMonoFamily
                font.pixelSize: feed.expanded && feed.compact ? 16 : 18
            }
            Text {
                y: 25
                width: feed.expanded && feed.compact ? parent.width * .6 - 6 : parent.width
                text: row.country + " · " + row.sourceIp
                color: Theme.muted; font.pixelSize: feed.expanded ? 16 : 14
                elide: Text.ElideRight
                textFormat: Text.PlainText
            }
            Text {
                y: feed.expanded && feed.compact ? 25 : 47
                x: feed.expanded && feed.compact ? parent.width * .6 + 6 : 0
                width: parent.width - x
                text: row.reputation
                color: "#edc795"; font.pixelSize: feed.expanded ? 16 : 14
                elide: Text.ElideRight
                textFormat: Text.PlainText
            }
            Text {
                y: feed.compact ? 48 : 78
                width: parent.width
                visible: feed.expanded
                text: row.command || "No command recorded"
                maximumLineCount: 1
                color: Theme.text; font.family: uiMonoFamily; font.pixelSize: feed.compact ? 14 : 16
                elide: Text.ElideRight
                textFormat: Text.PlainText
            }
        }
        TapHandler { onTapped: feed.selected(row.identity) }
    }
    Text {
        anchors.centerIn: parent
        visible: feed.count === 0
        text: "No recent events\nCheck connection and service status under System."
        color: Theme.muted
        font.pixelSize: 16
        horizontalAlignment: Text.AlignHCenter
    }
}
