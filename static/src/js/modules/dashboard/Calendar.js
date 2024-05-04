import $ from "jquery";
import datepicker from "js-datepicker";
import "js-datepicker/dist/datepicker.min.css";

class Calendar {
  constructor() {
    this.events();
  }

  // Events
  events() {
    // Calendar Selector
    $(window).on("load", this.initCalendar.bind(this));
    $(window).on("load", this.initCalendarEmbed.bind(this));
  }

  // Methods

  /**
   * Initialize Calendar
   */
  initCalendar(e) {
    let calEls = document.querySelectorAll(".oh-calendar-input");
    calEls.forEach(function (calEl) {
      datepicker(calEl, {
        customDays: ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"],
        formatter: (input, date, instance) => {
          const value = date.toLocaleDateString();
          input.value = value;
        },
      });
    });
  }

  /**
   * Embedded Calendar
   */
  initCalendarEmbed(e) {
    let calStartEls = document.querySelector(".oh-timeoff-date--start");
    let calEndEls = document.querySelector(".oh-timeoff-date--end");
    if (calStartEls && calEndEls) {
      datepicker(".oh-timeoff-date--start", {
        id: 1,
        alwaysShow: false,
        customDays: ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"],
        formatter: (input, date, instance) => {
          const value = date.toLocaleDateString();
          input.value = value;
        },
      });
      datepicker(".oh-timeoff-date--end", {
        id: 1,
        alwaysShow: false,
        customDays: ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"],
        formatter: (input, date, instance) => {
          const value = date.toLocaleDateString();
          input.value = value;
        },
      });
    }

  }
}

export default Calendar;
