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
            scrollAxisToNode(nodes[i]);
            return;
        }
    }
}

// Scroll the axis's own horizontal scroll container (the <ol>) so the target month
// comes into view. scrollIntoView() would also drag the whole page vertically to
// satisfy the node's block-axis visibility, which is not wanted for a horizontal axis.
function scrollAxisToNode(node) {
    var container = node.closest("ol");
    if (!container) {
        node.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "start" });
        return;
    }
    var containerRect = container.getBoundingClientRect();
    var nodeRect = node.getBoundingClientRect();
    var target = container.scrollLeft + (nodeRect.left - containerRect.left);
    container.scrollTo({ left: target, behavior: "smooth" });
}

window.addEventListener("load", initTimelineJump);
