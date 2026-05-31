document.addEventListener("DOMContentLoaded", function() {
    const sections = document.querySelectorAll(".section");

    sections.forEach(section => {
        const header = section.querySelector(".section-header");
        const content = section.querySelector(".section-content");

        if (!header || !content) return;

        header.setAttribute("aria-expanded", "false");

        const toggle = () => {
            const expanded = content.style.display !== "none" && content.style.display !== "";
            content.style.display = expanded ? "none" : "block";
            header.setAttribute("aria-expanded", String(!expanded));
        };

        header.addEventListener("click", toggle);
        header.addEventListener("keydown", (event) => {
            if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                toggle();
            }
        });
    });
});
