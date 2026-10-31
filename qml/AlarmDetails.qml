import QtQuick
import QtQuick.Layouts
import "Theme.js" as Theme

Flickable {
    id: view
    objectName: "alarmDetails"
    property var event: ({})
    property bool compact: false
    property bool expanded: false
    signal openDetails()
    clip: true
    contentWidth: width
    contentHeight: column.implicitHeight
    boundsBehavior: Flickable.StopAtBounds
    function rows() {
        if (!event.identity)
            return []
        const base = [
            {label: "SOURCE IP", value: event.sourceIp || "Unknown"},
            {label: "SERVICE", value: Theme.service(event)},
            {label: "REPUTATION", value: event.reputation || "Unknown", accent: "#ffbe77"}
        ]
        if (!compact || expanded)
            base.push({label: "GEO COORDINATES", value: Theme.coordinates(event)})
        base.push({label: "USERNAME", value: event.username || "--", accent: "#ff92c7"})
        base.push({label: "PASSWORD", value: event.password || "--", accent: "#ff92c7"})
        return base
    }
    ColumnLayout {
        id: column
        width: view.width
        spacing: view.compact && !view.expanded ? 6 : 14
        RowLayout {
            Layout.fillWidth: true
            spacing: 12
            Image {
                Layout.preferredWidth: view.compact && !view.expanded ? 54 : 81
                Layout.preferredHeight: view.compact && !view.expanded ? 36 : 54
                source: view.event.countryCode ? "../flags/" + view.event.countryCode + ".png" : ""
                sourceSize: Qt.size(162, 108)
                fillMode: Image.PreserveAspectFit
                asynchronous: true
                visible: status === Image.Ready
            }
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 2
                Text {
                    Layout.fillWidth: true
                    text: view.event.country || "No recent event"
                    color: Theme.text
                    font.pixelSize: view.compact && !view.expanded ? 20 : 26
                    font.weight: Font.DemiBold
                    elide: Text.ElideRight
                    textFormat: Text.PlainText
                }
                Text {
                    Layout.fillWidth: true
                    visible: !view.compact || view.expanded
                    text: [Theme.detail(view.event, "Region"), Theme.detail(view.event, "City")].filter(v => v).join(" / ")
                    color: Theme.muted
                    font.pixelSize: 16
                    elide: Text.ElideRight
                    textFormat: Text.PlainText
                }
            }
            Text { text: view.event.honeypot || ""; color: Theme.honeypotColor(text); font.pixelSize: view.compact ? 14 : 18; textFormat: Text.PlainText }
        }
        GridLayout {
            Layout.fillWidth: true
            columns: 2
            columnSpacing: 14
            rowSpacing: view.compact && !view.expanded ? 5 : 14
            Repeater {
                model: view.rows()
                ColumnLayout {
                    required property var modelData
                    Layout.fillWidth: true
                    Layout.columnSpan: modelData.label === "REPUTATION" && view.compact && !view.expanded ? 2 : 1
                    Layout.preferredWidth: view.width / 2 - 7
                    spacing: 2
                    Text { text: modelData.label; color: Theme.muted; font.pixelSize: view.compact && !view.expanded ? 11 : 13 }
                    Text {
                        objectName: modelData.label === "REPUTATION" ? "visibleReputation" : "alarmValue"
                        Layout.fillWidth: true
                        text: modelData.value
                        color: modelData.accent || Theme.text
                        font.family: uiMonoFamily
                        font.pixelSize: view.compact && !view.expanded ? 16 : view.expanded ? 20 : 19
                        elide: view.expanded ? Text.ElideNone : Text.ElideRight
                        wrapMode: view.expanded ? Text.WrapAnywhere : Text.NoWrap
                        textFormat: Text.PlainText
                    }
                }
            }
        }
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: view.compact && !view.expanded ? 46 : commandColumn.implicitHeight + 24
            color: Theme.background
            border.color: Theme.line
            Column {
                id: commandColumn
                x: 10; y: view.compact && !view.expanded ? 5 : 12
                width: parent.width - 20
                spacing: 4
                Text { text: "COMMAND / REQUEST" + (view.compact && !view.expanded ? "   DETAILS ↗" : " / PLAIN TEXT"); color: Theme.muted; font.pixelSize: 11 }
                Text {
                    width: parent.width
                    text: view.event.command || "No command recorded"
                    color: Theme.text
                    font.family: uiMonoFamily
                    font.pixelSize: view.compact && !view.expanded ? 14 : view.expanded ? 20 : 16
                    maximumLineCount: view.compact && !view.expanded ? 1 : 100
                    elide: Text.ElideRight
                    wrapMode: view.compact && !view.expanded ? Text.NoWrap : Text.WrapAnywhere
                    textFormat: Text.PlainText
                }
            }
            TapHandler { enabled: view.compact && !view.expanded; onTapped: view.openDetails() }
        }
        GridLayout {
            Layout.fillWidth: true
            visible: !view.compact || view.expanded
            columns: 2
            Repeater {
                model: view.expanded ? (view.event.details || []).filter(row => !["Country", "Region", "City", "Source IP", "Reputation", "Honeypot", "Username", "Password", "Command"].includes(row.label))
                                     : [{label: "AS organization", value: Theme.detail(view.event, "AS organization")},
                                        {label: "Timestamp", value: view.event.timestamp ? Theme.timestamp(view.event.timestamp) : ""}]
                ColumnLayout {
                    required property var modelData
                    Layout.fillWidth: true
                    Layout.preferredWidth: view.width / 2 - 7
                    Text { text: modelData.label.toUpperCase(); color: Theme.muted; font.pixelSize: 13 }
                    Text {
                        objectName: modelData.label === "Timestamp" ? "displayTimestamp" : "supplementaryValue"
                        Layout.fillWidth: true
                        text: modelData.value || "--"
                        color: Theme.text
                        font.family: uiMonoFamily
                        font.pixelSize: view.expanded ? 20 : 18
                        wrapMode: modelData.label === "AS organization" ? Text.Wrap : view.expanded ? Text.WrapAnywhere : Text.Wrap
                        textFormat: Text.PlainText
                    }
                }
            }
        }
    }
}
