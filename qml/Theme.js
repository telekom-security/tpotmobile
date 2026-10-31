.pragma library

const background = "#080a10"
const panel = "#12141e"
const line = "#2c2538"
const muted = "#b9b1c1"
const magenta = "#e20074"
const text = "#eee9f1"
const palette = ["#e20074", "#eda74c", "#78cddd", "#a48bec", "#8bca91", "#dc829d"]
const known = {"cowrie": palette[0], "dionaea": palette[1], "tanner": palette[2], "honeytrap": palette[3]}

function honeypotColor(name) {
    const key = String(name || "").toLowerCase()
    if (known[key])
        return known[key]
    let hash = 0
    for (let i = 0; i < key.length; ++i)
        hash = (hash * 31 + key.charCodeAt(i)) >>> 0
    return palette[hash % palette.length]
}

function count(value, compact) {
    if (typeof value !== "number" || !isFinite(value))
        return "--"
    if (!compact)
        return value.toLocaleString(Qt.locale("en_US"), "f", 0)
    for (const entry of [[1000000, "M"], [1000, "K"]]) {
        if (value >= entry[0]) {
            const rounded = Number((value / entry[0]).toFixed(value < entry[0] * 10 ? 1 : 0))
            return rounded === 1000 && entry[1] === "K" ? "1M" : rounded + entry[1]
        }
    }
    return String(value)
}

function time(timestamp) {
    return new Date(timestamp).toLocaleTimeString(Qt.locale("en_GB"), "HH:mm:ss")
}

function timestamp(value) {
    return new Date(value).toLocaleString(Qt.locale("en_GB"), "yyyy-MM-dd HH:mm:ss t")
}

function service(event) {
    const port = detail(event, "Port")
    return (port ? port + " / " : "") + (event.protocol || "Unknown")
}

function coordinates(event) {
    if (typeof event.latitude !== "number" || typeof event.longitude !== "number")
        return "Unknown"
    return Math.abs(event.latitude).toFixed(2) + "° " + (event.latitude < 0 ? "S" : "N")
           + " / " + Math.abs(event.longitude).toFixed(2) + "° " + (event.longitude < 0 ? "W" : "E")
}

function detail(event, label) {
    if (!event || !event.details)
        return ""
    for (const row of event.details)
        if (row.label === label)
            return row.value
    return ""
}
