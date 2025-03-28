import $ from "jquery";
import moment from "moment";

class WorkEntry {
  constructor() {
    this.events();
    this.monthView = true;
  }

  // Events
  events() {
    // Print out calendar columns for current month.
    $(window).on(
      "load",
      this.monthCells.bind(this, moment().month() + 1, moment().year())
    );
    // $(window).on("load", this.weekCells.bind(this, moment()));
    $('[data-we-navigate="month-next"]').on(
      "click",
      this.navigateMonth.bind(this, "next")
    );
    $('[data-we-navigate="month-prev"]').on(
      "click",
      this.navigateMonth.bind(this, "prev")
    );
    $("#toggleView").on("click", this.switchView.bind(this));
  }

  // Methods

  /**
   * Switch View
   */
  switchView() {
    // Clear all cells
    this.clearCells();
    this.monthView = !this.monthView;
    if (this.monthView) {
      this.monthCells(moment().month() + 1, moment().year());
      $("#toggleView").text("Week");
    } else {
      this.weekCells(moment());
      // Change button text
      $("#toggleView").text("Month");
    }
    $(".oh-we-calendar").toggleClass("oh-we-calendar--week");
  }

  /**
   * Month Cells
   */
  monthCells(month, year) {
    let daysOfMonth = moment(`${month}, ${year}`, "MM, YYYY").daysInMonth();

    // Select parent element to render the cells.
    let monthCellsParentEl = document.querySelector(
      '[data-we-cells="true"]'
    )?.id;

    // Display selected month
    let monthHeaderEl = document.querySelector('[data-we-header="true"]')?.id;

    // Populate attribute with selected month & year -- Used for next and previous navigation.
    $('[data-we-month="true"]').attr("data-we-number", month);
    $('[data-we-month="true"]').attr("data-we-year", year);

    this.generateTableHeader(monthHeaderEl, daysOfMonth, "month");

    this.displayMonthYear(month, year);

    if (workEntries) {
      workEntries.map((entry) => {
        this.generateCells(monthCellsParentEl, daysOfMonth, entry);
      });
    }
  }

  /**
   * Week Cells
   */
  weekCells(today) {
    // Select parent element to render the cells.
    let monthCellsParentEl = document.querySelector(
      '[data-we-cells="true"]'
    )?.id;

    // Display selected month
    let monthHeaderEl = document.querySelector('[data-we-header="true"]')?.id;
    // const today = moment().add(1, "weeks");

    const from_date = today.clone().startOf("week");
    const to_date = today.clone().endOf("week");

    let dayArray = [];
    for (let i = from_date; i.diff(to_date) != true; i.add(1, "days")) {
      dayArray.push(i.format("dddd, D"));
    }

    // Render table header
    this.generateTableHeader(monthHeaderEl, 7, "week", dayArray);
    // Render table cells
    if (workEntries) {
      workEntries.map((entry) => {
        this.generateCells(monthCellsParentEl, 6, entry);
      });
    }
  }

  /**
   * Generate Table Header
   */
  generateTableHeader(selector, count, type, dayArray) {
    let row =
      "<div class='oh-we-calendar__header'><div class='oh-we-calendar__header-cell oh-we-calendar__header-cell--title'>Work Entries</div>";

    if (type === "month") {
      for (let i = 0; i <= count; i++) {
        row += `<div class='oh-we-calendar__header-cell'>${i}</div>`;
      }
    } else {
      for (let i = 0; i < dayArray.length; i++) {
        row += `<div class='oh-we-calendar__header-cell'>${dayArray[i]}</div>`;
      }
    }

    row += "</div>";
    $(`#${selector}`).append(row);
  }
  /**
   * Generate Cells
   */
  generateCells(selector, count, entry) {
    let row = `<div class='oh-we-calendar__row'><div class='oh-we-calendar__cell oh-we-calendar__cell--name'>${entry.name}</div>`;

    for (let i = 0; i <= count; i++) {
      row += "<div class='oh-we-calendar__cell'></div>";
    }

    row += "</div>";

    $(`#${selector}`).append(row);
  }

  /*
   * Display Month
   */
  displayMonthYear(monthNumber, year) {
    let displayEl = document.querySelector('[data-we-month="true"]');

    if (displayEl) {
      const monthName = moment(monthNumber, "MM").format("MMMM");
      displayEl.innerText = `${monthName}, ${year}`;
    }
  }

  /**
   * Navigate Months
   */
  navigateMonth(action) {
    let month = this.currentDisplayedMonthOrYear("month");
    let year = this.currentDisplayedMonthOrYear("year");

    if (action === "prev") {
      if (month === 1) {
        month = 12;
        year--;
      } else {
        month--;
      }
    } else {
      if (month === 12) {
        month = 1;
        year++;
      } else {
        month++;
      }
    }

    this.clearCells();
    this.monthCells(month, year);
  }

  /**
   *  Get current month in display
   */
  currentDisplayedMonthOrYear(type) {
    if (type === "month") {
      let currentMonth = +$('[data-we-month="true"]').attr("data-we-number");
      return currentMonth;
    } else {
      let currentYear = +$('[data-we-month="true"]').attr("data-we-year");
      return currentYear;
    }
  }

  /**
   * Clear all cells
   */
  clearCells() {
    // Clear header
    $('[data-we-header="true"]').html("");
    // Clear Body
    $('[data-we-cells="true"]').html("");
  }
}

export default WorkEntry;
