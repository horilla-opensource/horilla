import $, { nodeName } from "jquery";

class Inputs {
  constructor() {
    this.events();
  }

  // Events
  events() {
    // Picker Event
    $(".oh-input-picker").on("click", this.togglePicker.bind(this));
    // // Selection Edit
    // $(".oh-btn--section-edit").on("click", this.editSection.bind(this));
    // Selection Edit
    $(".oh-btn--section-edit").on("click", this.editSectionShow.bind(this));
    // // Selection Edit Cancel
    // $(".oh-section-edit--cancel").on("click", this.cancelSection.bind(this));
    // Selection Edit Cancel
    $(".oh-section-edit--cancel").on("click", this.cancelSectionHide.bind(this));
    // Password Input Toggle
    $(".oh-password-input--toggle").on("click", this.passwordShowToggle.bind(this));
    // Input Resize Automatic
    $(".oh-input--resize").on("keyup", this.resizeInput.bind(this));
  }

  // Methods

  /**
   *  Toggling Input Picker
   */
  togglePicker(e) {
    let targetEl = e.target.closest(".oh-input-picker");
    let targetInput = targetEl.querySelector("input");

    if (targetEl && targetInput) {
      targetInput.checked = true;
      let currentSelections = targetEl.parentElement.querySelectorAll(
        ".oh-input-picker--selected"
      );
      currentSelections.forEach(function (currentSelection) {
        currentSelection.classList.remove("oh-input-picker--selected");
      });
      targetEl.classList.add("oh-input-picker--selected");
    }
  }

  /**
   * Section Edit
   */
  editSection(e) {
    e.preventDefault();
    let closestTargetEl = e.target.closest(".oh-btn--section-edit");
    let targetEl = closestTargetEl.dataset.target;
    let parentEl = closestTargetEl.parentElement;

    // Hide Edit Button
    closestTargetEl.classList.add('d-none');
    // Inputs
    let inputEls = parentEl.querySelectorAll(`${targetEl} input`);
    inputEls.forEach(function (element) {
      element.disabled = false;
    });
    // Selects
    let selectEl = parentEl.querySelectorAll(`${targetEl} select`);
    selectEl.forEach(function (element) {
      element.disabled = false;
    });

    let actionDiv = document.createElement("div");
    actionDiv.classList.add('oh-list__actions');
    parentEl.appendChild(actionDiv);

    // Create and add save, delete and cancel button to the DOM
    let deleteBtn = document.createElement("a");
    let deleteBtnEl = document.createTextNode("Delete");
    deleteBtn.appendChild(deleteBtnEl);
    deleteBtn.href = "#";
    deleteBtn.classList.add("oh-btn");
    deleteBtn.classList.add("oh-btn--danger-link");
    deleteBtn.classList.add("oh-section-edit--delete");
    deleteBtn.addEventListener("click", this.cancelSection.bind(this));
    actionDiv.appendChild(deleteBtn);

    let cancelBtn = document.createElement("a");
    let cancelLinkEl = document.createTextNode("Cancel");
    cancelBtn.appendChild(cancelLinkEl);
    cancelBtn.href = "#";
    cancelBtn.classList.add("oh-btn");
    cancelBtn.classList.add("oh-btn--light");
    cancelBtn.classList.add("me-2");
    cancelBtn.classList.add("oh-section-edit--cancel");
    cancelBtn.addEventListener("click", this.cancelSection.bind(this));
    actionDiv.appendChild(cancelBtn);

    let saveBtn = document.createElement("a");
    let saveLinkEl = document.createTextNode("Save");
    saveBtn.appendChild(saveLinkEl);
    saveBtn.href = "#";
    saveBtn.classList.add("oh-btn");
    saveBtn.classList.add("oh-btn--secondary");
    saveBtn.classList.add("oh-section-edit--save");
    saveBtn.classList.add("d-inline-flex");
    actionDiv.appendChild(saveBtn);
  }

  /**
   * Section Show
   */
    editSectionShow(e) {
      e.preventDefault();
      let closestTargetEl = e.target.closest(".oh-btn--section-edit");
      let targetEl = closestTargetEl.dataset.target;
      let parentEl = closestTargetEl.parentElement;

      // Hide Edit Button
      closestTargetEl.classList.add('d-none');
      // Inputs
      let inputEls = parentEl.querySelectorAll(`${targetEl} input`);
      inputEls.forEach(function (element) {
        element.disabled = false;
      });
      // Selects
      let selectEl = parentEl.querySelectorAll(`${targetEl} select`);
      selectEl.forEach(function (element) {
        element.disabled = false;
      });
      // Hide/Show Actions Detail
      let parentContainerEl = closestTargetEl.closest('.oh-section-edit');
      let actionsContainerEl = parentContainerEl.querySelector('.oh-list__actions');
      actionsContainerEl.classList.remove('d-none');
    }

  //  /**
  //  * Cancel Section Edit
  //  */
  //  cancelSection(e) {
  //   e.preventDefault();
  //   let closestTargetEl = e.target.closest(".oh-section-edit--cancel");
  //   let parentEl = closestTargetEl.closest('.oh-section-edit');
  //   // Show Edit Button
  //   closestTargetEl.classList.remove('d-none');
  //   // Inputs
  //   let inputEls = parentEl.querySelectorAll('input');
  //   inputEls.forEach(function (element) {
  //     element.disabled = true;
  //   });
  //   // Selects
  //   let selectEl = parentEl.querySelectorAll('select');
  //   selectEl.forEach(function (element) {
  //     element.disabled = true;
  //   });

  //   // Remove cancel and save button
  //   parentEl.querySelector('.oh-section-edit--cancel').remove();
  //   parentEl.querySelector('.oh-section-edit--save').remove();
  //   parentEl.querySelector('.oh-section-edit--delete').remove();
  //   parentEl.querySelector('.oh-btn--section-edit').classList.remove('d-none');
  // }

   /**
   * Section Hide
   */
  cancelSectionHide(e){
    e.preventDefault();
    let closestTargetEl = e.target.closest(".oh-section-edit--cancel");
    let parentEl = closestTargetEl.closest('.oh-section-edit');

    parentEl.querySelector('.oh-btn--section-edit ').classList.remove('d-none');
    // Inputs
    let inputEls = parentEl.querySelectorAll(`input`);
    inputEls.forEach(function (element) {
      element.disabled = true;
    });
    // Selects
    let selectEl = parentEl.querySelectorAll(`select`);
    selectEl.forEach(function (element) {
      element.disabled = true;
    });
    // Hide/Show Actions Detail
    let actionsContainerEl = parentEl.querySelector('.oh-list__actions');
    actionsContainerEl.classList.add('d-none');
  }

  /**
   *  Password Show/Hide Toggle
   */
  passwordShowToggle(e){
    e.preventDefault();
    let targetEl = $(e.target).closest('.oh-password-input--toggle');
    let showIcon = targetEl.find('.oh-passowrd-input__show-icon');
    let hideIcon = targetEl.find('.oh-passowrd-input__hide-icon');
    let passwordInput  = targetEl.parent().find('.oh-input--password');

    if(passwordInput.attr('type') == 'password'){
      passwordInput.attr('type', 'text');
      showIcon.addClass('d-none');
      hideIcon.removeClass('d-none');
    }else{
      passwordInput.attr('type', 'password');
      showIcon.removeClass('d-none');
      hideIcon.addClass('d-none');
    }
  }

  /**
   *  Resize Input
   */
  resizeInput(e){
    $(e.target).attr('size', $(e.target).val().length);
  }
}

export default Inputs;
