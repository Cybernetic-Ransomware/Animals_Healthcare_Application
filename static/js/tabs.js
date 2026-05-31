// Tab navigation: active-state management and per-panel script re-initialisation.
// Loaded globally from base.html; all handlers are external (CSP: no inline JS).

(function () {
    "use strict";

    function getActiveSlugFromPath() {
        // Match paths like /animals/<uuid>/tab/<slug>/
        const match = window.location.pathname.match(/\/tab\/([^/]+)\/?$/);
        return match ? match[1] : null;
    }

    function syncActiveTab(slug) {
        const nav = document.querySelector(".tab-nav");
        if (!nav || !slug) return;
        nav.querySelectorAll("[role='tab']").forEach(function (link) {
            link.classList.toggle("active", link.dataset.tab === slug);
        });
    }

    // Delegate tab clicks: update active class immediately without waiting for swap.
    document.addEventListener("click", function (event) {
        const link = event.target.closest(".tab-nav [role='tab']");
        if (!link) return;
        syncActiveTab(link.dataset.tab);
    });

    // Resync active tab when navigating back/forward.
    window.addEventListener("popstate", function () {
        syncActiveTab(getActiveSlugFromPath());
    });

    // After htmx injects a new tab panel, signal each per-page script to re-bind.
    document.addEventListener("htmx:afterSwap", function () {
        if (typeof initExpandingSections === "function") {
            initExpandingSections();
        }
        if (typeof initTimeline === "function") {
            initTimeline();
        }
        if (typeof initPinButton === "function") {
            initPinButton();
        }
        if (typeof initTimelineJump === "function") {
            initTimelineJump();
        }
    });
}());
