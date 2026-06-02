// Timeline layout: equalise heights of list-item divs so the connector line aligns.
// initTimeline() is called on window load and after htmx swaps.

function initTimeline() {
    const elements = document.querySelectorAll(".timeline li > div");
    if (elements.length > 0) {
        setEqualHeights(elements);
    }
}

function setEqualHeights(el) {
    let counter = 0;
    for (let i = 0; i < el.length; i++) {
        const singleHeight = el[i].offsetHeight;
        if (counter < singleHeight) {
            counter = singleHeight;
        }
    }
    for (let i = 0; i < el.length; i++) {
        el[i].style.height = counter + "px";
    }
}

window.addEventListener("load", initTimeline);
