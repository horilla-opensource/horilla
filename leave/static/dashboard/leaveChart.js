$(document).ready(function () {
  let overAllLeaveChart = null;

  function renderOverAllLeaveChart(data, labels) {
    const ctx = document.getElementById("overAllLeave")?.getContext("2d");
    if (!ctx) return;

    const dataset = [{
      label: "Leave count",
      data: data,
      backgroundColor: ["#cfe9ff", "#ffc9de", "#e6ccff"], // Customize as needed
      borderWidth: 0,
    }];

    if (overAllLeaveChart) {
      overAllLeaveChart.data.labels = labels;
      overAllLeaveChart.data.datasets = dataset;
      overAllLeaveChart.update();
      return;
    }

    overAllLeaveChart = new Chart(ctx, {
      type: "doughnut",
      data: {
        labels: labels,
        datasets: dataset,
      },
      options: {
        cutout: "70%",
        responsive: true,
        maintainAspectRatio: false,
        onClick: (e, activeEls) => {
          if (activeEls.length > 0) {
            const datasetIndex = activeEls[0].datasetIndex;
            const dataIndex = activeEls[0].index;
            const label = e.chart.data.labels[dataIndex];
            const selected = $("#overAllLeaveSelect").val();
            const params = `?department_name=${label}&overall_leave=${selected}`;
            window.location.href = "/leave/request-view" + params;
          }
        },
        plugins: {
          legend: {
            position: "bottom",
            labels: {
              usePointStyle: true,
              pointStyle: "circle",
              padding: 20,
              font: {
                size: 12,
              },
              color: "#000",
            },
          },
          tooltip: {
            padding: 10,
            cornerRadius: 4,
            backgroundColor: "#333",
            titleColor: "#fff",
            bodyColor: "#fff",
            callbacks: {
              label: function (context) {
                return context.parsed;
              },
            },
          },
        },
      },
      plugins: [
        {
          afterRender: (chart) => {
            if (typeof emptyChart === "function") {
              emptyChart(chart);
            }
          },
        },
      ],
    });
  }

  function fetchOverAllLeaveData(overallLeaveType = "today") {
    $.ajax({
      type: "GET",
      url: `/leave/overall-leave?overall_leave=${overallLeaveType}`,
      dataType: "json",
      success: function (response) {
        renderOverAllLeaveChart(response.data, response.labels);
      },
    });
  }

  // Initial chart load
  fetchOverAllLeaveData();

  // Dropdown change event
  $(document).on("change", "#overAllLeaveSelect", function () {
    fetchOverAllLeaveData($(this).val());
  });
});


// $(document).ready(function () {
//   //Todays leave count department wise chart
//   if (document.getElementById("overAllLeave")){
//   var myChart1 = document.getElementById("overAllLeave").getContext("2d");
//     var overAllLeave = new Chart(myChart1, {
//       type: "doughnut",
//       data: {
//         labels: [],
//         datasets: [
//           {
//             label: "Leave count",
//             data: [],
//             backgroundColor: null,
//           },
//         ],
//       },
//       options: {
//         responsive: true,
//         maintainAspectRatio: false,
//         onClick: (e, activeEls) => {
//           let datasetIndex = activeEls[0].datasetIndex;
//           let dataIndex = activeEls[0].index;
//           let datasetLabel = e.chart.data.datasets[datasetIndex].label;
//           let value = e.chart.data.datasets[datasetIndex].data[dataIndex];
//           let label = e.chart.data.labels[dataIndex];
//           params =`?department_name=${label}&overall_leave=${$("#overAllLeaveSelect").val()}`;
//           window.location.href = "/leave/request-view" + params;
//         },
//       },
//       plugins: [
//         {
//           afterRender: (chart) => emptyChart(chart),
//         },
//       ],
//     });
//   }

//   $.ajax({
//     type: "GET",
//     url: "/leave/overall-leave?overall_leave=today",
//     dataType: "json",
//     success: function (response) {
//       if (overAllLeave){
//         overAllLeave.data.labels = response.labels;
//         overAllLeave.data.datasets[0].data = response.data;
//         overAllLeave.data.datasets[0].backgroundColor = null;
//         overAllLeave.update();
//       }
//     },
//   });
//   $(document).on("change", "#overAllLeaveSelect", function () {
//     var selected = $(this).val();
//     $.ajax({
//       type: "GET",
//       url: `/leave/overall-leave?overall_leave=${selected}`,
//       dataType: "json",
//       success: function (response) {
//         overAllLeave.data.labels = response.labels;
//         overAllLeave.data.datasets[0].data = response.data;
//         overAllLeave.data.datasets[0].backgroundColor = null;
//         overAllLeave.update();
//       },
//     });
//   });

//   //Today leave employees chart
// });
