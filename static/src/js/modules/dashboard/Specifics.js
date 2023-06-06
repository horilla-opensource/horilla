import $ from "jquery";
import "select2";
import "select2/dist/css/select2.css";

class Specifics {
  constructor() {
    this.events();
  }

  // Events
  events() {
    // Select 2 Trigger
    $(window).on("load", this.loadSelect2.bind(this));
  }

  // Methods

  /**
   * Initialize Select 2
   */
  loadSelect2() {
    $(".oh-select--qa-change").each(function (item, element) {
      let targetDiv = element.closest(".oh-section-edit");
      let optionDiv = targetDiv.querySelector(".oh-link__expanded");
      let selectedValue = element.options[element.selectedIndex].text;
      if (selectedValue == "Multi-choices") {
        optionDiv.classList.remove("d-none");
      } else {
        optionDiv.classList.add("d-none");
      }
    });

    $(".oh-select--qa-change").on("select2:select", function (e) {
      let data = e.params.data;
      let targetDiv = e.target.closest(".oh-section-edit");
      let optionDiv = targetDiv.querySelector(".oh-link__expanded");
      if (data.text == "Multi-choices") {
        optionDiv.classList.remove("d-none");
      } else {
        optionDiv.classList.add("d-none");
      }
    });
  }
}

export default Specifics;
