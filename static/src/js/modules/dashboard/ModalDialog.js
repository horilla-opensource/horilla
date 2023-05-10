import $ from 'jquery'

class ModalDialog {

  constructor() {
    this.events();
  }

  // Events
  events() {
    // Generic Modal Events
    $("[data-toggle='oh-modal-toggle']").on('click', this.openModal.bind(this));
    $('.oh-modal__close, .oh-modal__cancel').on('click', this.closeModal.bind(this));
    // Activity Sidebar Events
    $('.oh-activity-sidebar__open').on('click', this.openActivitySidebar.bind(this));
    $('.oh-activity-sidebar__close').on('click', this.closeActivitySidebar.bind(this));

  }

  // Methods

  /**
   *  Opem modal dialog
   */
  openModal(e) {
    let clickedEl = $(e.target).closest('[data-toggle = "oh-modal-toggle"]');
    if (clickedEl != null) {
      const targetEl = clickedEl.data('target');
      $(targetEl).addClass('oh-modal--show');
    }
  }

  /**
   *  Close modal dialog
   */
  closeModal() {
    $('.oh-modal--show').removeClass('oh-modal--show');
  }

  /**
   *  Open activity sidebar dialog
   */
  openActivitySidebar(e) {
    let targetEl = e.target.dataset.target;
    if (targetEl) {
      $(targetEl).addClass('oh-activity-sidebar--show');
    }
  }

  /**
   *  Close activity sidebar dialog
   */
  closeActivitySidebar(e) {
    let targetEl = e.target.dataset.target;
    if (targetEl) {
      e.target.closest(targetEl).classList.remove('oh-activity-sidebar--show');
    }
  }

}

export default ModalDialog;