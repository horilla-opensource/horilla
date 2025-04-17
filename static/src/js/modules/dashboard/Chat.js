import $ from "jquery";

class Chat {
  constructor() {
    this.sideBarBtn =  $(".oh-chat--sidebar-toggle-btn");
    this.events();
  }

  // Events
  events() {
    // Dashboard Event Slider
    console.log(this.sideBarBtn);
    this.sideBarBtn.on(
      "click",
      this.toggleSidebar.bind(this)
    );
    $(".oh-chat__sidebar-close-btn").on(
      "click",
      this.closeSidebar.bind(this)
    );
  }
  // Methods

  /**
   * Toggle Sidebar
   */
  toggleSidebar(e) {
    const sidebarEl = $(".oh-chat__sidebar");
    sidebarEl.toggleClass("oh-chat__sidebar--show");
  }
  /**
   * Close Sidebar
   */
  closeSidebar(e) {
    const sidebarEl = $(".oh-chat__sidebar");
    sidebarEl.removeClass("oh-chat__sidebar--show");
  }
}

export default Chat;
