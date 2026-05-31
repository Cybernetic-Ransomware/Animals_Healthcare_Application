// Animal multi-select: shows checked animals as dismissible tag-pills above the checkbox list.
// Reuses .tag-pill / .tag-pill__remove CSS from the tag input component.
// Exposed as window.initAnimalSelect so modal.js can re-run it after htmx swaps.
// Re-entrant safe: removes any existing pill bar before building a new one.

(function () {
    "use strict";

    window.initAnimalSelect = function initAnimalSelect() {
        var wrapper = document.getElementById("field_additional_animals");
        if (!wrapper) return;

        // Remove any pill bar from a previous initialisation (re-entrant safe).
        var existing = wrapper.querySelector(".animal-select-pills");
        if (existing) existing.remove();

        var checkboxes = Array.from(wrapper.querySelectorAll("input[type='checkbox']"));
        if (!checkboxes.length) return;

        var pillBar = document.createElement("div");
        pillBar.className = "animal-select-pills";

        var fieldLabel = wrapper.querySelector("label[for]");
        var anchor = fieldLabel ? fieldLabel.nextElementSibling : null;
        if (anchor) {
            wrapper.insertBefore(pillBar, anchor);
        } else {
            wrapper.appendChild(pillBar);
        }

        function labelText(cb) {
            var lbl = cb.closest("label");
            if (lbl) return lbl.textContent.trim();
            var explicit = document.querySelector("label[for='" + cb.id + "']");
            return explicit ? explicit.textContent.trim() : cb.value;
        }

        function render() {
            pillBar.innerHTML = "";
            checkboxes.forEach(function (cb) {
                if (!cb.checked) return;

                var pill = document.createElement("span");
                pill.className = "tag-pill";

                var text = document.createElement("span");
                text.textContent = labelText(cb);

                var btn = document.createElement("button");
                btn.type = "button";
                btn.className = "tag-pill__remove";
                btn.setAttribute("aria-label", "Remove " + text.textContent);
                btn.textContent = "×";
                btn.addEventListener("click", function () {
                    cb.checked = false;
                    render();
                });

                pill.appendChild(text);
                pill.appendChild(btn);
                pillBar.appendChild(pill);
            });
        }

        checkboxes.forEach(function (cb) {
            cb.addEventListener("change", render);
        });

        render();
    };

    document.addEventListener("DOMContentLoaded", window.initAnimalSelect);
}());
