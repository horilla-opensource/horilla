$(document).ready(function () {
  function employeeChart(dataSet, labels) {
    const data = {
      labels: labels,
      datasets: dataSet,
    };
    // Create chart using the Chart.js library
    window["myChart"] = {};
    const ctx = document.getElementById("totalEmployees").getContext("2d");
    employeeChart = new Chart(ctx, {
      type: "doughnut",
      data: data,
      options: {
        responsive: true,
        maintainAspectRatio: false,
        onClick: (e, activeEls) => {
          let datasetIndex = activeEls[0].datasetIndex;
          let dataIndex = activeEls[0].index;
          let datasetLabel = e.chart.data.datasets[datasetIndex].label;
          let value = e.chart.data.datasets[datasetIndex].data[dataIndex];
          let label = e.chart.data.labels[dataIndex];
          var active = "False";
          if (label.toLowerCase() == "active") {
            active = "True";
          }
          localStorage.removeItem("savedFilters");
          window.location.href = "/employee/employee-view?is_active=" + active;
        },
      },
      plugins: [
        {
          afterRender: (chart) => emptyChart(chart),
        },
      ],
    });
  }

  function genderChart(dataSet, labels) {
    const data = {
      labels: labels,
      datasets: dataSet,
    };
    // Create chart using the Chart.js library
    window["genderChart"] = {};
    const ctx = document.getElementById("genderChart").getContext("2d");
    genderChart = new Chart(ctx, {
      type: "doughnut",
      data: data,
      options: {
        responsive: true,
        maintainAspectRatio: false,
        onClick: (e, activeEls) => {
          let datasetIndex = activeEls[0].datasetIndex;
          let dataIndex = activeEls[0].index;
          let datasetLabel = e.chart.data.datasets[datasetIndex].label;
          let value = e.chart.data.datasets[datasetIndex].data[dataIndex];
          let label = e.chart.data.labels[dataIndex];
          localStorage.removeItem("savedFilters");
          window.location.href =
            "/employee/employee-view?gender=" + label.toLowerCase();
        },
      },
      plugins: [
        {
          afterRender: (chart) => emptyChart(chart),
        },
      ],
    });
  }

  function departmentChart(dataSet, labels) {
    const data = {
      labels: labels,
      datasets: dataSet,
    };
    // Create chart using the Chart.js library
    window["departmentChart"] = {};
    const ctx = document.getElementById("departmentChart").getContext("2d");
    departmentChart = new Chart(ctx, {
      type: "doughnut",
      data: data,
      options: {
        responsive: true,
        maintainAspectRatio: false,
        onClick: (e, activeEls) => {
          let datasetIndex = activeEls[0].datasetIndex;
          let dataIndex = activeEls[0].index;
          let datasetLabel = e.chart.data.datasets[datasetIndex].label;
          let value = e.chart.data.datasets[datasetIndex].data[dataIndex];
          let label = e.chart.data.labels[dataIndex];
          localStorage.removeItem("savedFilters");
          window.location.href =
          "/employee/employee-view?department=" + label;

        },
      },
      plugins: [
        {
          afterRender: (chart) => emptyChart(chart),
        },
      ],
    });
  }

  function employeeCount(data) {
    $("#totalEmployeesCount").html(data["total_employees"]);
    $("#newbie").html(data["newbies_week"]);
    $("#newbiePerc").html(data["newbies_week_percentage"]);
    $("#newbieToday").html(data["newbies_today"]);
    $("#newbieTodayPerc").html(data["newbies_today_percentage"]);
  }

  $.ajax({
    url: "/employee/dashboard-employee",
    type: "GET",
    success: function (response) {
      // Code to handle the response
      dataSet = response.dataSet;
      labels = response.labels;

      employeeChart(dataSet, labels);
    },
  });

  $.ajax({
    url: "/employee/dashboard-employee-gender",
    type: "GET",
    success: function (response) {
      // Code to handle the response
      dataSet = response.dataSet;
      labels = response.labels;
      genderChart(dataSet, labels);
    },
  });

  $.ajax({
    url: "/employee/dashboard-employee-department",
    type: "GET",
    success: function (response) {
      // Code to handle the response
      dataSet = response.dataSet;
      labels = response.labels;
      departmentChart(dataSet, labels);
    },
    error: function (error) {
      console.log(error);
    },
  });

  $.ajax({
    url: "/employee/dashboard-employee-count",
    type: "GET",
    success: function (response) {
      // Code to handle the response
      employeeCount(response);
    },
  });

  $(".oh-card-dashboard__title").click(function (e) {
    var chartType = myChart.config.type;
    if (chartType === "line") {
      chartType = "bar";
    } else if (chartType === "bar") {
      chartType = "doughnut";
    } else if (chartType === "doughnut") {
      chartType = "pie";
    } else if (chartType === "pie") {
      chartType = "line";
    }
    myChart.config.type = chartType;
    myChart.update();
  });
});
