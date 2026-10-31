import QtQuick
import "Theme.js" as Theme

Canvas {
    id: chart
    objectName: "histogram"
    property var values: []
    property var times: []
    property bool grid: false
    property int revision: 0
    property color accent: Theme.magenta
    property bool compact: false
    onRevisionChanged: requestPaint()
    onValuesChanged: requestPaint()
    onTimesChanged: requestPaint()
    onWidthChanged: requestPaint()
    onHeightChanged: requestPaint()
    Component.onCompleted: requestPaint()
    onPaint: {
        const ctx = getContext("2d")
        ctx.clearRect(0, 0, width, height)
        if (!values || !values.length)
            return
        const maximum = Math.max(1, ...values)
        const left = grid ? 40 : 0, right = width - 8, top = 12, bottom = height - (grid ? 32 : 8)
        if (bottom <= top || right <= left)
            return
        if (grid) {
            ctx.font = (compact ? "11" : "13") + "px monospace"
            ctx.strokeStyle = "#37303f"; ctx.fillStyle = Theme.muted; ctx.lineWidth = .5
            for (let i = 0; i <= 4; ++i) {
                const y = top + (bottom - top) * i / 4
                ctx.beginPath(); ctx.moveTo(left, y); ctx.lineTo(right, y); ctx.stroke()
                ctx.textAlign = "left"; ctx.fillText(Theme.count(Math.round(maximum * (1 - i / 4)), compact), 0, y + 4)
            }
            const markers = width < 420 ? 2 : 4
            for (let i = 0; i <= markers; ++i) {
                const x = left + (right - left) * i / markers
                ctx.beginPath(); ctx.moveTo(x, top); ctx.lineTo(x, bottom); ctx.stroke()
                if (times && times.length) {
                    const timestamp = times[Math.round((times.length - 1) * i / markers)]
                    const label = new Date(timestamp).toLocaleTimeString(Qt.locale("en_GB"), "HH:mm")
                    ctx.textAlign = i === 0 ? "left" : i === markers ? "right" : "center"
                    ctx.fillText(label, x, height - 10)
                }
            }
        }
        ctx.fillStyle = accent
        const step = (right - left) / values.length
        for (let i = 0; i < values.length; ++i) {
            if (values[i] <= 0)
                continue
            const barHeight = Math.max(1, values[i] / maximum * (bottom - top))
            ctx.fillRect(left + i * step + 1, bottom - barHeight, Math.max(1, step - 2), barHeight)
        }
    }
}
