// Modal: open/close <dialog id="ahc-modal"> driven by htmx swaps.
// Loaded globally from base.html; all handlers are external (CSP: no inline JS).

(function () {
    "use strict";

    var modal = document.getElementById("ahc-modal");
    if (!modal) return;

    var modalTitle = document.getElementById("modal-title");
    var modalBody = document.getElementById("modal-body");

    // Captured only in "beforeRequest" — other htmx events reuse event.detail.elt for unrelated nodes.
    var lastTrigger = null;

    // Populate modal title from the triggering element before the htmx request fires.
    document.addEventListener("htmx:beforeRequest", function (event) {
        if (event.detail.target.id !== "modal-body") return;
        var elt = event.detail.elt;
        lastTrigger = elt || null;
        if (elt && modalTitle && elt.dataset.modalTitle) {
            modalTitle.textContent = elt.dataset.modalTitle;
        }
    });

    // Excludes disabled, tabindex="-1", and hidden (offsetParent-null) elements from being a focus target.
    function isFocusable(el) {
        if (!el) return false;
        if (el.disabled) return false;
        if (el.tabIndex < 0) return false;
        if (el.offsetParent === null) return false;
        return true;
    }

    // Native <dialog> defaults to focusing the dialog/article itself, not a form control — this picks a deterministic target instead.
    function focusInitialElement() {
        if (!modalBody) return;

        var explicit = modalBody.querySelector("[autofocus]");
        if (isFocusable(explicit)) {
            explicit.focus();
            return;
        }

        var candidates = modalBody.querySelectorAll(
            "input:not([type=hidden]):not([type=checkbox]):not([type=radio])" +
            ":not([type=submit]):not([type=button]):not([type=file]), select, textarea"
        );
        for (var i = 0; i < candidates.length; i++) {
            if (isFocusable(candidates[i])) {
                candidates[i].focus();
                return;
            }
        }

        if (closeBtn) closeBtn.focus();
    }

    // Focus is chosen after initNoteForm() etc. so conditional-visibility scripts have already hidden/disabled fields.
    document.addEventListener("htmx:afterSwap", function (event) {
        if (event.detail.target.id !== "modal-body") return;
        if (!modal.open) modal.showModal();
        if (typeof window.initNoteForm === "function") window.initNoteForm();
        if (typeof window.initTagInput === "function") window.initTagInput();
        if (typeof window.initAnimalSelect === "function") window.initAnimalSelect();
        // Deferred because showModal()'s async default-focus step would otherwise clobber a synchronous .focus() here.
        requestAnimationFrame(focusInitialElement);
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

    // Native "close" fires for every close path (X, backdrop, Escape, data-close-modal) — one listener covers them all.
    modal.addEventListener("close", function () {
        var trigger = lastTrigger;
        lastTrigger = null;
        if (trigger && document.contains(trigger) && isFocusable(trigger)) {
            trigger.focus();
        }
    });
}());
