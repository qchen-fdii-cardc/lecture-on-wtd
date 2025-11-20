document.addEventListener("DOMContentLoaded", () => {
    const images = document.querySelectorAll(".bd-content img");
    images.forEach((img) => {
        if (img.classList.contains("logo") || img.closest(".logo-container")) {
            return;
        }
        img.style.maxWidth = "50%";
        img.style.height = "auto";
    });
});
