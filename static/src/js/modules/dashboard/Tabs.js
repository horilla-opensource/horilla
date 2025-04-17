import $ from "jquery";
import "jquery-ui/ui/core";
import "jquery-ui/ui/widgets/sortable";
import { v4 as uuidv4 } from "uuid";
import Tables from "./Tables";
class Tabs extends Tables {
  constructor() {
    super();
    this.events();
    // Switch Tab
    $(".oh-tabs__tab").on("click", this.switchTab.bind(this));
    // Add New Tab
    $(".oh-tabs__new-tab").on("click", this.addTab.bind(this));
    // Add New Config Tab
    $(".oh-tabs__advanced-form").on("submit", this.addConfigTab.bind(this));
    // Add Table Rows
    $(".oh-table__add-row-form").on("submit", this.addTableRow.bind(this));
    // Close Tab
    $(".oh-tabs__close-btn").on("click", this.closeTab.bind(this));
    // Collapse Movable Dialog
    $(".oh-tabs__movable-header").on("click", this.collapseMovable.bind(this));
    // Prevent inheriting parent funciton
    $(".oh-tabs__movable-header .oh-btn").on("click", this.preventCollapseMovable.bind(this));
    // Add New Movable Table
    $(".oh-tabs__action-new-table").on(
      "click",
      this.addNewMovaleTable.bind(this)
    );
    // Remove Movable Table
    $(".oh-tabs__movable-close").on("click", this.removeMovaleTable.bind(this));
    // General Tab
    $('[data-action="general-tab"]').on(
      "click",
      this.switchGeneralTab.bind(this)
    );

    // Close dialog on click outside
    $(window).on("click", this.closeOnClickOutside.bind(this));
  }

