document.addEventListener("DOMContentLoaded", () => {
    const images = document.querySelectorAll(".bd-content img");
    images.forEach((img) => {
        if (img.dataset.processed === "true") {
            return;
        }

        if (img.classList.contains("logo") || img.closest(".logo-container")) {
            return;
        }

        const existingFigure = img.closest("figure.image-center");
        let figure = existingFigure;

        if (!figure) {
            figure = document.createElement("figure");
            figure.classList.add("image-center");
            figure.style.margin = "1.5rem auto";
            figure.style.textAlign = "center";
            figure.style.display = "block";

            const parent = img.parentNode;
            parent.insertBefore(figure, img);
            figure.appendChild(img);
        }

        img.style.maxWidth = "50%";
        img.style.height = "auto";
        img.style.display = "block";
        img.style.margin = "0 auto";

        const altText = img.getAttribute("alt");
        const hasCaption = figure.querySelector("figcaption");

        if (altText && !hasCaption) {
            const caption = document.createElement("figcaption");
            caption.textContent = altText;
            caption.style.marginTop = "0.5rem";
            caption.style.fontSize = "0.95rem";
            caption.style.color = "#555";
            caption.style.textAlign = "center";
            figure.appendChild(caption);
        }

        img.dataset.processed = "true";
    });
});
