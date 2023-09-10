document.addEventListener("DOMContentLoaded", function() {
    const sections = document.querySelectorAll(".section");

    sections.forEach(section => {
        const header = section.querySelector(".section-header");
        const content = section.querySelector(".section-content");

        header.addEventListener("click", () => {
            if (content.style.display === "none" || content.style.display === "") {
                content.style.display = "block";
            } else {
                content.style.display = "none";
            }
        });
    });
});