  // Events
  events() {
    // Movable Tabs
    $(".oh-tabs__movable-area, .pipeline-header").sortable({
      cursor: "row-resize",
      opacity: "0.55",
      items: ".oh-tabs__movable",
    });
    // Inter-Table Sort.
    $(".oh-table--inter-sortable").sortable({
      cursor: "row-resize",
      opacity: "0.55",
      items: ".oh-sticky-table__tr",
      connectWith: ".oh-sticky-table__tbody",
    });

    /* ======= EVENTS FROM TABLE.JS {TEMP} ======= */
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
      placeholder: "oh-sticky-table__tbody--highlight",
    });
  }

  // Methods

  // Switch Tab
  switchTab(e) {
    let parentContainerEl = e.target.closest(".oh-tabs");
    let tabElement = e.target.closest(".oh-tabs__tab");
    if (tabElement.classList.contains("oh-tabs__new-tab")) return;

    let targetSelector = e.target.dataset.target;
    let targetEl = parentContainerEl
      ? parentContainerEl.querySelector(targetSelector)
      : null;

    // Highlight active tabs
    if (tabElement && !tabElement.classList.contains("oh-tabs__tab--active")) {
      parentContainerEl
        .querySelectorAll(".oh-tabs__tab--active")
        .forEach(function (item) {
          item.classList.remove("oh-tabs__tab--active");
        });

      if (!tabElement.classList.contains("oh-tabs__new-tab")) {
        tabElement.classList.add("oh-tabs__tab--active");
      }
    }

    // Switch tabs
    if (targetEl && !targetEl.classList.contains("oh-tabs__content--active")) {
      parentContainerEl
        .querySelectorAll(".oh-tabs__content--active")
        .forEach(function (item) {
          item.classList.remove("oh-tabs__content--active");
        });
      targetEl.classList.add("oh-tabs__content--active");
    }
  }

  // Add Tab
  addTab(e) {
    let targetEl = e.target.closest(".oh-tabs__new-tab");
    let targetDiv = e.target.closest(".oh-tabs__tablist");
    let tabContentEl = targetDiv
      .closest(".oh-tabs")
      .querySelector(".oh-tabs__contents");
    let previousTabId = targetEl.previousElementSibling.dataset.target;
    let nextID = +previousTabId.split("_")[1] + 1;

    // Add New Tab
    this.createTabElement(nextID, targetEl, targetDiv, tabContentEl, "New Tab");
  }

  // Add Tab with Config.
  addConfigTab(e) {
    e.preventDefault();
    let formEl = e.target.closest("form");
    let tabTitle = formEl[formEl.dataset.title].value;

    let targetEl = e.target.closest(".oh-tabs__new-tab-config");
    let targetDiv = e.target.closest(".oh-tabs__tablist");
    let tabContentEl = targetDiv
      .closest(".oh-tabs")
      .querySelector(".oh-tabs__contents");
    let previousTabId = targetEl.previousElementSibling.dataset.target;
    let nextID = +previousTabId.split("_")[1] + 1;

    // Add New Tab
    this.createTabElement(nextID, targetEl, targetDiv, tabContentEl, tabTitle);

    // Remove close button if there's only one tab left.
    this.showHideCloseButton(targetDiv.closest(".oh-tabs"));

    let submitBtn = formEl.querySelector('button[type="submit"]');
    if (submitBtn.classList.contains("oh-d-hide")) {
      let targetEl = submitBtn.dataset.target;
      if (targetEl) {
        $(targetEl).addClass("d-none");
      }
    }

    // Reset form
    formEl.reset();
  }

  // Close Tab
  closeTab(e) {
    let clickedTabEl = e.target
      .closest(".oh-tabs__close-btn")
      .closest(".oh-tabs__tab");

    let tabContainerEl = e.target
      .closest(".oh-tabs__close-btn")
      .closest(".oh-tabs__tab")
      .closest(".oh-tabs");

    let targetId = clickedTabEl.dataset.target;

    // Find if sibilings exists
    let prevTab = clickedTabEl.previousElementSibling
      ? clickedTabEl.previousElementSibling.dataset.target
      : null;
    let nextTab = clickedTabEl.nextElementSibling.dataset.target
      ? clickedTabEl.nextElementSibling.dataset.target
      : null;

    if (
      nextTab &&
      !clickedTabEl.nextElementSibling.classList.contains(
        "oh-tabs__new-tab-config"
      )
    ) {
      $(`.oh-tabs__tab[data-target='${nextTab}']`).addClass(
        "oh-tabs__tab--active"
      );
      $(nextTab).addClass("oh-tabs__content--active");
    } else if (prevTab) {
      $(`.oh-tabs__tab[data-target='${prevTab}']`).addClass(
        "oh-tabs__tab--active"
      );
      $(prevTab).addClass("oh-tabs__content--active");
    }
    // Remove tab & content
    if (prevTab || nextTab) {
      $(`.oh-tabs__content${targetId}`).remove();
      clickedTabEl.remove();
    }
    // Remove close button if there's only one tab left.
    this.showHideCloseButton(tabContainerEl);
  }

  // Construct Tab Elementn
  createTabElement(nextID, targetEl, targetDiv, tabContentEl, tabTitle) {
    // Create Tab Element
    let newTab = document.createElement("li");
    let newTabText = document.createTextNode(tabTitle);
    newTab.appendChild(newTabText);

    newTab.classList.add("oh-tabs__tab");
    newTab.dataset.target = `#tab_${nextID}`;

    // Add tab switch event listener to the new tab.
    newTab.addEventListener("click", this.switchTab.bind(this));

    // Create and add close button to tab.
    let closeBtn = document.createElement("button");
    // Close button classes
    closeBtn.classList.add("oh-btn");
    closeBtn.classList.add("oh-btn--sq-sm");
    closeBtn.classList.add("oh-btn--transparent");
    closeBtn.classList.add("oh-tabs__close-btn");
    // Close button icon
    closeBtn.innerHTML = '<ion-icon name="close-outline"></ion-icon>';
    // Link close tab event.
    closeBtn.addEventListener("click", this.closeTab.bind(this));
    newTab.appendChild(closeBtn);

    targetDiv.insertBefore(newTab, targetEl);

    // Create Tab Content
    let newTabContent = document.createElement("div");
    newTabContent.classList.add("oh-tabs__content");
    newTabContent.id = `tab_${nextID}`;
    newTabContent.addEventListener("click", this.switchTab.bind(this));
    tabContentEl.appendChild(newTabContent);

    // Display close button if more than 1 tab exists
    let tabsLeft = $(".oh-tabs__tab").length - 1;
    if (tabsLeft > 1) {
      targetDiv
        .closest(".oh-tabs")
        .querySelector(".oh-tabs__close-btn")
        .classList.remove("d-none");
    }

    // Remove focus from currenlty active tabs and content.
    targetDiv
      .querySelectorAll(".oh-tabs__tab--active")
      .forEach(function (item) {
        item.classList.remove("oh-tabs__tab--active");
      });
    tabContentEl
      .querySelectorAll(".oh-tabs__content--active")
      .forEach(function (item) {
        item.classList.remove("oh-tabs__content--active");
      });

    // Swtich to newly inserted tab.
    targetDiv
      .querySelector(`[data-target='#tab_${nextID}']`)
      .classList.add("oh-tabs__tab--active");

    tabContentEl
      .querySelector(`#tab_${nextID}`)
      .classList.add("oh-tabs__content--active");
  }

  // Show / Hide Close Button
  showHideCloseButton(tabContainerEl) {
    let tabsLeft = 0;
    if ($(".oh-tabs__new-tab-config").length > 0) {
      tabsLeft = $(".oh-tabs__tab").length;
    } else {
      tabsLeft = $(".oh-tabs__tab").length - 1;
    }
    if (tabsLeft == 1) {
      tabContainerEl
        .querySelector(".oh-tabs__close-btn")
        .classList.add("d-none");
    } else {
      // Remove d-none from the first tab
      tabContainerEl
        .querySelector(".oh-tabs__close-btn")
        .classList.remove("d-none");
    }
  }

  // Show / Hide Movable Dialog
  collapseMovable(e) {
    e.stopPropagation();
    let clickedEl = e.target.closest(".oh-tabs__movable-header");
    let movableDialogEl = clickedEl.closest(".oh-tabs__movable");

    $(movableDialogEl).find(".oh-tabs__movable-body").toggleClass("d-none");
  }

  // Prevent inheriting toggle function
  preventCollapseMovable(e){
    e.stopPropagation();
  }

  // Add New Movable Table
  addNewMovaleTable(e) {
    // ID
    let uniqueID = uuidv4();
    // Selectors
    let targetEl = $(e.target).closest(".oh-tabs__action-new-table");
    let parentEl = targetEl.parents(".oh-tabs__content");
    let movableAreaEl = parentEl.find(".oh-tabs__movable-area");
    let cloneEl = parentEl.find(".oh-tabs__movable").last().clone(); // Do not deep clone for jQuery sortable won't work if you do.
    let dropDownCloneEl = parentEl.find(".oh-dropdown__menu")?.last().clone(true, true);  // Clone dialog

    // Add event to add row button
    cloneEl.find('.oh-d-toggle').attr('data-target', `#${uniqueID}`);
    cloneEl.find('.oh-d-toggle').on("click", function(e){
      e.preventDefault();
      let targetEl = e.target.closest(".oh-d-toggle").dataset.target;
      if (targetEl) {
        $(targetEl).removeClass("d-none");
      }
    });
    // Add ID to dropdown
    dropDownCloneEl.attr('id', uniqueID);

    cloneEl.find(":text").val("");
    cloneEl.find(":text").attr("placeholder", "Edit");
    cloneEl
      .find(".oh-sticky-table__tbody .oh-sticky-table__tr")
      .filter(":not(.oh-sticky-table__tbody .oh-sticky-table__tr:first-child)")
      .remove();

    if (movableAreaEl) {
      $(movableAreaEl).append(cloneEl).append(dropDownCloneEl);

      this.events();
      $('.oh-input--resize').on("keyup", function(e){
        $(e.target).attr('size', $(e.target).val().length);
      });
      /* =========== Register Events =========== */

      this.tableTabsEvents(cloneEl);
    }
  }

  // Register Table Events
  tableTabsEvents(parentEl) {
    // Editable Table Inputs
    $(parentEl)
      .find(".oh-table__editable-input")
      .on("click", this.makeEditable.bind(this));
    // Editable Table Inputs
    $(parentEl)
      .find(".oh-table__editable-input")
      .on("keypress", this.disableEditableOnReturn.bind(this));
    // Add Table Row
    $(parentEl)
      .find(".oh-table__add-row")
      .on("click", this.addRow.bind($(this)));
    // Add Table Column
    $(parentEl)
      .find(".oh-table__add-column")
      .on("click", this.addColumn.bind($(this)));
    // Delete Table Row
    $(parentEl)
      .find(".oh-table-config__close-tr")
      .on("click", this.removeRow.bind($(this)));
    // Delete Table Columns
    $(parentEl)
      .find(".oh-table-config__close-th")
      .on("click", this.removeColumn.bind($(this)));
    // Remove Movable Table
    $(parentEl)
      .find(".oh-tabs__movable-close")
      .on("click", this.removeMovaleTable.bind(this));
    // Collapse Movable Dialog
    $(parentEl)
      .find(".oh-tabs__movable-header")
      .on("click", this.collapseMovable.bind(this));
  }

  // Remove Movable Table
  removeMovaleTable(e) {
    e.stopPropagation();
    let targetEl = $(e.target).closest(".oh-tabs__movable-close");
    let closeEl = targetEl.parents(".oh-tabs__movable");
    let dropdown = closeEl.next('.oh-dropdown__menu');
    closeEl?.remove();
    dropdown?.remove();
  }

  // Switch General Tab
  switchGeneralTab(e) {
    // DO NOT USE GENERAL TABS TWICE ON A SINGLE PAGE.
    e.preventDefault();
    let clickedEl = e.target.closest(".oh-general__tab-link");
    let targetSelector = clickedEl.dataset.target;

    // Remove active class from all the tabs
    $(".oh-general__tab-link").removeClass("oh-general__tab-link--active");
    // Remove active class to the clicked tab
    clickedEl.classList.add("oh-general__tab-link--active");

    // Hide all the general tabs
    $(".oh-general__tab-target").addClass("d-none");
    // Show the tab with the chosen target
    $(`.oh-general__tab-target${targetSelector}`).removeClass("d-none");
  }

  // Add New Table Row
  addTableRow(e) {
    e.preventDefault();
    // Parent containing both table and the dropdown menu
    let parentSelector = $(e.target).data("parent");
    // Table on to which the new row is to be attached
    let targetSelector = $(e.target).data("target");
    // Dropdown menu
    let parentContainer = $(e.target).parents(".oh-dropdown__menu");

    // Get form data
    let formData = $(e.target).serializeArray();

    // Check if both the parent container and table exists
    if (parentSelector && targetSelector) {
      // Row Start
      let tableRow = `<div class="oh-sticky-table__tr oh-table-config__tr ui-sortable-handle" draggable="true">`;

      $.each(formData, function (i, field) {
        // Check if the first cell, if so add profile image and close button.
        if (i == 0) {
          tableRow += `
            <div class="oh-sticky-table__sd oh-table-config__td">
                <button class="oh-table-config__close-tr">
                  <ion-icon name="close-outline" role="img" class="md hydrated" aria-label="close outline"></ion-icon>
                </button>
                <div class="oh-profile oh-profile--md">
                  <div class="oh-profile__avatar mr-1">
                    <img src="https://ui-avatars.com/api/?name=${field.value}&amp;background=random" class="oh-profile__image" alt="User">
                  </div>
                  <input class="oh-table__editable-input" placeholder="Edit" value="${field.value}" readonly>
                </div>
            </div>`;
        } else {
          tableRow += `
            <div class="oh-sticky-table__sd oh-table-config__td">
              <input class="oh-table__editable-input" placeholder="Edit" value="${field.value}" readonly>
            </div>`;
        }
      });

      // Row End
      tableRow += "</div>";

      let attachTarget = parentContainer.prev('.oh-tabs__movable').find(`${targetSelector}`).last();

      // Append new row to the table [[ Check if we're adding on to the right parent ]]

      $(tableRow).insertAfter(attachTarget);

      // Clear all form inputs
      $(e.target).find("input").val("");
      // Close the dropdown
      parentContainer.addClass("d-none");

      // Re-register events
      this.tableTabsEvents(parentSelector);
    }
  }

  // Close new table row dialog on click outside
  closeOnClickOutside(e){
      if($(e.target).closest('.oh-table__add-row-dropdown').length > 0 || $(e.target).closest('.oh-d-toggle').length > 0 ) return;
      $('.oh-table__add-row-dropdown').addClass('d-none');

  }
}

export default Tabs;
