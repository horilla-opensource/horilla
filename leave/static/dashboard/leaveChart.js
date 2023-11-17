$(document).ready(function () {
  //Todays leave count department wise chart
  var myChart1 = document.getElementById("overAllLeave").getContext("2d");
  var overAllLeave = new Chart(myChart1, {
    type: "doughnut",
    data: {
      labels: [],
      datasets: [
        {
          label: "Leave count",
          data: [],
          backgroundColor: null,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      onClick: (e, activeEls) => {
        let datasetIndex = activeEls[0].datasetIndex;
        let dataIndex = activeEls[0].index;
        let datasetLabel = e.chart.data.datasets[datasetIndex].label;
        let value = e.chart.data.datasets[datasetIndex].data[dataIndex];
        let label = e.chart.data.labels[dataIndex];
        params =
          "?department_name=" +
          label +
          "&overall_leave=" +
          $("#overAllLeaveSelect").val();
        window.location.href = "/leave/request-view" + params;
      },
    },
    plugins: [
      {
        afterRender: (chart) => emptyChart(chart),
      },
    ],
  });

  $.ajax({
    type: "GET",
    url: "/leave/overall-leave?overall_leave=today",
    dataType: "json",
    success: function (response) {
      overAllLeave.data.labels = response.labels;
      overAllLeave.data.datasets[0].data = response.data;
      overAllLeave.data.datasets[0].backgroundColor = null;
      overAllLeave.update();
    },
  });
  $(document).on("change", "#overAllLeaveSelect", function () {
    var selected = $(this).val();
    $.ajax({
      type: "GET",
      url: `/leave/overall-leave?overall_leave=${selected}`,
      dataType: "json",
      success: function (response) {
        overAllLeave.data.labels = response.labels;
        overAllLeave.data.datasets[0].data = response.data;
        overAllLeave.data.datasets[0].backgroundColor = null;
        overAllLeave.update();
      },
    });
  });

  //Today leave employees chart
  $.ajax({
    type: "GET",
    url: "/leave/employee-leave",
    dataType: "json",
    success: function (response) {
      $.each(response.employees, function (index, value) {
        $("#leaveEmployee").append(
          `<li class="oh-card-dashboard__user-item">
                <div class="oh-profile oh-profile--md">
                  <div class="oh-profile__avatar mr-1">
                    <img src="https://ui-avatars.com/api/?name=${value}&background=random" class="oh-profile__image"
                      alt="Beth Gibbons" />
                  </div>
                  <span class="oh-profile__name oh-text--dark">${value}</span>
                </div>
              </li>
              `
        );
      });
    },
  });
});
