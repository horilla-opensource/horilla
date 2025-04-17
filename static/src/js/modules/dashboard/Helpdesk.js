class Helpdesk {
  constructor() {
    this.ticketHeaderEl = document.querySelector(".oh-helpdesk__right-header");
    this.ticketDetailsEl = document.querySelector(".oh-helpdesk__right-body");
    this.events();
  }

  events() {
    if (this.ticketHeaderEl && this.ticketDetailsEl) {
      this.ticketHeaderEl.addEventListener(
        "click",
        this.showHideTicketDetails.bind(this)
      );
    }
  }
  /**
   * Show / hide ticket details on mobile devices.
   */
  showHideTicketDetails() {
    this.ticketHeaderEl.classList.toggle("oh-helpdesk__right-header--active");
    this.ticketDetailsEl.classList.toggle("oh-helpdesk__right-body--show");
  }
}

export default Helpdesk;
