import $ from "jquery";

class Faq {
  constructor() {
    this.headerEl = $(".oh-faq__item-header");
    this.events();
  }

  events() {
    this.headerEl.on("click", this.toggleFaq.bind(this));
  }

  toggleFaq(e) {
    const targetEl = $(e.target);
    const selectedItemEl = targetEl.parents(".oh-faq__item");

    console.log(targetEl.hasClass("oh-btn"), targetEl.hasClass("oh-faq__tag"), targetEl.hasClass("oh-faq__tag"))
    if (selectedItemEl) {
      if (
        !targetEl.hasClass("oh-btn") &&
        !targetEl.hasClass("oh-faq__tag") &&
        !targetEl.hasClass("oh-faq__tags") &&
        !targetEl.hasClass("icon-inner")
      ) {
        selectedItemEl.toggleClass("oh-faq__item--show");
      }
    }
  }
}

export default Faq;
