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
      options: {},
    });
    $("#totalEmployees").on("click", function (event) {
      var activeBars = employeeChart.getElementsAtEventForMode(
        event,
        "index",
        { intersect: true },
        true
      );
      if (activeBars.length > 0) {
        var clickedBarIndex = activeBars[0].index;
        var clickedLabel = data.labels[clickedBarIndex];
        localStorage.removeItem("savedFilters")
        window.location.href =  "/employee/employee-view?is_active="+clickedLabel.toLowerCase()
      }
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
      options: {},
    });
    $("#genderChart").on("click", function (event) {
      var activeBars = genderChart.getElementsAtEventForMode(
        event,
        "index",
        { intersect: true },
        true
      );

      if (activeBars.length > 0) {
        var clickedBarIndex = activeBars[0].index;
        var clickedLabel = data.labels[clickedBarIndex];
        localStorage.removeItem("savedFilters")
        window.location.href =  "/employee/employee-view?gender="+clickedLabel.toLowerCase()
      }
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
      options: {},
    });
    $("#departmentChart").on("click", function (event) {
      var activeBars = departmentChart.getElementsAtEventForMode(
        event,
        "index",
        { intersect: true },
        true
      );

      if (activeBars.length > 0) {
        var clickedBarIndex = activeBars[0].index;
        var clickedLabel = data.labels[clickedBarIndex];
        localStorage.removeItem("savedFilters")
        window.location.href =  "/employee/employee-view?department="+clickedLabel
      }
    });
  }

  function employeeCount(data){

    $("#totalEmployeesCount").html(data['total_employees'])
    $("#newbie").html(data['newbies_week'])
    $("#newbiePerc").html(data['newbies_week_percentage'])
    $("#newbieToday").html(data['newbies_today'])
    $("#newbieTodayPerc").html(data['newbies_today_percentage'])
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
      if (isChartEmpty(dataSet)) {
				$("#departmentChart").parent().html(
					`<div style="height: 325px; display:flex;align-items: center;justify-content: center;" class="">
					<div style="" class="">
					<img style="display: block;width: 70px;margin: 20px auto ;" src="/static/images/ui/joiningchart.png" class="" alt=""/>
					<h3 style="font-size:16px" class="oh-404__subtitle">${response.message}</h3>
					</div>
				</div>`
				);
			} else {
      departmentChart(dataSet, labels);
      }
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
      employeeCount(response)
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