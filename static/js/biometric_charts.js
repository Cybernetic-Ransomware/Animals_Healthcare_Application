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

function initBiometricCharts() {
    var dataEl = document.getElementById("biometric-chart-data");
    if (!dataEl) return;

    var series = JSON.parse(dataEl.textContent);

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
