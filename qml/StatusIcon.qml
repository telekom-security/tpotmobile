import QtQuick
import "Theme.js" as Theme

Item {
    id: icon
    objectName: "statusIcon"
    property string kind: "wifi"
    property var value: null
    property bool charging: false
    property color accent: Theme.magenta
    signal clicked()
    implicitWidth: 46
    implicitHeight: 46
    Canvas {
        id: drawing
        objectName: "statusDrawing"
        anchors.fill: parent
        onPaint: {
            const ctx = getContext("2d")
            ctx.reset()
            ctx.clearRect(0, 0, width, height)
            ctx.translate(width / 2 - 16, height / 2 - 16)
            ctx.lineWidth = 2
            ctx.lineCap = "round"
            ctx.lineJoin = "round"
            ctx.strokeStyle = icon.accent
            ctx.fillStyle = icon.accent
            if (icon.kind === "fixture") {
                ctx.beginPath(); ctx.moveTo(16, 5); ctx.lineTo(27, 16)
                ctx.lineTo(16, 27); ctx.lineTo(5, 16); ctx.closePath(); ctx.stroke()
            } else if (icon.kind === "live") {
                ctx.beginPath(); ctx.arc(16, 16, 11, 0, Math.PI * 2); ctx.stroke()
                ctx.beginPath(); ctx.arc(16, 16, 7, 0, Math.PI * 2); ctx.fill()
            } else if (icon.kind === "held") {
                ctx.fillRect(10, 7, 4, 18); ctx.fillRect(18, 7, 4, 18)
            } else if (icon.kind === "warning") {
                ctx.beginPath(); ctx.arc(16, 16, 11, 0, Math.PI * 2); ctx.stroke()
                ctx.beginPath(); ctx.moveTo(16, 9); ctx.lineTo(16, 18); ctx.stroke()
                ctx.beginPath(); ctx.arc(16, 23, 1.4, 0, Math.PI * 2); ctx.fill()
            } else if (icon.kind === "wifi") {
                const known = typeof icon.value === "number"
                for (let i = 0; i < 3; ++i) {
                    ctx.strokeStyle = known && icon.value > [65, 35, 0][i] ? Theme.magenta : "#443b4c"
                    ctx.beginPath()
                    ctx.arc(16, 25, [20, 13.33, 6.67][i], -Math.PI * .75, -Math.PI * .25)
                    ctx.stroke()
                }
                ctx.fillStyle = known && icon.value > 0 ? Theme.magenta : "#443b4c"
                ctx.beginPath(); ctx.arc(16, 25, 1.6, 0, Math.PI * 2); ctx.fill()
                if (!known || icon.value === 0) {
                    ctx.strokeStyle = "#f0907c"
                    ctx.beginPath(); ctx.moveTo(5, 5); ctx.lineTo(27, 27); ctx.stroke()
                }
            } else if (icon.kind === "battery") {
                ctx.strokeStyle = typeof icon.value === "number" && icon.value < 10 ? "#ff725f" : Theme.text
                ctx.strokeRect(2, 6, 26, 20)
                ctx.fillStyle = Theme.text; ctx.fillRect(30, 11, 2, 10)
                ctx.fillStyle = typeof icon.value === "number" && icon.value < 10 ? "#ff725f" : Theme.magenta
                if (typeof icon.value === "number")
                    ctx.fillRect(5, 9, 20 * Math.max(0, Math.min(100, icon.value)) / 100, 14)
                if (icon.charging) {
                    ctx.strokeStyle = "#fff"
                    ctx.beginPath(); ctx.moveTo(15, 21); ctx.lineTo(15, 11)
                    ctx.moveTo(11, 15); ctx.lineTo(15, 11); ctx.lineTo(19, 15); ctx.stroke()
                } else if (typeof icon.value !== "number") {
                    ctx.fillStyle = Theme.text; ctx.font = "16px sans-serif"; ctx.textAlign = "center"; ctx.fillText("?", 15, 22)
                }
            }
        }
    }
    onValueChanged: drawing.requestPaint()
    onChargingChanged: drawing.requestPaint()
    onKindChanged: drawing.requestPaint()
    onAccentChanged: drawing.requestPaint()
    Component.onCompleted: drawing.requestPaint()
    TapHandler { onTapped: icon.clicked() }
    Accessible.role: Accessible.Button
    Accessible.name: kind === "wifi" ? "Wi-Fi details" : kind === "battery" ? charging ? "Battery charging; details" : "Battery details" : kind === "fixture" ? "Synthetic fixture information" : kind === "warning" ? "Data status" : "Follow live"
    Accessible.onPressAction: clicked()
}
