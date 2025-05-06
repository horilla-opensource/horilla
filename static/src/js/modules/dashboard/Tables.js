import $ from "jquery";
import "jquery-ui/ui/core";
import "jquery-ui/ui/widgets/sortable";

class Tables {
  constructor() {
    this.events();
    // Editable Table Inputs
    $(".oh-table__editable-input").on("click", this.makeEditable.bind(this));
    // Editable Table Inputs
    $(".oh-table__editable-input").on(
      "keypress",
      this.disableEditableOnReturn.bind(this)
    );
    // Add Table Row
    $(".oh-table__add-row").on("click", this.addRow.bind($(this)));
    // Add Table Column
    $(".oh-table__add-column").on("click", this.addColumn.bind($(this)));
    // Delete Table Row
    $(".oh-table-config__close-tr").on("click", this.removeRow.bind($(this)));
    // Delete Table Columns
    $(".oh-table-config__close-th").on(
      "click",
      this.removeColumn.bind($(this))
    );
    // Toggle Collapse Table
    $(".oh-table__toggle-parent").on(
      "click",
      this.toggleCollapseTable.bind(this)
    );
    // Sticky Table Dropdown
    $(".oh-sticky-table__dropdown-button").on(
      "click",
      this.toggleTableDropdown.bind(this)
    );
    // Disable editable table input on click outside
    $(window).on("click", this.disableEditable.bind(this));
    // Close Tabledropdown
    $(window).on("click", this.hideTableDropdown.bind(this));
  }

  // Events
  events() {
    // Make tables with the 'oh-table--sortable' class sortable.
    $(".oh-table--sortable tbody").sortable({
      cursor: "row-resize",
      opacity: "0.55",
      items: "tr",
    });
    // For sticky tables.
    $(".oh-table--sortable .oh-sticky-table__tbody").sortable({
      cursor: "row-resize",
      opacity: "0.55",
      items: ".oh-sticky-table__tr",
    });

    // Multi-Table Sort.
    $(".oh-multiple-table-sort").sortable({
      cursor: "row-resize",
      opacity: "0.55",
      items: ".oh-multiple-table-sort__movable",
    });

    // Collapsable Sort.
    $(".oh-table__collaspable-sort").sortable({
      cursor: "row-resize",
      opacity: "0.55",
      items: "tbody",
    });

    // Collapsable sort. - Sticky
    $(".oh-table__sticky-collaspable-sort").sortable({
      cursor: "row-resize",
      opacity: "0.55",
      items: ".oh-sticky-table__tbody",
    });

    // Inter-Table Sort.
    $(".oh-table--inter-sortable").sortable({
      cursor: "row-resize",
      opacity: "0.55",
      items: ".oh-sticky-table__tr",
      connectWith: ".oh-sticky-table__tbody",
    });
  }

  // Methods

  // Editable Input
  makeEditable(e) {
    e.stopPropagation();
    let targetEl = e.target.closest(".oh-table__editable-input");
    targetEl.readOnly = false;
  }

  // Disable Input
  disableEditable() {
    $(".oh-table__editable-input").prop("readonly", true);
  }

  // Disable Input on Pressing Return
  disableEditableOnReturn(e) {
    var code = e.keyCode || e.which;
    if (code == 13) {
      $(e.target).closest(".oh-table__editable-input").prop("readonly", true);
    }
  }

  // Add Row
  addRow(e) {
    var $tr = $(e.target).parent().find(".oh-table-config__tr").last();
    var $clone = $tr.clone(true, true);
    $clone.find(":text").val("");
    $clone.find(":text").attr("placeholder", "Edit Here");
    $tr.after($clone);
  }

  // Add Column
  addColumn(e) {
    let table = $(e.target).closest(".oh-table--configurable");

    let tableRows = table.find(".oh-table-config__tr");

    tableRows.each(function (index, item) {
      let childElements = item.children;
      let cloneTd = null;

      for (var i = 0; i < childElements.length; i++) {
        if (childElements[i].classList.contains("oh-table-config__th")) {
          if (i == childElements.length - 2) {
            cloneTd = $(childElements[i]).clone(true, true);
          }
        } else {
          if (i == childElements.length - 1) {
            cloneTd = $(childElements[i]).clone(true, true);
          }
        }
      }

      if ($(item).find(".oh-table-config__th").length > 0) {
        $(cloneTd).insertBefore(
          $(item).children(".oh-table-config__th").last()
        );
      } else {
        $(item).append(cloneTd);
      }
    });
  }

  // Remove Row
  removeRow(e) {
    let targetEl = $(e.target).closest(".oh-table-config__close-tr");
    let rowToDelete = targetEl.parents(".oh-table-config__tr");

    if (rowToDelete) {
      rowToDelete.remove();
    }
  }

  // Remove removeColumn
  removeColumn(e) {
    let targetEl = $(e.target).closest(".oh-table-config__close-th");
    let targetColumnIndex = $(e.target).closest(".oh-table-config__th").index();
    let allRows = targetEl
      .parents(".oh-table--configurable")
      .find(".oh-table-config__tr");

    allRows.each(function (index, item) {
      $(item).children().eq(targetColumnIndex).remove();
    });
  }

  // Toggle Collapsable
  toggleCollapseTable(e) {
    e.preventDefault();
    let clickedEl = $(e.target).closest(".oh-table__toggle-parent");
    let targetSelector = clickedEl.data("target");
    let toggleBtn = clickedEl.find(".oh-table__toggle-button");
    $(`[data-group='${targetSelector}']`).toggleClass(
      "oh-table__toggle-child--show"
    );
    if (toggleBtn) {
      toggleBtn.toggleClass("oh-table__toggle-button--show");
    }
  }

  // Stick Table Dropdown
  toggleTableDropdown(e) {
    e.preventDefault();
    let clickedEl = $(e.target).closest(".oh-sticky-table__dropdown-button");
    let caretIcon = clickedEl.find(".oh-sticky-table__dropdown-caret");
    let dropdownMenuEl = clickedEl
      .parents(".oh-sticky-table__dropdown")
      .find(".oh-dropdown__menu");

    if (dropdownMenuEl && caretIcon) {
      if (dropdownMenuEl.hasClass("d-none")) {
        dropdownMenuEl.removeClass("d-none");
        caretIcon.css({ transform: "rotate(180deg)" });
      } else {
        dropdownMenuEl.addClass("d-none");
        caretIcon.css({ transform: "rotate(0deg)" });
      }
    }
  }

  // Sticky Table Dropdown
  hideTableDropdown(e) {
    if ($(e.target).parents(".oh-sticky-table__dropdown").length == 0) {
      if (
        $('.oh-sticky-table__dropdown .oh-dropdown__menu:not(".d-none")')
          .length > 0
      ) {
        $(".oh-dropdown__menu").addClass("d-none");
      }
    }
  }
}

export default Tables;
