// Accordion sections: toggle .section-content visibility on header click.
// initExpandingSections() is called on DOMContentLoaded and after htmx swaps.

function initExpandingSections() {
    document.querySelectorAll(".section").forEach(function (section) {
        // Skip sections that were already initialised.
        if (section.dataset.expandingInit) return;
        section.dataset.expandingInit = "1";

        const header = section.querySelector(".section-header");
        const content = section.querySelector(".section-content");

        if (!header || !content) return;

        header.setAttribute("aria-expanded", "false");

        const toggle = function () {
            const expanded = content.style.display !== "none" && content.style.display !== "";
            content.style.display = expanded ? "none" : "block";
            header.setAttribute("aria-expanded", String(!expanded));
        };

        header.addEventListener("click", toggle);
        header.addEventListener("keydown", function (event) {
            if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                toggle();
            }
        });
    });
}

document.addEventListener("DOMContentLoaded", initExpandingSections);
