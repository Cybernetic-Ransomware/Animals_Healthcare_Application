// Timeline layout: on desktop, equalise card heights and size the axis's vertical padding to match; on mobile (plain vertical feed) any leftover inline styles from a prior desktop layout are cleared instead. Runs on load, after htmx swaps, and on matchMedia breakpoint changes (not resize).

const TIMELINE_DESKTOP_QUERY = "(min-width: 768px)";

function initTimeline() {
    const isDesktop = window.matchMedia(TIMELINE_DESKTOP_QUERY).matches;
    document.querySelectorAll(".timeline").forEach(function (timeline) {
        const ol = timeline.querySelector("ol");
        const cards = timeline.querySelectorAll("li > div");
        if (!ol) {
            return;
        }
        if (!isDesktop) {
            resetMobileLayout(ol, cards);
            return;
        }
        if (cards.length === 0) {
            return;
        }
        const maxHeight = setEqualHeights(cards);
        setAxisPadding(ol, maxHeight);
    });
}

// Clears any inline height/padding a previous desktop layout left behind.
function resetMobileLayout(ol, cards) {
    ol.style.paddingTop = "";
    ol.style.paddingBottom = "";
    for (let i = 0; i < cards.length; i++) {
        cards[i].style.height = "";
    }
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
// positioning (see .timeline ol li:nth-child(odd/even) > div in timeline.css), so
// the ol needs at least maxHeight + 16px of padding on each side, plus a little
// breathing room, to avoid clipping the tallest card. A single fixed padding
// can't fit every timeline's content, so it's computed per instance here.
function setAxisPadding(ol, maxHeight) {
    const padding = maxHeight + 32;
    ol.style.paddingTop = padding + "px";
    ol.style.paddingBottom = padding + "px";
}

window.addEventListener("load", initTimeline);
window.matchMedia(TIMELINE_DESKTOP_QUERY).addEventListener("change", initTimeline);
