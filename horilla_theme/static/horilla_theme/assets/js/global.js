// Shared by permission/group tab fragments (base/templates/base/auth/*, employee/templates/cbv/allocations/auth/*).
// Defined globally so it's available regardless of which htmx fragment loads first, since several of
// those fragments call checkSelected() without defining it themselves.
function checkSelected(names, target, initial = false) {
  names = JSON.parse(`${names}`);
  $.each(names, function (indexInArray, valueOfElement) {
    if (!initial) {
      $(target).find(`[value=${valueOfElement}]`).prop("checked", true).change();
    } else {
      $(target).find(`[value=${valueOfElement}]`).prop("checked", true);
    }
  });
  if (typeof refreshPermPicker === "function") {
    var $picker = $(target).closest("[data-perm-picker]");
    if (!$picker.length) {
      $picker = $(target).find("[data-perm-picker]");
    }
    if ($picker.length) {
      refreshPermPicker($picker);
    }
  }
}

// CUSTOM MODAL
document.addEventListener("DOMContentLoaded", () => {
  // Open modal
  document.querySelectorAll("[data-modal-open]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const modalId = btn.getAttribute("data-modal-open");
      const modal = document.getElementById(modalId);
      const box = modal.querySelector(".modal-box");

      modal.classList.remove("hidden");
      modal.classList.add("modal-active"); // ✅ Add this
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
        modal.classList.remove("modal-active"); // ✅ Remove here
      }, 300);
    });
  });
});


// CUSTOM DROPDOWN
document.addEventListener("DOMContentLoaded", () => {
  // Toggle dropdowns
  document.querySelectorAll(".dropdown-toggle").forEach((toggle) => {
    toggle.addEventListener("click", function (e) {
      e.stopPropagation();
      // Close other dropdowns
      document.querySelectorAll(".dropdown-menu").forEach((menu) => {
        if (!menu.closest(".dropdown-wrapper").contains(this)) {
          menu.classList.add("hidden");
        }
      });
      // Toggle this one
      const menu =
        this.closest(".dropdown-wrapper").querySelector(".dropdown-menu");
      menu.classList.toggle("hidden");
    });
  });

  // Close dropdowns when clicking outside. Scoped to this component's own
  // ".dropdown-wrapper .dropdown-menu" convention (matching the toggle
  // logic above) — other components on the page reuse the bare
  // ".dropdown-menu" class name for their own, unrelated dropdowns (e.g.
  // the pipeline tab bar's "Actions" kebab uses ".dropdown-wrapper-tab"),
  // and closing those too on every click anywhere broke them.
  document.addEventListener("click", () => {
    document.querySelectorAll(".dropdown-wrapper .dropdown-menu").forEach((menu) => {
      menu.classList.add("hidden");
    });
  });
});

// SIDEBARModal DSESIGN
document.addEventListener("DOMContentLoaded", () => {
  // Toggle any sidebar based on data-sidebar attribute
  document.querySelectorAll(".toggleSidemenu").forEach((button) => {
    button.addEventListener("click", () => {
      const sidebarId = button.getAttribute("data-sidebar");
      const sidebar = document.getElementById(sidebarId);
      if (sidebar) {
        sidebar.classList.toggle("active");
        document.body.classList.toggle("overflow-hidden");
      }
    });
  });

  // Close any sidebar based on data-sidebar attribute
  document.querySelectorAll(".closeSidemenu").forEach((button) => {
    button.addEventListener("click", () => {
      const sidebarId = button.getAttribute("data-sidebar");
      const sidebar = document.getElementById(sidebarId);
      if (sidebar) {
        sidebar.classList.remove("active");
        document.body.classList.remove("overflow-hidden");
      }
    });
  });
});
