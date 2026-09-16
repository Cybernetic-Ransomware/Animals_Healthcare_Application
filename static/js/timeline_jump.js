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

    // Tab timelines: node anchors follow the pattern "tlmonth-<slug>-YYYY-MM"
    var nodes = document.querySelectorAll("[id$='-" + month + "']");
    for (var i = 0; i < nodes.length; i++) {
        if (nodes[i].id.indexOf("tlmonth-") === 0) {
            scrollToMonthNode(nodes[i]);
            return;
        }
    }
}

// Reads the container's actual overflow-x instead of re-checking the breakpoint here, so this stays correct even if timeline.css's breakpoint changes.
function scrollToMonthNode(node) {
    var container = node.closest("ol");
    if (container && getComputedStyle(container).overflowX === "scroll") {
        scrollAxisHorizontally(container, node);
        return;
    }
    // Vertical mobile axis: the node is in normal document flow, so scroll the page.
    node.scrollIntoView({ behavior: "smooth", block: "start" });
}

// Scrolls the ol's own horizontal container — scrollIntoView() would also drag the page vertically, which is wrong for a horizontal axis.
function scrollAxisHorizontally(container, node) {
    var containerRect = container.getBoundingClientRect();
    var nodeRect = node.getBoundingClientRect();
    var target = container.scrollLeft + (nodeRect.left - containerRect.left);
    container.scrollTo({ left: target, behavior: "smooth" });
}

window.addEventListener("load", initTimelineJump);
