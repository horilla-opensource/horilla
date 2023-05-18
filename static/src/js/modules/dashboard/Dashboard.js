import $ from "jquery";

class Dashboard {
  constructor() {
    this.events();
  }

  // Events
  events() {
    // Dashboard Event Slider
    $(".oh-dashboard__events-nav-item").on("click", this.moveSlider.bind(this));
    // Move Dashboard Event Slider Automatically
    $(window).on("load", this.moveSliderAuto.bind(this));
    // Add Random colors to slides
    $(window).on("load", this.applySlideColors.bind(this));
  }

  // Methods

  /**
   * Events slider: Move slides
   */
  moveSlider(e) {
    let clickedEl = $(e.target).closest(".oh-dashboard__events-nav-item");
    let targetSlideNumber = +clickedEl.data("target");
    let sliderReel = $(".oh-dashbaord__events-reel");

    if (targetSlideNumber >= 0 && sliderReel.length > 0) {
      sliderReel[0].style.transform = `translateX(-${
        targetSlideNumber * 100
      }%)`;
      // Remove existing active class
      $(".oh-dashboard__events-nav-item--active").removeClass(
        "oh-dashboard__events-nav-item--active"
      );
      clickedEl.addClass("oh-dashboard__events-nav-item--active");
    }
  }

  /**
   * Events slider: Move slider periodically
   */
  moveSliderAuto() {
    let slideElements = $(".oh-dashboard__events-nav-item");

    if (slideElements.length > 0) {
      let sliderReel = $(".oh-dashbaord__events-reel");

      // Iterator
      let i = 0;

      // Move slider in an interval of 5 seconds
      setInterval(function () {
        // Increment iterator
        i++;
        // Reset iterator
        if (i == slideElements.length) {
          i = 0;
        }

        sliderReel[0].style.transform = `translateX(-${i * 100}%)`;
        let currSlide = $(`.oh-dashboard__events-nav-item[data-target="${i}"]`);
        // Remove existing active class
        $(".oh-dashboard__events-nav-item--active").removeClass(
          "oh-dashboard__events-nav-item--active"
        );
        // Add active class to new slide
        currSlide.addClass("oh-dashboard__events-nav-item--active");
      }, 5000);
    }
  }

  /**
   * Event Slider: Apply Random Colors
   */

  applySlideColors() {
    // Get slider elements
    let sliderEls = $(".oh-dashboard__event");

    if (sliderEls.length > 0) {
      const colors = [
        "#16a085",
        "#2980b9",
        "#e74c3c",
        "#8e44ad",
        "#f39c12",
        "#c0392b",
        "#6F1E51",
        "#5758BB",
      ];

      sliderEls.each(function (index, sliderEl) {
        // Generate a color key based on a random number between the number of colors
        let colorKey = Math.floor(Math.random() * colors.length);

        if (sliderEl) {
          sliderEl.style.backgroundColor = colors[colorKey];
        }
      });
    }
  }
}

export default Dashboard;
