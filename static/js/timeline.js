// Timeline layout: equalise heights of list-item divs so the connector line aligns,
// and size the axis's vertical padding to match. Each .timeline instance is measured
// independently so unrelated timelines never force each other's card/axis size
// (e.g. the Notes tab renders a history timeline and a biometrics timeline together).
// initTimeline() is called on window load and after htmx swaps.

function initTimeline() {
    document.querySelectorAll(".timeline").forEach(function (timeline) {
        const ol = timeline.querySelector("ol");
        const cards = timeline.querySelectorAll("li > div");
        if (!ol || cards.length === 0) {
            return;
        }
        const maxHeight = setEqualHeights(cards);
        setAxisPadding(ol, maxHeight);
    });
}

function setEqualHeights(elements) {
    // Clear any height a previous run set, otherwise a card can never shrink
    // back down after "Load older" or an htmx swap removes its taller siblings.
    for (let i = 0; i < elements.length; i++) {
        elements[i].style.height = "";
    }
    let maxHeight = 0;
    for (let i = 0; i < elements.length; i++) {
        const singleHeight = elements[i].offsetHeight;
        if (maxHeight < singleHeight) {
            maxHeight = singleHeight;
        }
    }
    for (let i = 0; i < elements.length; i++) {
        elements[i].style.height = maxHeight + "px";
    }
    return maxHeight;
}

// Cards sit 16px above (odd) or below (even) the axis line via absolute
// positioning (see .timeline ol li:nth-child(odd/even) div in timeline.css), so
// the ol needs at least maxHeight + 16px of padding on each side, plus a little
// breathing room, to avoid clipping the tallest card. A single fixed padding
// can't fit every timeline's content, so it's computed per instance here.
function setAxisPadding(ol, maxHeight) {
    const padding = maxHeight + 32;
    ol.style.paddingTop = padding + "px";
    ol.style.paddingBottom = padding + "px";
}

window.addEventListener("load", initTimeline);
