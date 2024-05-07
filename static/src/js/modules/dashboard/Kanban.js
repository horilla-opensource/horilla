import $ from "jquery";
import "jquery-ui/ui/core";
import "jquery-ui/ui/widgets/sortable";
import { v4 as uuidv4 } from "uuid";

class Kanban {
  constructor() {
    this.events();
    // Add New Section Form Handler
    $(".oh-kanban__add-section-form").on(
      "submit",
      this.addKanbanSection.bind(this)
    );
    // Edit Form Handler
    $(".oh-kanban__edit-modal-form").on(
      "submit",
      this.editFormHandler.bind(this)
    );
    // Kanban Group Collapse
    $(".oh-kanban-group__head").on("click", this.kanbanGroupToggle.bind(this));

    this.registerKanbanEvents();
  }

  // Events
  events() {
    // Kanban Section Sort.
    $(".oh-kanban").sortable({
      cursor: "row-resize",
      opacity: "0.55",
      items: ".oh-kanban__section",
      placeholder: "oh-kanban__section--highlight",
    });
    // Kanban Card-Section Sort.
    $(".oh-kanban__section-body").sortable({
      cursor: "row-resize",
      opacity: "0.55",
      items: ".oh-kanban__card",
      connectWith: ".oh-kanban__section-body",
      placeholder: "oh-kanban__card--highlight",
    });
    // Trigger Kanban Card Highlight Color
    $(".oh-kanban__select").on("change", this.changeCardHighlight.bind(this));
  }

  // Kanban Actions
  registerKanbanEvents() {
    // Remove existing event listers to avoid conflict.
    $(
      ".oh-kanban__dropdown-toggle, .oh-kanban__section-delete, .oh-kanban__add-card-btn, .oh-kanban__add-card-cancel-btn, input[name='kanban-card-name']"
    ).off("click");

    // Add New Card Form Handler
    $(".oh-kanban__add-card-form").on("submit", this.addKanbanCard.bind(this));

    // Toggle Kanban Dropdown
    $(".oh-kanban__dropdown-toggle").on(
      "click",
      this.toggleKanbanDropdown.bind(this)
    );
    // Delete Kanban
    $(".oh-kanban__section-delete").on(
      "click",
      this.deleteKanbanSection.bind(this)
    );
    // Delete Kanban Card
    $(".oh-kanban__card-delete").on("click", this.deleteKanbanCard.bind(this));
    // Show Kanban Card Prompt
    $(".oh-kanban__add-card-btn").on(
      "click",
      this.showKanbanCardForm.bind(this)
    );
    // Show Kanban Card Prompt
    $(".oh-kanban-group__add-card").on(
      "click",
      this.showKanbanCardGroup.bind(this)
    );
    // Hide Kanban Card Prompt
    $(".oh-kanban__add-card-cancel-btn").on(
      "click",
      this.hideKanbanCardForm.bind(this)
    );
    // Check for valid input
    $("input[name='kanban-card-name']").on("keyup", this.checkValid.bind(this));

    // Edit Modal
    $("[data-toggle='oh-kanban-toggle']").on(
      "click",
      this.openEditModal.bind(this)
    );

    // Hide Dropdown
    $(window).on("click", this.hideKanbanDropdown.bind(this));
  }

  // Methods

  /**
   * Open Edit Kanban Modal
   */
  openEditModal(e) {
    if (e.target != null) {
      // Get modal target.
      const targetEl = e.target.dataset.target;
      // Get element where the UUID for section / card is stored as the ID.
      const keyStemEl = e.target.dataset.key;
      // Get the UUID
      const key = $(e.target).parents(keyStemEl).attr("id");
      // Get label value of the section / card.
      if (key) {
        let labelEl = $(`#${key} [data-type='label']`);
        let labelText = "";
        if (labelEl.length > 1) {
          labelText = $(`#${key} [data-type='label']`).first().text();
        } else {
          labelText = $(`#${key} [data-type='label']`).text();
        }
        // Assign as the value of modal input
        $(`${targetEl} input[name='edit-value']`).val(labelText);
        $(`${targetEl} .oh-kanban__edit-modal-form`).data("target", `#${key}`);
      }
      // Show modal dialog
      $(targetEl).addClass("oh-modal--show");
    }
  }

