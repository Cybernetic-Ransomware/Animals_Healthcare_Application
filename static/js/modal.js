// Modal: open/close <dialog id="ahc-modal"> driven by htmx swaps.
// Loaded globally from base.html; all handlers are external (CSP: no inline JS).

(function () {
    "use strict";

    var modal = document.getElementById("ahc-modal");
    if (!modal) return;

    var modalTitle = document.getElementById("modal-title");

    // Populate modal title from the triggering element before the htmx request fires.
    document.addEventListener("htmx:beforeRequest", function (event) {
        if (event.detail.target.id !== "modal-body") return;
        var elt = event.detail.elt;
        if (elt && modalTitle && elt.dataset.modalTitle) {
            modalTitle.textContent = elt.dataset.modalTitle;
        }
    });

    // Show modal and re-init per-form JS after htmx injects content.
    document.addEventListener("htmx:afterSwap", function (event) {
        if (event.detail.target.id !== "modal-body") return;
        if (!modal.open) modal.showModal();
        if (typeof window.initNoteForm === "function") window.initNoteForm();
        if (typeof window.initTagInput === "function") window.initTagInput();
        if (typeof window.initAnimalSelect === "function") window.initAnimalSelect();
    });

    // Close on backdrop click (clicking the <dialog> element itself, not the article).
    modal.addEventListener("click", function (event) {
        if (event.target === modal) modal.close();
    });

    // Close via [data-close-modal] (delegated — survives htmx content replacement).
    document.addEventListener("click", function (event) {
        if (event.target.closest("[data-close-modal]")) modal.close();
    });

    // Wire Pico's header close button.
    var closeBtn = document.getElementById("modal-close");
    if (closeBtn) {
        closeBtn.addEventListener("click", function () { modal.close(); });
    }
}());
