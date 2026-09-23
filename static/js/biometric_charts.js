// Biometric history charts (Chart.js). Reads chart series from the json_script blob
// rendered by _biometrics.html and draws one line chart per <canvas data-biometric-chart>.
// Called on initial page load (DOMContentLoaded) and after every htmx tab swap (tabs.js) —
// direct navigation to /tab/biometrics/ must show the chart without an extra tab click.
//
// x axis is "linear" (millisecond timestamps + Intl.DateTimeFormat tick labels), not
// "time"/"timeseries", so no Chart.js date-adapter plugin needs to be vendored.

// Backend sends plain "YYYY-MM-DD" calendar dates (the whole point of the date-resolution
// cascade is picking the correct LOCAL day). `new Date("YYYY-MM-DD")` parses as UTC midnight,
// which a browser in a negative-offset timezone would then render as the previous day — so
// dates are parsed and formatted as UTC throughout, treating them as date-only values rather
// than instants tied to the viewer's clock.
function dateToTimestamp(isoDate) {
    var parts = isoDate.split("-").map(Number);
    return Date.UTC(parts[0], parts[1] - 1, parts[2]);
}

function formatChartDate(timestamp) {
    return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeZone: "UTC" }).format(new Date(timestamp));
}

// Chart.js's linear scale has no notion of "a sensible span of time" — with only one
// data point min===max, and its "nice number" tick algorithm then picks round bounds
// relative to the sheer magnitude of millisecond-since-epoch values (~1.7e12), producing
// an axis stretching years in either direction around a single dot. Pin an explicit,
// tight window instead of letting it autoscale.
var SINGLE_POINT_WINDOW_MS = 14 * 24 * 60 * 60 * 1000;

function initBiometricCharts() {
    var dataEl = document.getElementById("biometric-chart-data");
    if (!dataEl) return;

    // Right after an htmx innerHTML swap (or on first paint), the browser hasn't
    // necessarily committed layout for the freshly-inserted canvas wrappers yet —
    // Chart.js measures its container synchronously at construction time, and without
    // this rAF it reproducibly locks in its ~300px fallback width instead of the real
    // (wider) card width. One frame is enough for layout to settle.
    requestAnimationFrame(function () {
        _renderBiometricCharts(JSON.parse(dataEl.textContent));
    });
}

function _renderBiometricCharts(series) {
    document.querySelectorAll("canvas[data-biometric-chart]").forEach(function (canvas) {
        var s = series[Number(canvas.dataset.seriesIndex)];
        if (!s || !s.points || s.points.length === 0) return;

        var existing = typeof Chart !== "undefined" && Chart.getChart ? Chart.getChart(canvas) : null;
        if (existing) existing.destroy();

        var points = s.points.map(function (p) {
            return { x: dateToTimestamp(p.date), y: p.value };
        });
        var singlePoint = points.length === 1;

        new Chart(canvas, {
            type: "line",
            data: {
                datasets: [
                    {
                        label: s.label,
                        data: points,
                        showLine: !singlePoint,
                        pointRadius: singlePoint ? 5 : 3,
                        tension: 0.15,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        type: "linear",
                        min: singlePoint ? points[0].x - SINGLE_POINT_WINDOW_MS : undefined,
                        max: singlePoint ? points[0].x + SINGLE_POINT_WINDOW_MS : undefined,
                        ticks: {
                            callback: formatChartDate,
                        },
                    },
                    y: {
                        title: { display: true, text: s.unit },
                    },
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            title: function (items) {
                                if (!items.length) return "";
                                return formatChartDate(items[0].parsed.x);
                            },
                            label: function (item) {
                                return item.parsed.y + " " + s.unit;
                            },
                        },
                    },
                },
            },
        });
    });
}

document.addEventListener("DOMContentLoaded", initBiometricCharts);