  /**
   * Edit Form Handler
   */
  editFormHandler(e) {
    e.preventDefault();
    // Get form data.
    let formData = $(e.target).serializeArray();
    // Get the target of which element to update.
    let targetSelector = $(e.target).data("target");

    if (targetSelector) {
      $.each(formData, function (i, field) {
        if (field.name === "edit-value" && field.value.length > 0) {
          // Get the changed value.
          let changedValue = field.value;
          // Update the target element text.
          $(`${targetSelector} [data-type='label']`).first().text(changedValue);
          // Close Form
          $(e.target).parents(".oh-modal").removeClass("oh-modal--show");
        }
      });
    }
  }

  /**
   * Add Kanban Section
   */
  addKanbanSection(e) {
    e.preventDefault();
    let formData = $(e.target).serializeArray();
    $.each(formData, function (i, field) {
      if (field.name === "kanban-section-name" && field.value.length > 0) {
        let kanbanSection = `
        <div class="oh-kanban__section" id=${uuidv4()}>
        <div class="oh-kanban__section-head">
          <span class="oh-kanban__section-title" data-type='label'
            >${field.value.trim()}</span
          >
          <div class="oh-kanban__head-actions oh-kanban__dropdown">
            <button
              class="oh-btn oh-btn--small oh-btn--transparent oh-kanban__btn oh-kanban__dropdown-toggle"
            >
              <ion-icon name="ellipsis-vertical-sharp"></ion-icon>
            </button>
            <div class="oh-dropdown oh-kanban__dropdown-menu d-none">
              <div
                class="oh-dropdown__menu oh-dropdown__menu--right"
              >
                <ul class="oh-dropdown__items">
                  <li class="oh-dropdown__item">
                    <a href="#" class="oh-dropdown__link" data-toggle="oh-kanban-toggle"
                    data-target="#editDialog" data-key=".oh-kanban__section">Rename</a>
                  </li>
                  <li class="oh-dropdown__item">
                    <a href="#" class="oh-dropdown__link oh-dropdown__link--danger oh-kanban__section-delete">Delete</a>
                  </li>
                </ul>
              </div>
            </div>
            <button
              class="oh-btn oh-btn--small oh-btn--transparent oh-kanban__btn oh-kanban__add-card-btn"
            >
              <ion-icon name="add-sharp"></ion-icon>
            </button>
          </div>
        </div>
        <div class="oh-kanban__section-body">
        <div class="oh-card oh-kanban__add-card-container d-none mb-2">
                    <form class="oh-kanban__add-card-form">
                      <input type="text" name="kanban-card-name" class="oh-input oh-input--small w-100" placeholder="Candidate name" autofocus  autocomplete="off"/>
                      <div class="d-flex align-items-center justify-content-end">
                        <a  href="#" role="button" class="oh-btn oh-btn--light-dark-text oh-btn--x-small oh-kanban__add-card-cancel-btn me-2 mt-2">Cancel</a>
                        <button type="submit" class="oh-btn oh-btn--secondary oh-btn--x-small mt-2" disabled>Add</button>
                      </div>
                    </form>
                  </div>
        </div>
      </div>
      `;
        if ($(".oh-kanban .oh-kanban__section:nth-last-child(2)").length > 0) {
          $(kanbanSection).insertAfter(
            ".oh-kanban .oh-kanban__section:nth-last-child(2)"
          );
        } else {
          $(kanbanSection).insertBefore(".oh-kanban__add-container");
        }
      }
    });
    $("input[name='kanban-section-name']").val("");
    this.events();
    this.registerKanbanEvents();
  }
  /**
   * Add Kanban Card
   */
  addKanbanCard(e) {
    e.preventDefault();
    // Get Type of the form
    let type = $(e.target).data("type");

    let formData = $(e.target).serializeArray();
    $.each(formData, function (i, field) {
      if (field.name === "kanban-card-name" && field.value) {
        if (type === "asset") {
          let kanbanCard = `
          <div class="oh-kanban__card oh-kanban__card--status oh-kanban__card--blue"  id=${uuidv4()}>
            <div class="oh-kanban__card-head">
              <div class="oh-profile oh-profile--md">
                <span class="oh-profile__name oh-text--dark" data-type='label'
                  >${field.value.trim()}</span
                >
              </div>
              <div class="oh-kanban__card-actions oh-kanban__dropdown">
                        <button
                          class="oh-btn oh-btn--small oh-btn--transparent oh-kanban__btn oh-kanban__dropdown-toggle"
                        >
                          <ion-icon name="ellipsis-vertical-sharp"></ion-icon>
                        </button>

                        <div class="oh-dropdown oh-kanban__dropdown-menu d-none">
                          <div
                            class="oh-dropdown__menu oh-dropdown__menu--right"
                          >
                            <ul class="oh-dropdown__items">
                              <li class="oh-dropdown__item">
                                <a href="#" class="oh-dropdown__link oh-dropdown__link--danger oh-kanban__card-delete">Delete</a>
                              </li>
                            </ul>
                          </div>
                        </div>

                      </div>
            </div>
            <div class="oh-kanban__card-footer py-0">
              <select class="oh-kanban__select oh-select oh-select--sm oh-select-2 oh-select-no-search">
                <option value='1'>Assigned</option>
                <option value='2'>Free</option>
                <option value='3'>On Repair</option>
                <option value='4'>Unavailable</option>
              </select>
            </div>
          </div>
          `;
          // Add the card to section body
          $(e.target).parents(".oh-kanban-group__body").append(kanbanCard);
        } else {
          let kanbanCard = `
            <div class="oh-kanban__card"  id=${uuidv4()}>
              <div class="oh-kanban__card-head">
                <div class="oh-profile oh-profile--md">
                  <div class="oh-profile__avatar mr-1">
                    <img
                      src="https://ui-avatars.com/api/?name=${field.value.trim()}&background=random"
                      class="oh-profile__image"
                      alt="${field.value.trim()}"
                    />
                  </div>
                  <span class="oh-profile__name oh-text--dark" data-type='label'
                    >${field.value.trim()}</span
                  >
                </div>
                <div class="oh-kanban__card-actions oh-kanban__dropdown">
                          <button
                            class="oh-btn oh-btn--small oh-btn--transparent oh-kanban__btn oh-kanban__dropdown-toggle"
                          >
                            <ion-icon name="ellipsis-vertical-sharp"></ion-icon>
                          </button>

                          <div class="oh-dropdown oh-kanban__dropdown-menu d-none">
                            <div
                              class="oh-dropdown__menu oh-dropdown__menu--right"
                            >
                              <ul class="oh-dropdown__items">
                                <li class="oh-dropdown__item">
                                  <a href="#" class="oh-dropdown__link oh-dropdown__link--danger oh-kanban__card-delete">Delete</a>
                                </li>
                              </ul>
                            </div>
                          </div>

                        </div>
              </div>
              <div class="oh-kanban__card-footer">
                <span class="oh-kanban__card-footer-text oh-text--light"
                  >Candidate</span
                >
              </div>
            </div>
            `;
          // Add the card to section body
          $(e.target).parents(".oh-kanban__section-body").append(kanbanCard);
        }
        // Close the dialog
        $(e.target)
          .parents(".oh-kanban__add-card-container")
          .addClass("d-none");
        // Clear the dialog
        $(e.target).find('input[name="kanban-card-name"]').val("");
      }
    });

    this.events();
    this.registerKanbanEvents();
  }

