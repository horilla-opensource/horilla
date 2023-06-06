import $ from "jquery";

class Recruitment {
  constructor() {
    this.events();
  }

  // Events
  events() {
    // Calendar Selector
    $(".oh-recruitment-action--create-tab").on(
      "click",
      this.addNewTab.bind(this)
    );
  }

  // Methods

  /**
   * Add New Tab
   */
  addNewTab(e) {
    let clickedEl = $(e.target).closest(".oh-recruitment-action--create-tab");
    let emptyParentEl = $(e.target).parent('.oh-empty');
    let targetEl = clickedEl.data("target");

    $(targetEl).removeClass("d-none");
    emptyParentEl.addClass("d-none");
  }
}

export default Recruitment;
