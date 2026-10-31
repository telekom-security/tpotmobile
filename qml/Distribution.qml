import QtQuick
import QtQuick.Layouts
import "Theme.js" as Theme

Panel {
    id: panel
    property string title: ""
    property var entries: []
    property bool countries: false
    property bool compact: false
    property int revision: 0
    FontMetrics { id: nameMetrics; font.family: uiFontFamily; font.pixelSize: panel.compact ? 14 : 17 }
    FontMetrics { id: numberMetrics; font.family: uiMonoFamily; font.pixelSize: panel.compact ? 15 : 18 }
    function colorAt(index) {
        return countries ? Theme.palette[index % Theme.palette.length] : Theme.honeypotColor(entries[index].name)
    }
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: panel.compact ? 10 : 16
        spacing: 8
        Text { text: panel.title; color: Theme.muted; font.pixelSize: panel.compact ? 12 : 14 }
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 8
            Canvas {
                id: donut
                objectName: "distributionDonut"
                Layout.preferredWidth: panel.width * .42
                Layout.fillHeight: true
                onWidthChanged: requestPaint()
                onHeightChanged: requestPaint()
                onPaint: {
                    const ctx = getContext("2d")
                    ctx.clearRect(0, 0, width, height)
                    const entries = panel.entries || []
                    const total = entries.reduce((sum, entry) => sum + entry.count, 0)
                    if (!total) {
                        ctx.fillStyle = Theme.muted; ctx.font = "16px sans-serif"; ctx.textAlign = "center"; ctx.fillText("No data", width / 2, height / 2)
                        return
                    }
                    const radius = Math.min(width, height) * .42
                    let start = -Math.PI / 2
                    entries.forEach((entry, index) => {
                        const end = start + entry.count / total * Math.PI * 2
                        ctx.beginPath(); ctx.arc(width / 2, height / 2, radius, start, end)
                        ctx.strokeStyle = panel.colorAt(index); ctx.lineWidth = radius * .35; ctx.stroke()
                        start = end
                    })
                    ctx.textAlign = "center"; ctx.fillStyle = Theme.text
                    ctx.font = (panel.compact ? "22" : "30") + "px monospace"
                    ctx.fillText(Theme.count(total, panel.compact), width / 2, height / 2 + 4)
                    ctx.fillStyle = Theme.muted; ctx.font = "12px sans-serif"
                    ctx.fillText("EVENTS", width / 2, height / 2 + 25)
                }
            }
            Item {
                id: legendArea
                objectName: "legendArea"
                Layout.fillWidth: true
                Layout.fillHeight: true
                ListView {
                    id: legend
                    objectName: "distributionLegend"
                    readonly property real iconWidth: panel.countries ? panel.compact ? 24 : 30 : 9
                    readonly property real numberWidth: Math.max(28, ...(panel.entries || []).map(entry => numberMetrics.advanceWidth(Theme.count(entry.count, panel.compact))))
                    readonly property real nameWidth: Math.max(0, ...(panel.entries || []).map(entry => nameMetrics.advanceWidth(entry.name)))
                    readonly property real nameNumberGap: panel.compact ? 16 : 32
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    width: Math.min(parent.width, iconWidth + 6 + nameWidth + nameNumberGap + numberWidth)
                    height: Math.min(parent.height, count * (panel.compact ? 28 : 40))
                    clip: true
                    model: panel.entries || []
                    delegate: Item {
                        id: legendRow
                        required property var modelData
                        required property int index
                        readonly property rect capitalInk: nameMetrics.tightBoundingRect("H")
                        readonly property real nameInkCenter: legendName.y + legendName.baselineOffset + capitalInk.y + capitalInk.height / 2
                        width: legend.width
                        height: panel.compact ? 28 : 40
                        Image {
                            id: flagImage
                            objectName: "legendFlag"
                            width: legend.iconWidth
                            height: panel.compact ? 16 : 20
                            y: legendRow.nameInkCenter - height / 2
                            visible: panel.countries && status === Image.Ready
                            source: panel.countries && modelData.code && /^[a-z]{2}$/.test(modelData.code) ? "../flags/" + modelData.code + ".png" : ""
                            fillMode: Image.PreserveAspectFit
                            sourceSize: Qt.size(60, 40)
                            Rectangle {
                                x: (flagImage.width - flagImage.paintedWidth) / 2
                                y: (flagImage.height - flagImage.paintedHeight) / 2
                                width: flagImage.paintedWidth
                                height: flagImage.paintedHeight
                                color: "transparent"
                                border.color: "#55475b"
                                visible: flagImage.status === Image.Ready
                            }
                        }
                        Rectangle { visible: !panel.countries; y: legendRow.nameInkCenter - height / 2; width: 9; height: 9; radius: 5; color: panel.colorAt(index) }
                        Text {
                            id: legendName
                            objectName: "legendName"
                            x: legend.iconWidth + 6
                            width: Math.max(0, parent.width - x - legend.nameNumberGap - legend.numberWidth)
                            anchors.verticalCenter: parent.verticalCenter
                            text: modelData.name; color: Theme.text; font.pixelSize: panel.compact ? 14 : 17
                            elide: Text.ElideRight; textFormat: Text.PlainText
                        }
                        Text {
                            objectName: "legendNumber"
                            anchors.right: parent.right
                            anchors.verticalCenter: parent.verticalCenter
                            width: legend.numberWidth
                            horizontalAlignment: Text.AlignRight
                            text: Theme.count(modelData.count, panel.compact); color: Theme.text; font.family: uiMonoFamily; font.pixelSize: panel.compact ? 15 : 18
                        }
                    }
                }
            }
        }
    }
    onRevisionChanged: donut.requestPaint()
    onEntriesChanged: donut.requestPaint()
}