  /**
   * Kanban Dropdown
   */
  toggleKanbanDropdown(e) {
    e.preventDefault();
    let clickedEl = $(e.target).closest(".oh-kanban__dropdown-toggle");
    let parentEl = clickedEl.parents(".oh-kanban__dropdown");
    parentEl.find(".oh-kanban__dropdown-menu").toggleClass("d-none");
  }

  /**
   * Kanban Hide Dropdown
   */
  hideKanbanDropdown(e) {
    e.stopPropagation();
    let targetEl = $(e.target);
    if (
      targetEl.hasClass(".oh-dropdown__items").length ||
      targetEl.hasClass(".oh-dropdown__item").length ||
      targetEl.hasClass(".oh-dropdown__link").length ||
      targetEl.hasClass(".oh-kanban__dropdown-menu").length ||
      targetEl.closest(".oh-kanban__dropdown-toggle").length > 0
    ) {
      return;
    }
    $(".oh-kanban__dropdown-menu").addClass("d-none");
  }

  /**
   * Kanban Delete Section
   */
  deleteKanbanSection(e) {
    e.preventDefault();
    let clickedEl = $(e.target).closest(".oh-kanban__section-delete");
    clickedEl.parents(".oh-kanban__section").remove();
  }
  /**
   * Kanban Delete Card
   */
  deleteKanbanCard(e) {
    e.preventDefault();
    let clickedEl = $(e.target).closest(".oh-kanban__card-delete");
    clickedEl.parents(".oh-kanban__card").remove();
  }

