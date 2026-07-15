(function () {
  "use strict";

  var mobileViewport = window.matchMedia("(max-width: 767.98px)");

  function closeInheritedSidebarOnMobile(event) {
    if (!event.matches) {
      return;
    }
    var wrapper = document.querySelector(".oh-wrapper-main");
    if (!wrapper) {
      return;
    }
    wrapper.classList.add("oh-wrapper-main--closed");
    try {
      window.localStorage.setItem("sidebarOpen", "false");
    } catch (error) {
      // The layout still closes when storage is unavailable.
    }
  }

  closeInheritedSidebarOnMobile(mobileViewport);
  if (mobileViewport.addEventListener) {
    mobileViewport.addEventListener("change", closeInheritedSidebarOnMobile);
  } else {
    mobileViewport.addListener(closeInheritedSidebarOnMobile);
  }
})();
