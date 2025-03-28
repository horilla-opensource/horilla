import $ from "jquery";
require("orgchart");

class OrgChart {
  constructor() {
    this.events();
  }

  // Events
  events() {
    // Trigger OrgChart initialization on window load.
    $(window).on("load", this.initOrgChart.bind(this));
  }

  // Methods

  /**
   * Initialize OrgChart
   */
  initOrgChart() {
    const chartDisplayEl = $("#chart-container");
    if (chartDisplayEl.length > 0) {
      $("#chart-container").orgchart({
        data: datascource,
        nodeContent: "title",
      });
    }
  }
}

export default OrgChart;