  /**
   * Kanban Card Form
   */
  showKanbanCardForm(e) {
    let clickedEl = $(e.target).closest(".oh-kanban__add-card-btn");
    if (clickedEl.length > 0) {
      clickedEl
        .parents(".oh-kanban__section")
        .find(".oh-kanban__add-card-container")
        .removeClass("d-none");
    }
  }

  /**
   * Show Kanban Card Group
   */
  showKanbanCardGroup(e) {
    e.stopPropagation();
    console.log("hello");
    let clickedEl = $(e.target).closest(".oh-kanban-group__add-card");
    if (clickedEl.length > 0) {
      clickedEl
        .parents(".oh-kanban-group")
        .find(".oh-kanban__add-card-container")
        .removeClass("d-none");
    }
  }

  /**
   * Hide Kanban Card Form
   */
  hideKanbanCardForm(e) {
    let clickedEl = $(e.target).closest(".oh-kanban__add-card-cancel-btn");
    if (clickedEl.length > 0) {
      clickedEl.parents(".oh-kanban__add-card-container").addClass("d-none");
    }
  }

  /**
   * Check for valid input
   */
  checkValid(e) {
    if ($(e.target).val().length > 0) {
      $(e.target)
        .parent()
        .find("button[type='submit']")
        .attr("disabled", false);
    } else {
      $(e.target).parent().find("button[type='submit']").attr("disabled", true);
    }
  }

  /**
   * Kanban Collapse Toggle
   */
  kanbanGroupToggle(e) {
    e.preventDefault();
    let clickedEl = $(e.target).closest(".oh-kanban-group");
    clickedEl.toggleClass("oh-kanban-card--collapsed");
  }

  /**
   * Change Kanban Card Highlight
   */
  changeCardHighlight(e) {
    e.preventDefault();
    let highlightClass = "oh-kanban__card--";
    let patentCardEl = $(e.target).parents(".oh-kanban__card");

    switch (e.target.value) {
      case "1":
        highlightClass += "blue";
        break;
      case "2":
        highlightClass += "green";
        break;
      case "3":
        highlightClass += "amber";
        break;
      case "4":
        highlightClass += "red";
        break;
    }
    // Remove existing class
    if (patentCardEl) {
      if (patentCardEl.hasClass("oh-kanban__card--blue")) {
        patentCardEl.removeClass("oh-kanban__card--blue");
      } else if (patentCardEl.hasClass("oh-kanban__card--red")) {
        patentCardEl.removeClass("oh-kanban__card--red");
      } else if (patentCardEl.hasClass("oh-kanban__card--amber")) {
        patentCardEl.removeClass("oh-kanban__card--amber");
      } else {
        patentCardEl.removeClass("oh-kanban__card--green");
      }
      // Add new class
      patentCardEl.addClass(highlightClass);
    }
  }
}

export default Kanban;
