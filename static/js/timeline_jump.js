// Scroll the timeline to the target month after a month-jump swap or on initial page load.
// initTimelineJump() is called on window load (deep-link support) and from tabs.js
// after every htmx swap.

function initTimelineJump() {
    var marker = document.querySelector("[data-scroll-month]");
    if (!marker) return;
    var month = marker.getAttribute("data-scroll-month");
    if (!month) return;

    // Full-page timeline: vertical scroll to <h4 id="month-YYYY-MM">
    var anchor = document.getElementById("month-" + month);
    if (anchor) {
        anchor.scrollIntoView({ behavior: "smooth", block: "start" });
        return;
    }

    // Tab horizontal timelines: node anchors follow the pattern "tlmonth-<slug>-YYYY-MM"
    var nodes = document.querySelectorAll("[id$='-" + month + "']");
    for (var i = 0; i < nodes.length; i++) {
        if (nodes[i].id.indexOf("tlmonth-") === 0) {
            nodes[i].scrollIntoView({ behavior: "smooth", block: "nearest", inline: "start" });
            return;
        }
    }
}

window.addEventListener("load", initTimelineJump);
