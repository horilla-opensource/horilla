import $ from "jquery";
import "jquery-ui/ui/core";
import "jquery-ui/ui/widgets/sortable";
import "select2";
import "select2/dist/css/select2.css";

class Generic {
  constructor() {
    this.events();
  }

  // Events
  events() {
    // Select 2 Trigger
    $(window).on("load", this.loadSelect2.bind(this));
    // Hide dropdown on click outside
    $(document).on("click", this.hideOnClickOutside.bind(this));
    // Editable Trigger
    $(".oh-editable-input-trigger").on("click", this.makeEditable.bind(this));
    // Clone Element
    $("[data-action='clone']").on("click", function () {
      let targetEl = $(this).data("target");
      let cloneTo = $(this).data("clone");
      $(targetEl).clone(true, true).appendTo(cloneTo);
    });
    $(".oh-permission-table--toggle").on(
      "click",
      this.collapsePermissionTable.bind(this)
    );
    // Accordion
    $(".oh-accordion-header").on("click", this.toggleAccordion.bind(this));
    // Toggle Element
    $(".oh-d-toggle").on("click", this.toggleView.bind(this));
    // Hide target
    $(".oh-d-hide").on("click", this.hideView.bind(this));
    // Accordion Meta
    $(".oh-accordion-meta__item").on(
      "click",
      this.toggleAccordionMeta.bind(this)
    );
    // Stop Propagation
    $(".oh-stop-prop").on("click", this.ohStopPropagation.bind(this));
    // Sidebar Reveal on hover
    $("#sidebar").on("mouseover", this.sidebarReveal.bind(this));
    // Navbar Toggler
    $(".oh-navbar__toggle-link").on("click", this.sidebarToggle.bind(this));
    // Remove Keayboard
    $(window).on("keyup", this.keyboardRemove.bind(this));

    // Dashboard Cards Movable ss
    $(".oh-dashboard__movable-cards").sortable({
      cursor: "row-resize",
      opacity: "0.55",
      items: ".oh-card-dashboard--moveable",
    });
  }

  // Methods

  /**
   *  Make input editable
   */
  makeEditable(e) {
    let targetEl = e.target.closest(".oh-editable-input-trigger").dataset
      .target;
  }

  /**
   * Clone element
   */
  cloneElement(e) {
    let targetEl = e.target.dataset.target;
    let cloneSectionEl = e.target.dataset.clone;

    if (targetEl && cloneSectionEl) {
      document
        .querySelector(cloneSectionEl)
        .insertAdjacentElement(
          "afterbegin",
          document.querySelector(targetEl).cloneNode(true)
        );
    }
  }

  /**
   * Initialize Select 2
   */
  loadSelect2() {
    $(".oh-select-2").select2();
    // Select2 Autofocus
    $(document).on("select2:open", () => {
      document.querySelector(".select2-search__field").focus();
    });
    // Select 2 with image
    $(".oh-select-image").select2({
      placeholder: "Search",
      templateResult: this.imageFormatState,
      templateSelection: this.imageFormatState,
    });
    $(".oh-select-no-search").select2({
      minimumResultsForSearch: Infinity,
    });
  }

  /**
   * Image Format State
   */
  imageFormatState(state) {
    if (!state.id) {
      return state.text;
    }
    var $state = $(
      '<span><img src="' +
        $(state.element).attr("data-src") +
        '" class="oh-select-image__img" /> ' +
        state.text +
        "</span>"
    );
    return $state;
  }

  // Toggle Display View
  toggleView(e) {
    // e.preventDefault();
    let targetEl = e.target.closest(".oh-d-toggle").dataset.target;
    if (targetEl) {
      $(targetEl).removeClass("d-none");
    }
  }

  /**
   * Show / Collapse Permission list row.
   */
  collapsePermissionTable(e) {
    e.stopPropagation();
    let clickedEl = $(e.target).closest(".oh-permission-table--toggle");
    let parentRow = clickedEl.parents(".oh-permission-table__tr");
    // let collapsedPanel = parentRow.find(".oh-collapse-panel");
    let count = parentRow.data("count");
    let labelText = parentRow.data("label");
    // Count number of permissions.
    // let permissionCount = collapsedPanel.length;
    let cellEl = parentRow
      .find(".oh-collapse-panel")
      .parents(".oh-sticky-table__td");
    // Label
    let labelEl = null;
    if (labelText) {
      if (count > 1) {
        labelEl = `<span class='oh-permission-count'>${count} ${labelText}s</span>`;
      } else {
        labelEl = `<span class='oh-permission-count'>${count} ${labelText}</span>`;
      }
    }
    // Collapse / Hide Permission Panels
    parentRow.toggleClass("oh-permission-table--collapsed");
    if (parentRow.hasClass("oh-permission-table--collapsed")) {
      if (labelEl) {
        $(cellEl).append(labelEl);
      }
    } else {
      $(cellEl).find(".oh-permission-count").remove();
    }
  }

  // Hide View
  hideView(e) {
    let targetEl = e.target.dataset.target;

    if (targetEl) {
      $(targetEl).addClass("d-none");
    }
  }

  // Hide on click outside
  hideOnClickOutside(e) {
    if (
      $(e.target).closest(".oh-dropdown__close-outside-click").length > 0 ||
      $(e.target).closest(".oh-tabs__new-tab-config").length > 0
    )
      return;
    $(".oh-dropdown__close-outside-click").addClass("d-none");
  }

  /**
   * Togggle Accordion
   */
  toggleAccordion(e) {
    let clickedEl = $(e.target).closest(".oh-accordion-header");
    let accordionEl = clickedEl.parent(".oh-accordion");
    accordionEl.toggleClass("oh-accordion--show");
  }

  /**
   * Toggle Accordion
   */
  keyboardRemove(e) {
    let targetEl = $("[data-action='keyboard-remove']");
    if (targetEl.length == 0) return;
    let pressedKey = targetEl.data("key");
    if (e.keyCode === pressedKey) {
      let classRemove = targetEl.data("class");
      targetEl.addClass(classRemove);
    }
  }

  /**
   * Toggle Accordion Meta
   */
  toggleAccordionMeta(e) {
    e.preventDefault;
    e.stopPropagation;
    let clickedEl = $(e.target).closest(".oh-accordion-meta__header");
    let accordionItemBody = clickedEl
      .parent(".oh-accordion-meta__item")
      .find(".oh-accordion-meta__body");

    if (clickedEl) {
      clickedEl.toggleClass("oh-accordion-meta__header--show");
    }
    if (accordionItemBody) {
      accordionItemBody.toggleClass("d-none");
    }
  }

  /**
   * Stop Propagation
   */
  ohStopPropagation(e) {
    e.stopPropagation();
  }

  /**
   * Sidebar reaveal on hover
   */
  sidebarReveal(e) {
    e.preventDefault();
    let sidebarContainer = $(".oh-wrapper-main");

    if (sidebarContainer.hasClass("oh-wrapper-main--closed")) {
      sidebarContainer.removeClass("oh-wrapper-main--closed");
    }
  }
  /**
   * Sidebar show/reaveal on click
   */
  sidebarToggle(e) {
    e.preventDefault();
    let sidebarContainer = $(".oh-wrapper-main");

    console.log(sidebarContainer.hasClass("oh-wrapper-main--closed"));

    if (sidebarContainer.hasClass("oh-wrapper-main--closed")) {
      sidebarContainer.removeClass("oh-wrapper-main--closed");
    }else{
      sidebarContainer.addClass("oh-wrapper-main--closed");
    }
  }
}

export default Generic;
