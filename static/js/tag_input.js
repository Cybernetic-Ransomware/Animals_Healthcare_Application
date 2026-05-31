// Tag pill input: enhances #id_note_tags (plain text) into an interactive pill UI.
// The original input is hidden and kept as the source of truth (comma-separated string).
// Exposed as window.initTagInput so modal.js can re-run it after htmx swaps.
// Re-entrant safe: removes any existing container before building a new one.

(function () {
    "use strict";

    function buildTagInput(field) {
        var parent = field.parentNode;

        // Remove any container from a previous initialisation (re-entrant safe).
        var existing = parent.querySelector(".tag-input-container");
        if (existing) existing.remove();

        field.style.display = "none";

        var container = document.createElement("div");
        container.className = "tag-input-container";
        parent.insertBefore(container, field.nextSibling);

        var textInput = document.createElement("input");
        textInput.type = "text";
        textInput.className = "tag-text-input";
        textInput.placeholder = "Add tag…";
        textInput.setAttribute("aria-label", "Add tag");
        container.appendChild(textInput);

        function getTags() {
            return field.value
                .split(",")
                .map(function (t) { return t.trim(); })
                .filter(Boolean);
        }

        function setTags(tags) {
            field.value = tags.join(", ");
        }

        function renderPills() {
            container.querySelectorAll(".tag-pill").forEach(function (p) { p.remove(); });
            getTags().forEach(function (tag, index) {
                var pill = document.createElement("span");
                pill.className = "tag-pill";

                var text = document.createElement("span");
                text.textContent = tag;

                var btn = document.createElement("button");
                btn.type = "button";
                btn.className = "tag-pill__remove";
                btn.setAttribute("aria-label", "Remove " + tag);
                btn.setAttribute("data-tag-index", index);
                btn.textContent = "×";
                btn.addEventListener("click", function () {
                    var i = parseInt(this.getAttribute("data-tag-index"), 10);
                    var tags = getTags();
                    if (i >= 0 && i < tags.length) {
                        tags.splice(i, 1);
                        setTags(tags);
                        renderPills();
                    }
                });

                pill.appendChild(text);
                pill.appendChild(btn);
                container.insertBefore(pill, textInput);
            });
        }

        function addTag(raw) {
            var tag = raw.trim().replace(/,/g, "");
            if (!tag) return;
            var tags = getTags();
            if (tags.indexOf(tag) === -1) {
                tags.push(tag);
                setTags(tags);
                renderPills();
            }
            textInput.value = "";
        }

        textInput.addEventListener("keydown", function (event) {
            if (event.key === "," || event.key === "Enter") {
                event.preventDefault();
                addTag(textInput.value);
            } else if (event.key === "Backspace" && !textInput.value) {
                var tags = getTags();
                if (tags.length) {
                    tags.pop();
                    setTags(tags);
                    renderPills();
                }
            }
        });

        textInput.addEventListener("blur", function () {
            if (textInput.value.trim()) addTag(textInput.value);
        });

        container.addEventListener("click", function () { textInput.focus(); });

        renderPills();
    }

    window.initTagInput = function initTagInput() {
        var field = document.getElementById("id_note_tags");
        if (!field) return;
        buildTagInput(field);
    };

    document.addEventListener("DOMContentLoaded", window.initTagInput);
}());
