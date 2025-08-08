// Global search handler: triggers search only on Enter or when cleared
// Prevents API calls on every keystroke

document.addEventListener(
  "keyup",
  function (e) {
    const target = e.target;
    if (
      target.tagName !== "INPUT" ||
      (target.type !== "text" && target.type !== "search")
    ) {
      return;
    }
    const idName = (target.name || "") + (target.id || "");
    if (!idName.toLowerCase().includes("search")) {
      return;
    }

    const form = target.closest("form");
    const dropdown = target.parentElement.querySelector("#dropdown");
    const searchText = target.parentElement.querySelector(".search_text");

    if (dropdown) {
      if (target.value) {
        $(dropdown).show();
        if (searchText) {
          $(searchText).html(target.value);
        }
      } else {
        $(dropdown).hide();
      }
    }

    if (e.key === "Enter" || target.value.trim() === "") {
      if (form) {
        const button = form.querySelector(
          ".filterButton, #hiddenSubmit, [id$='FilterButton'], button[type='submit'], input[type='submit']"
        );
        if (button) {
          button.click();
        }
      }
    } else {
      e.stopImmediatePropagation();
      e.stopPropagation();
    }
  },
  true
);
