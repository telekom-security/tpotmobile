import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "Theme.js" as Theme

ApplicationWindow {
    id: root
    width: backend.state.fixture ? fixtureWidth : Screen.width
    height: backend.state.fixture ? fixtureHeight : Screen.height
    visible: true
    visibility: backend.state.fixture ? Window.Windowed : Window.FullScreen
    title: "T-Pot Mobile"
    color: Theme.background
    palette.window: Theme.panel
    palette.base: Theme.background
    palette.text: Theme.text
    palette.windowText: Theme.text
    palette.button: "#191621"
    palette.buttonText: Theme.text
    palette.highlight: Theme.magenta
    font.family: uiFontFamily
    font.pixelSize: 16
    readonly property bool compact: width < 1000
    property int page: 0
    property bool presentation: false
    property bool presentationPaused: false
    property bool startupVisible: true
    property bool startupComplete: false
    property bool startupPainted: false
    property bool chartExpanded: false
    property bool animationsEnabled: true
    property string powerAction: ""
    property string clockText: ""
    property string statusText: ""
    property string statusTitle: ""
    readonly property var state: backend.state
    readonly property var telemetry: state.system
    function number(value, digits) { return typeof value === "number" ? value.toFixed(digits) : "n/a" }
    function navigate(destination) { page = destination; chartExpanded = false }
    function openEvent(identity) {
        backend.selectEvent(identity)
        if (page === 1 || page === 2)
            details.open()
    }
    function showStatus(title, text) { statusTitle = title; statusText = text; statusDialog.open() }
    function dataStatus() {
        const alerts = [state.eventsError, state.statsError, state.notice, state.actionMessage].filter(value => value)
        return alerts.length ? alerts.join("\n") : "Last event poll: " + state.eventAge + "s ago\nLast statistics: " + state.statsAge + "s ago"
    }
    function updateClock() { clockText = Theme.time(Date.now()) }
    function finishStartup() {
        if (!startupComplete && startupPainted && state.eventAge >= 0) {
            startupVisible = false
            startupComplete = true
        }
    }
    onFrameSwapped: {
        if (startupVisible && bootImage.status === Image.Ready) {
            startupPainted = true
            finishStartup()
        }
    }
    PointHandler { onActiveChanged: if (active && root.presentation) root.presentationPaused = true }
    Shortcut { sequence: "Q"; onActivated: Qt.quit() }
    Timer {
        objectName: "presentationTimer"
        interval: 20000; repeat: true
        running: root.presentation && !root.presentationPaused && !root.startupVisible && !root.chartExpanded
                 && !details.opened && !statusDialog.opened && !powerDialog.opened
        onTriggered: root.navigate((root.page + 1) % 5)
    }
    Timer { interval: 1000; repeat: true; running: true; onTriggered: root.updateClock() }
    Component.onCompleted: updateClock()
    Connections {
        target: backend
        function onStateChanged() { root.finishStartup() }
    }
    Canvas {
        anchors.fill: parent
        opacity: .25
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()
        onPaint: {
            const ctx = getContext("2d")
            ctx.clearRect(0, 0, width, height); ctx.strokeStyle = "#571a40"; ctx.lineWidth = .7
            for (let x = width * .65; x < width + 70; x += 92)
                for (let y = 0; y < height + 80; y += 80) {
                    ctx.beginPath(); ctx.moveTo(x + 23, y + 1); ctx.lineTo(x + 69, y + 1)
                    ctx.lineTo(x + 91, y + 40); ctx.lineTo(x + 69, y + 79); ctx.lineTo(x + 23, y + 79)
                    ctx.lineTo(x + 1, y + 40); ctx.closePath(); ctx.stroke()
                }
        }
    }
    Rectangle { width: parent.width; height: 3; color: Theme.magenta }
    ColumnLayout {
        anchors.fill: parent
        anchors.leftMargin: root.compact ? 12 : 20
        anchors.rightMargin: root.compact ? 12 : 20
        anchors.topMargin: root.compact ? 5 : 8
        anchors.bottomMargin: root.compact ? 9 : 12
        spacing: root.compact ? 8 : 12
        visible: root.page !== 1
        RowLayout {
            objectName: "topBar"
            Layout.fillWidth: true
            Layout.preferredHeight: root.compact ? 45 : 52
            Layout.maximumHeight: root.compact ? 46 : 52
            spacing: root.compact ? 8 : 12
            Image {
                Layout.preferredWidth: root.compact ? 26 : 30
                Layout.preferredHeight: root.compact ? 31 : 36
                source: "../images/telekom-logo-magenta.svg"
                fillMode: Image.PreserveAspectFit
            }
            Text { text: "T-POT MOBILE"; color: Theme.text; font.pixelSize: root.compact ? 20 : 23; font.weight: Font.Bold }
            Text { visible: !root.compact; text: "dev-24.04.2"; color: Theme.muted; font.pixelSize: 15 }
            Item { Layout.fillWidth: true }
            Column {
                visible: !root.compact
                Text { text: "PUBLIC IP"; color: Theme.muted; font.pixelSize: 11 }
                Text { text: root.telemetry.externalIp || "n/a"; color: Theme.text; font.family: uiMonoFamily; font.pixelSize: 19; textFormat: Text.PlainText }
            }
            StatusIcon {
                kind: root.state.fixture ? "fixture" : root.state.eventsError || root.state.eventAge > 15 ? "warning" : "live"
                accent: root.state.fixture ? "#ffbe77" : root.state.eventsError || root.state.eventAge > 15 ? "#ff725f" : Theme.magenta
                Layout.alignment: Qt.AlignVCenter
                onClicked: root.showStatus(root.state.fixture ? "SYNTHETIC FIXTURE" : "DATA STATUS", (root.state.fixture ? "Synthetic development data. Hardware actions disabled.\n" : "") + root.dataStatus())
            }
            StatusIcon {
                kind: root.state.following ? "live" : "held"
                Layout.alignment: Qt.AlignVCenter
                onClicked: backend.followLive()
            }
            StatusIcon {
                kind: "wifi"; value: root.telemetry.signal
                Layout.alignment: Qt.AlignVCenter
                onClicked: root.showStatus("WI-FI / NETWORK", "Signal quality: " + root.number(root.telemetry.signal, 0) + "%\nPublic IP: " + (root.telemetry.externalIp || "n/a") + "\nLocal IP: " + (root.telemetry.localIp || "n/a") + "\n" + (root.telemetry.networkError || ""))
            }
            StatusIcon {
                kind: "battery"; value: root.telemetry.battery.percentage; charging: root.telemetry.battery.charging === true
                Layout.alignment: Qt.AlignVCenter
                onClicked: root.showStatus("BATTERY / UPS", "Estimated charge: " + root.number(root.telemetry.battery.percentage, 0) + "%\n" + (root.telemetry.battery.charging === true ? "Charging" : root.telemetry.battery.charging === false ? "Discharging" : "State unknown") + "\n" + root.number(root.telemetry.battery.watts, 2) + " W / " + root.number(root.telemetry.battery.voltage, 2) + " V\nVoltage-based estimate, not a calibrated fuel gauge.\n" + (root.telemetry.error || ""))
            }
            Text { text: root.clockText; color: Theme.text; font.family: uiMonoFamily; font.pixelSize: root.compact ? 21 : 24 }
        }
        Loader {
            id: content
            objectName: "pageContent"
            Layout.fillWidth: true; Layout.fillHeight: true
            sourceComponent: [overviewPage, null, eventsPage, topsPage, systemPage][root.page]
        }
        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: root.compact ? 52 : 60
            Layout.maximumHeight: root.compact ? 52 : 60
            spacing: root.compact ? 8 : 10
            Repeater {
                model: ["Overview", "Map", "Events", "Tops", "System"]
                TouchButton {
                    required property int index
                    required property string modelData
                    objectName: "navigationButton"
                    Layout.fillWidth: true; Layout.fillHeight: true
                    text: modelData; highlighted: root.page === index
                    onClicked: root.navigate(index)
                }
            }
        }
    }
    Component {
        id: overviewPage
        ColumnLayout {
            spacing: root.compact ? 8 : 12
            RowLayout {
                Layout.preferredHeight: root.compact ? 59 : 76
                Layout.maximumHeight: root.compact ? 59 : 76
                spacing: root.compact ? 8 : 12
                Repeater {
                    model: ["1m", "15m", "1h", "24h"]
                    Panel {
                        required property string modelData
                        Layout.fillWidth: true; Layout.fillHeight: true
                        border.color: root.state.timeframe === modelData ? Theme.magenta : Theme.line
                        Column {
                            x: 16; anchors.verticalCenter: parent.verticalCenter
                            Text { text: "LAST " + parent.parent.modelData; color: Theme.muted; font.pixelSize: root.compact ? 12 : 14 }
                            Text { text: Theme.count(root.state.counts[parent.parent.modelData], root.compact); color: Theme.text; font.family: uiMonoFamily; font.pixelSize: root.compact ? 24 : 29 }
                        }
                        TapHandler { onTapped: backend.selectTimeframe(parent.modelData) }
                    }
                }
            }
            RowLayout {
                Layout.fillWidth: true; Layout.fillHeight: true
                spacing: root.compact ? 8 : 14
                Panel {
                    Layout.fillWidth: true; Layout.fillHeight: true
                    Layout.preferredWidth: root.compact ? 480 : 720
                    border.color: Theme.honeypotColor(backend.selected.honeypot)
                    ColumnLayout {
                        anchors.fill: parent; anchors.margins: root.compact ? 10 : 16
                        spacing: root.compact ? 7 : 12
                        RowLayout {
                            Layout.fillWidth: true
                            Text { text: "ALARM INTELLIGENCE"; color: Theme.muted; font.pixelSize: root.compact ? 12 : 14 }
                            Item { Layout.fillWidth: true }
                            Text { text: root.state.following ? "◉ LIVE" : "Ⅱ HELD"; color: Theme.text; font.pixelSize: 13; TapHandler { onTapped: backend.followLive() } }
                        }
                        AlarmDetails {
                            Layout.fillWidth: true; Layout.fillHeight: true
                            event: backend.selected; compact: root.compact
                            onOpenDetails: details.open()
                        }
                    }
                }
                ColumnLayout {
                    Layout.preferredWidth: root.compact ? 289 : 510
                    Layout.fillHeight: true
                    spacing: 12
                    Panel {
                        visible: !root.compact
                        Layout.fillWidth: true; Layout.fillHeight: true
                        ColumnLayout {
                            anchors.fill: parent; anchors.margins: 12
                            spacing: 9
                            Text { text: "ATTACK STREAM"; color: Theme.muted; font.pixelSize: 13 }
                            EventFeed { Layout.fillWidth: true; Layout.fillHeight: true; onSelected: identity => root.openEvent(identity) }
                        }
                    }
                    Panel {
                        objectName: "activityWidget"
                        Layout.fillWidth: true
                        Layout.fillHeight: root.compact
                        Layout.preferredHeight: root.compact ? 280 : 178
                        ColumnLayout {
                            anchors.fill: parent; anchors.margins: root.compact ? 10 : 16
                            Text { text: "ACTIVITY / LAST " + root.state.chartTimeframe + (root.state.statsError ? "  !" : "   ↗"); color: root.state.statsError ? "#ffbe77" : Theme.muted; font.pixelSize: root.compact ? 12 : 14 }
                            Chart {
                                Layout.fillWidth: true; Layout.fillHeight: true
                                values: root.state.timeline; times: root.state.timelineTimes
                                grid: true; compact: root.compact; revision: root.state.statsRevision
                            }
                        }
                        TapHandler { onTapped: root.chartExpanded = true }
                    }
                }
            }
        }
    }
    Component {
        id: eventsPage
        Panel {
            ColumnLayout {
                anchors.fill: parent; anchors.margins: root.compact ? 10 : 16
                spacing: root.compact ? 7 : 12
                Text { text: "EVENT INTELLIGENCE / MOST RECENT 200"; color: Theme.muted; font.pixelSize: root.compact ? 12 : 14 }
                EventFeed { Layout.fillWidth: true; Layout.fillHeight: true; expanded: true; compact: root.compact; onSelected: identity => root.openEvent(identity) }
            }
        }
    }
    Component {
        id: topsPage
        ColumnLayout {
            spacing: root.compact ? 8 : 12
            RowLayout {
                Text { text: "THREAT DISTRIBUTION"; color: Theme.muted; font.pixelSize: root.compact ? 13 : 16 }
                Item { Layout.fillWidth: true }
                Repeater {
                    model: ["1m", "15m", "1h", "24h"]
                    TouchButton {
                        required property string modelData
                        Layout.preferredWidth: 64; Layout.preferredHeight: 44
                        text: modelData; highlighted: root.state.timeframe === modelData
                        onClicked: backend.selectTimeframe(modelData)
                    }
                }
            }
            RowLayout {
                Layout.fillWidth: true; Layout.fillHeight: true
                Distribution { Layout.fillWidth: true; Layout.fillHeight: true; title: "ORIGIN COUNTRIES / TOP 4"; entries: root.state.countries; countries: true; compact: root.compact; revision: root.state.statsRevision }
                Distribution { Layout.fillWidth: true; Layout.fillHeight: true; title: "HONEYPOT DISTRIBUTION"; entries: root.state.honeypots; compact: root.compact; revision: root.state.statsRevision }
            }
            Panel {
                id: servicesPanel
                readonly property real valueWidth: Math.max(40, ...root.state.services.map(entry => portNumberMetrics.advanceWidth(Theme.count(entry.count, root.compact))))
                FontMetrics { id: portNumberMetrics; font.family: uiMonoFamily; font.pixelSize: root.compact ? 14 : 16 }
                Layout.fillWidth: true; Layout.preferredHeight: root.compact ? 112 : 160
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: root.compact ? 10 : 16
                    Text { text: "TARGET SERVICES / TOP PORTS"; color: Theme.muted; font.pixelSize: root.compact ? 12 : 14 }
                    GridLayout {
                        Layout.fillWidth: true; Layout.fillHeight: true
                        columns: 2; columnSpacing: 24
                        Repeater {
                            model: root.state.services
                            RowLayout {
                                required property var modelData
                                required property int index
                                Layout.fillWidth: true; Layout.preferredWidth: root.width / 2 - 60
                                Text {
                                    text: modelData.name; color: Theme.text; font.pixelSize: root.compact ? 13 : 16
                                    Layout.minimumWidth: root.compact ? 92 : 110
                                    Layout.maximumWidth: root.compact ? 92 : 110
                                    elide: Text.ElideRight
                                    textFormat: Text.PlainText
                                }
                                Rectangle {
                                    objectName: "portTrack"
                                    Layout.fillWidth: true; height: 12; color: "#26202e"; radius: 4
                                    Rectangle { objectName: "portFill"; width: parent.width * modelData.count / Math.max(1, ...root.state.services.map(entry => entry.count)); height: parent.height; color: Theme.palette[index % Theme.palette.length]; radius: 4 }
                                }
                                Text {
                                    objectName: "portValue"
                                    text: Theme.count(modelData.count, root.compact); color: Theme.text; font.family: uiMonoFamily; font.pixelSize: root.compact ? 14 : 16
                                    Layout.minimumWidth: servicesPanel.valueWidth
                                    Layout.maximumWidth: servicesPanel.valueWidth
                                    horizontalAlignment: Text.AlignRight
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    Component {
        id: systemPage
        Flickable {
            clip: true; contentWidth: width; contentHeight: systemColumn.implicitHeight
            ColumnLayout {
                id: systemColumn
                width: parent.width; spacing: 12
                Text { text: "DEVICE HEALTH / PRESENTATION"; color: Theme.magenta; font.pixelSize: 18 }
                RowLayout {
                    TouchButton { text: root.presentation ? "Disable demo" : "Enable demo"; highlighted: root.presentation; onClicked: { root.presentation = !root.presentation; root.presentationPaused = false } }
                    TouchButton { visible: root.presentation && root.presentationPaused; text: "Resume"; onClicked: root.presentationPaused = false }
                    TouchButton { text: root.animationsEnabled ? "Effects on" : "Effects off"; highlighted: root.animationsEnabled; onClicked: root.animationsEnabled = !root.animationsEnabled }
                }
                Text { text: "CPU " + root.number(root.telemetry.cpu, 1) + "% / RAM " + root.number(root.telemetry.ramUsed, 0) + " / " + root.number(root.telemetry.ramTotal, 0) + " MiB / " + root.number(root.telemetry.temperature, 1) + " °C"; color: Theme.text; font.pixelSize: 16 }
                Text { text: "Battery estimate " + root.number(root.telemetry.battery.percentage, 0) + "% / " + root.number(root.telemetry.battery.watts, 2) + " W / " + (root.telemetry.battery.charging === true ? "Charging" : root.telemetry.battery.charging === false ? "Discharging" : "Unknown"); color: Theme.text; font.pixelSize: 16 }
                Chart { Layout.fillWidth: true; Layout.preferredHeight: 65; values: root.telemetry.history; revision: root.state.systemRevision; accent: "#78cddd" }
                Text { text: "Valid power readings / trailing 10 minutes"; color: Theme.muted; font.pixelSize: 13 }
                RowLayout {
                    Text { text: "Brightness"; color: Theme.text }
                    Slider { id: brightness; Layout.fillWidth: true; from: 5; to: 100; stepSize: 1; value: typeof root.telemetry.brightness === "number" ? root.telemetry.brightness : 60; onPressedChanged: if (!pressed) backend.brightness(Math.round(value)) }
                    Text { text: typeof root.telemetry.brightness === "number" ? root.telemetry.brightness + "%" : "n/a"; color: Theme.text }
                }
                Text { text: "Battery cap: 60%. Manual override lasts until the next power-source change."; color: Theme.muted; font.pixelSize: 13 }
                Text { text: "Public IP " + (root.telemetry.externalIp || "n/a") + " / Local IP " + (root.telemetry.localIp || "n/a") + " / Wi-Fi " + root.number(root.telemetry.signal, 0) + "%"; color: Theme.text; font.pixelSize: 16; textFormat: Text.PlainText }
                Text { Layout.fillWidth: true; text: root.dataStatus() + "\n" + (root.telemetry.error || "") + "\n" + (root.telemetry.networkError || ""); color: Theme.muted; wrapMode: Text.Wrap; font.pixelSize: 14; textFormat: Text.PlainText }
                Repeater {
                    model: root.telemetry.containers || []
                    RowLayout {
                        required property var modelData
                        Text { Layout.preferredWidth: 160; text: modelData.name; color: Theme.text; elide: Text.ElideRight; textFormat: Text.PlainText }
                        Text { text: modelData.state; color: modelData.state === "running" ? "#78cddd" : "#ffbe77"; textFormat: Text.PlainText }
                        Text { Layout.fillWidth: true; text: modelData.status; color: Theme.muted; elide: Text.ElideRight; textFormat: Text.PlainText }
                    }
                }
                RowLayout {
                    TouchButton { text: "Boot preview"; visible: root.state.fixture; onClicked: root.startupVisible = true }
                    TouchButton { text: "Reboot"; onClicked: { root.powerAction = "reboot"; powerDialog.open() } }
                    TouchButton { text: "Power off"; highlighted: true; onClicked: { root.powerAction = "poweroff"; powerDialog.open() } }
                }
            }
        }
    }
    Loader {
        anchors.fill: parent
        active: root.page === 1
        sourceComponent: Component {
            Item {
                AttackMap { anchors.fill: parent; compact: root.compact; animationsEnabled: root.animationsEnabled && !details.opened && !root.startupVisible; onSelected: identity => root.openEvent(identity) }
                RowLayout {
                    anchors.top: parent.top; anchors.left: parent.left; anchors.right: parent.right; anchors.margins: 16
                    Text { text: "GLOBAL ATTACK RADAR" + (root.state.fixture ? " / FIXTURE" : ""); color: Theme.text; font.pixelSize: root.compact ? 16 : 19; style: Text.Outline; styleColor: Theme.background }
                    Item { Layout.fillWidth: true }
                    Text { text: root.state.eventsError || root.state.eventAge > 15 ? "!" : "●"; color: root.state.eventsError || root.state.eventAge > 15 ? "#ff725f" : Theme.magenta; font.pixelSize: 24; TapHandler { onTapped: root.showStatus("DATA STATUS", root.dataStatus()) } }
                    TouchButton { implicitHeight: 52; text: "← Back"; onClicked: root.navigate(0) }
                }
                RowLayout {
                    anchors.bottom: parent.bottom; anchors.left: parent.left; anchors.right: parent.right
                    anchors.margins: 16; spacing: 10
                    Repeater {
                        model: root.state.recentEvents.slice(0, root.compact ? 2 : 3)
                        Panel {
                            id: mapCard
                            required property var modelData
                            readonly property var event: modelData
                            Layout.fillWidth: true; Layout.preferredHeight: 96
                            color: "#e8100e1d"
                            readonly property color accent: Theme.honeypotColor(event.honeypot)
                            readonly property bool chosen: backend.selected.identity === event.identity
                            border.color: chosen ? accent : Qt.rgba(accent.r, accent.g, accent.b, .4)
                            border.width: chosen ? 2 : 1
                            RowLayout {
                                anchors.fill: parent; anchors.margins: 10
                                Image { Layout.preferredWidth: 42; Layout.preferredHeight: 28; source: mapCard.event.countryCode ? "../flags/" + mapCard.event.countryCode + ".png" : ""; fillMode: Image.PreserveAspectFit }
                                ColumnLayout {
                                    Layout.fillWidth: true; spacing: 3
                                    RowLayout {
                                        Layout.fillWidth: true
                                        Text { Layout.fillWidth: true; text: mapCard.event.honeypot; color: Theme.honeypotColor(text); font.pixelSize: 17; elide: Text.ElideRight; textFormat: Text.PlainText }
                                        Text { objectName: "mapTimestamp"; text: Theme.time(mapCard.event.timestamp); color: Theme.text; font.family: uiMonoFamily; font.pixelSize: 18 }
                                    }
                                    Text { Layout.fillWidth: true; text: mapCard.event.sourceIp; color: Theme.text; font.family: uiMonoFamily; font.pixelSize: 16; elide: Text.ElideRight; textFormat: Text.PlainText }
                                    Text { Layout.fillWidth: true; text: mapCard.event.reputation; color: Theme.text; font.pixelSize: 16; elide: Text.ElideRight; textFormat: Text.PlainText }
                                }
                            }
                            TapHandler { onTapped: root.openEvent(mapCard.event.identity) }
                        }
                    }
                }
            }
        }
    }
    Rectangle {
        objectName: "chartOverlay"
        anchors.fill: parent; visible: root.chartExpanded; color: Theme.background
        ColumnLayout {
            anchors.fill: parent; anchors.margins: root.compact ? 14 : 22; spacing: 10
            RowLayout {
                Layout.fillWidth: true
                Text { text: "ACTIVITY / LAST " + root.state.chartTimeframe; color: Theme.text; font.pixelSize: root.compact ? 18 : 21 }
                Item { Layout.fillWidth: true }
                Repeater {
                    model: ["1m", "15m", "1h", "24h"]
                    TouchButton {
                        required property string modelData
                        objectName: "histogramControl"
                        Layout.preferredWidth: 64; Layout.preferredHeight: 52
                        text: modelData; highlighted: root.state.timeframe === modelData
                        onClicked: backend.selectTimeframe(modelData)
                    }
                }
                Rectangle { objectName: "histogramDivider"; width: 1; height: 32; color: "#655069" }
                TouchButton { objectName: "histogramControl"; Layout.preferredWidth: 64; Layout.preferredHeight: 52; text: "Back"; onClicked: root.chartExpanded = false }
            }
            Panel {
                Layout.fillWidth: true; Layout.fillHeight: true
                Chart { anchors.fill: parent; anchors.margins: 14; grid: true; compact: root.compact; values: root.state.timeline; times: root.state.timelineTimes; revision: root.state.statsRevision }
            }
        }
    }
    Dialog {
        id: details
        objectName: "detailsDialog"
        anchors.centerIn: parent; width: root.width - 40; height: root.height - 40
        modal: true; title: "ALARM DETAILS"
        contentItem: ColumnLayout {
            AlarmDetails { Layout.fillWidth: true; Layout.fillHeight: true; event: backend.selected; expanded: true; compact: root.compact }
            TouchButton { Layout.fillWidth: true; implicitHeight: 52; text: "Back"; onClicked: details.close() }
        }
    }
    Dialog {
        id: statusDialog
        anchors.centerIn: parent; width: Math.min(600, root.width - 40)
        modal: true; title: root.statusTitle
        contentItem: ColumnLayout {
            Text { Layout.fillWidth: true; text: root.statusText; color: Theme.text; font.pixelSize: 19; wrapMode: Text.Wrap; textFormat: Text.PlainText }
            TouchButton { Layout.fillWidth: true; text: "Close"; onClicked: statusDialog.close() }
        }
    }
    Dialog {
        id: powerDialog
        anchors.centerIn: parent; width: Math.min(480, root.width - 40)
        modal: true; title: root.powerAction === "reboot" ? "Reboot device?" : "Power off device?"
        contentItem: ColumnLayout {
            Text { Layout.fillWidth: true; text: "This stops all honeypots and data collection."; color: Theme.text; font.pixelSize: 18; wrapMode: Text.Wrap }
            RowLayout {
                TouchButton { text: "Cancel"; onClicked: powerDialog.close() }
                TouchButton { text: "Confirm"; highlighted: true; onClicked: { backend.action(root.powerAction); powerDialog.close() } }
            }
        }
    }
    Rectangle {
        objectName: "startupOverlay"
        anchors.fill: parent; visible: root.startupVisible; color: Theme.background
        ColumnLayout {
            anchors.centerIn: parent; width: parent.width * .85; height: parent.height * .9; spacing: 12
            Image {
                id: bootImage
                Layout.fillWidth: true; Layout.fillHeight: true
                source: root.compact ? "../images/splash_43.png" : "../images/splash_8.png"
                fillMode: Image.PreserveAspectFit; smooth: false
            }
            Text { visible: bootImage.status === Image.Error; text: "Boot logo asset unavailable; see application log."; color: "#ff725f"; font.pixelSize: 14 }
            Text { Layout.alignment: Qt.AlignHCenter; text: "T-POT MOBILE / DEV-24.04.2"; color: Theme.text; font.pixelSize: 17 }
            Text { Layout.fillWidth: true; text: (root.state.fixture ? "SYNTHETIC DEVELOPMENT FIXTURE\n" : "") + root.dataStatus(); color: Theme.muted; font.pixelSize: 14; wrapMode: Text.Wrap; textFormat: Text.PlainText; horizontalAlignment: Text.AlignHCenter }
            TouchButton { Layout.alignment: Qt.AlignHCenter; text: "Open UI"; onClicked: root.startupVisible = false }
        }
    }
}
