document.addEventListener("DOMContentLoaded", () => {
  // Open modal
  document.querySelectorAll("[data-modal-open]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const modalId = btn.getAttribute("data-modal-open");
      const modal = document.getElementById(modalId);
      const box = modal.querySelector(".modal-box");

      modal.classList.remove("hidden");
      setTimeout(() => {
        box.classList.remove("opacity-0", "scale-95");
        box.classList.add("opacity-100", "scale-100");
      }, 10);
    });
  });

  // Close modal
  document.querySelectorAll("[data-modal-close]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const modalId = btn.getAttribute("data-modal-close");
      const modal = document.getElementById(modalId);
      const box = modal.querySelector(".modal-box");

      box.classList.remove("opacity-100", "scale-100");
      box.classList.add("opacity-0", "scale-95");
      setTimeout(() => {
        modal.classList.add("hidden");
      }, 300);
    });
  });
});
