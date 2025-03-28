import $ from 'jquery'

class LoadLayout {

  constructor() {
    this.events();
  }

  // Events
  events() {
    $(window).on('load', this.loadHeader.bind(this));
  }

  // Methods

  /**
   *  Loads header from the templates.
   */
  loadHeader() {
    $("#sidebar").load("./../../templates/sidebar.html");
    $("#mainNav").load("./../../templates/navbar.html");
  }

}

export default LoadLayout;
