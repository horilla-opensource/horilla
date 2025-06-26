staticUrl = $("#statiUrl").attr("data-url");

$(document).ready(function () {
  var today = new Date();
  var availableLeaveChart;
  var departmentLeaveChart;
  var leaveTypeChart;
  var leavePeriodChart;
  var myChart2 = document.getElementById("employeeLeave");
  var employeeLeaveChart = new Chart(myChart2, {
    type: "bar",
    data: {
      labels: [],
      datasets: [],
    },
  });
  var start_index = 0;
  var per_page = 10;

  month = ("0" + (today.getMonth() + 1)).slice(-2);
  year = today.getFullYear();
  $(".month").val(`${year}-${month}`);
  $("#dash_month").val(`${year}-${month}`);
  $("#dash_department_month").val(`${year}-${month}`);
  $("#dash_leave_type_month").val(`${year}-${month}`);

  function isChartEmpty(chartData) {
    if (!chartData) {
      return true;
    }
    for (let i = 0; i < chartData.length; i++) {
      const hasNonZeroValues = chartData[i].data.some((value) => value !== 0);
      if (hasNonZeroValues) {
        return false; // Return false if any non-zero value is found
      }
    }
    return true; // Return true if all values are zero
  }

  //Employee wise chart for available leaves
  // function available_leave_chart(dataSet) {
  //   var myChart1 = document.getElementById("availableLeave");
  //   availableLeaveChart = new Chart(myChart1, {
  //     type: "pie",
  //     data: {
  //       labels: dataSet.labels,
  //       datasets: dataSet.dataset,
  //     },
  //   });
  // }

  function available_leave_chart(dataSet) {
    const colors = ['#a5b4fc', '#fca5a5', '#fdba74', '#86efac', '#fbbf24', '#c084fc'];
    const visibility = dataSet.labels.map(() => true);
    const ctx = document.getElementById("availableLeave")?.getContext("2d");

    if (!ctx || !dataSet?.dataset?.length) return;

    const dataset = {
      data: dataSet.dataset[0].data,
      backgroundColor: colors.slice(0, dataSet.labels.length),
      borderColor: '#fff',
      borderWidth: 2
    };

    if (availableLeaveChart) {
      availableLeaveChart.destroy();
    }

    availableLeaveChart = new Chart(ctx, {
      type: "pie",
      data: {
        labels: dataSet.labels,
        datasets: [dataset]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            enabled: true,
            backgroundColor: "#111827",
            bodyColor: "#f3f4f6",
            borderColor: "#e5e7eb",
            borderWidth: 1,
          }
        }
      }
    });

    // 🧩 Custom interactive legend (must exist in HTML)
    const legendContainer = document.getElementById("availableLeaveLegend");
    if (!legendContainer) return;

    legendContainer.innerHTML = "";
    dataSet.labels.forEach((label, i) => {
      const colorDot = `<span class="inline-block w-3 h-3 mr-2 rounded-full" style="background-color: ${colors[i]};"></span>`;
      const labelText = `<span>${label}</span>`;
      const item = document.createElement("div");
      item.className = "cursor-pointer text-sm flex items-center mb-2 text-gray-700";
      item.innerHTML = `${colorDot}${labelText}`;

      item.addEventListener("click", () => {
        visibility[i] = !visibility[i];
        availableLeaveChart.data.datasets[0].data = dataSet.dataset[0].data.map((val, idx) =>
          visibility[idx] ? val : 0
        );
        availableLeaveChart.data.datasets[0].backgroundColor = colors.map((col, idx) =>
          visibility[idx] ? col : '#e5e7eb'
        );
        availableLeaveChart.update();

        const dot = item.querySelector('span:first-child');
        const labelSpan = item.querySelector('span:last-child');
        dot.style.opacity = visibility[i] ? '1' : '0.4';
        labelSpan.style.textDecoration = visibility[i] ? 'none' : 'line-through';
      });

      legendContainer.appendChild(item);
    });
  }


  // function department_leave_chart(dataSet) {
  //   var myChart3 = document.getElementById("departmentLeave");
  //   departmentLeaveChart = new Chart(myChart3, {
  //     type: "pie",
  //     data: {
  //       labels: dataSet.labels,
  //       datasets: dataSet.dataset,
  //     },
  //   });
  // }
  function department_leave_chart(dataSet) {
    const colors = ['#a5b4fc', '#fca5a5', '#fdba74', '#86efac', '#fbbf24', '#c084fc'];
    const visibility = dataSet.labels.map(() => true);
    const ctx = document.getElementById("departmentLeave").getContext("2d");

    // Ensure dataset is single pie-type (merge if needed)
    const dataset = {
      data: dataSet.dataset[0].data,
      backgroundColor: colors.slice(0, dataSet.labels.length),
      borderColor: '#fff',
      borderWidth: 2
    };

    if (departmentLeaveChart) {
      departmentLeaveChart.destroy();
    }

    departmentLeaveChart = new Chart(ctx, {
      type: "pie",
      data: {
        labels: dataSet.labels,
        datasets: [dataset]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: { enabled: true }
        }
      }
    });

    // Interactive legend — assumes #departmentPieLegend exists in HTML
    const legendContainer = document.getElementById("departmentPieLegend");
    if (!legendContainer) return;

    legendContainer.innerHTML = '';
    dataSet.labels.forEach((label, i) => {
      const colorDot = `<span class="inline-block w-3 h-3 mr-2 rounded-full" style="background-color: ${colors[i]};"></span>`;
      const labelText = `<span>${label}</span>`;
      const item = document.createElement("div");
      item.className = "cursor-pointer text-sm flex items-center mb-2 text-gray-700";
      item.innerHTML = `${colorDot}${labelText}`;
      item.addEventListener("click", () => {
        visibility[i] = !visibility[i];
        departmentLeaveChart.data.datasets[0].data = dataSet.dataset[0].data.map((val, idx) =>
          visibility[idx] ? val : 0
        );
        departmentLeaveChart.data.datasets[0].backgroundColor = colors.map((col, idx) =>
          visibility[idx] ? col : '#e5e7eb'
        );
        departmentLeaveChart.update();

        const dot = item.querySelector('span:first-child');
        const label = item.querySelector('span:last-child');
        dot.style.opacity = visibility[i] ? '1' : '0.4';
        label.style.textDecoration = visibility[i] ? 'none' : 'line-through';
      });

      legendContainer.appendChild(item);
    });
  }


  // function leave_type_chart(dataSet) {
  //   var myChart4 = document.getElementById("leaveType");
  //   leaveTypeChart = new Chart(myChart4, {
  //     type: "doughnut",
  //     data: {
  //       labels: dataSet.labels,
  //       datasets: dataSet.dataset,
  //     },
  //   });
  // }

  function leave_type_chart(dataSet) {
    const ctx = document.getElementById("leaveType")?.getContext("2d");
    if (!ctx || !dataSet?.dataset?.length) return;

    const labels = dataSet.labels;
    const values = dataSet.dataset[0].data;
    const visibility = Array(labels.length).fill(true);
    const colors = [
      "#facc15", "#f87171", "#ddd6fe", "#a5b4fc", "#93c5fd", "#d1d5db"
    ];

    if (leaveTypeChart) {
      leaveTypeChart.destroy();
    }

    leaveTypeChart = new Chart(ctx, {
      type: "doughnut",
      data: {
        labels: labels,
        datasets: [
          {
            ...dataSet.dataset[0],
            backgroundColor: colors.slice(0, labels.length),
            borderWidth: 0,
            borderRadius: 10,
            hoverOffset: 8,
          },
        ],
      },
      options: {
        cutout: "70%",
        responsive: true,
        maintainAspectRatio: false,
        onClick: function (e, activeEls) {
          if (!activeEls.length) return;
          const index = activeEls[0].index;
          const label = labels[index];
          // Customize the redirection or interaction here if needed
          console.log("Clicked:", label);
        },
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: "#111827",
            bodyColor: "#f3f4f6",
            borderColor: "#e5e7eb",
            borderWidth: 1,
          },
        },
      },
      plugins: [
        {
          id: "centerText",
          afterDraw(chart) {
            const { width, height, ctx } = chart;
            ctx.save();

            const total = chart.data.datasets[0].data.reduce((sum, val) => sum + val, 0);

            ctx.font = "bold 22px sans-serif";
            ctx.fillStyle = "#374151";
            ctx.textAlign = "center";
            ctx.textBaseline = "middle";
            ctx.fillText(total, width / 2, height / 2 - 5);

            ctx.font = "15px sans-serif";
            ctx.fillStyle = "#9ca3af";
            ctx.fillText("Total", width / 2, height / 2 + 20);

            ctx.restore();
          },
        },
      ],
    });

    // 🔁 Render Custom Legend
    const legendContainer = document.getElementById("leaveTypeLegend");
    if (!legendContainer) return;
    legendContainer.innerHTML = "";

    labels.forEach((label, index) => {
      const color = colors[index % colors.length];

      const legendItem = document.createElement("div");
      legendItem.className = "flex items-center mb-2 cursor-pointer text-sm text-gray-700";
      legendItem.innerHTML = `
        <span class="inline-block w-3 h-3 mr-2 rounded-full" style="background-color: ${color};"></span>
        <span class="legend-label">${label}</span>
      `;

      legendItem.addEventListener("click", function () {
        visibility[index] = !visibility[index];

        leaveTypeChart.data.datasets[0].data = values.map((val, i) => visibility[i] ? val : 0);
        leaveTypeChart.data.datasets[0].backgroundColor = colors.map((col, i) => visibility[i] ? col : "#e5e7eb");

        const dot = legendItem.querySelector("span:first-child");
        const labelEl = legendItem.querySelector(".legend-label");

        dot.style.opacity = visibility[index] ? "1" : "0.4";
        labelEl.style.textDecoration = visibility[index] ? "none" : "line-through";

        leaveTypeChart.update();
      });

      legendContainer.appendChild(legendItem);
    });
  }


  function leave_period_chart(dataSet) {
    var myChart4 = document.getElementById("leavePeriod");
    leavePeriodChart = new Chart(myChart4, {
      type: "line",
      data: {
        labels: dataSet.labels,
        datasets: dataSet.dataset,
      },
      options: {
        scales: {
          x: {
            //   stacked: true,
            title: {
              display: true,
              text: dataSet.x_axis,
              font: {
                weight: "bold",
                size: 16,
              },
            },
          },
          y: {
            //   stacked: true,
            title: {
              display: true,
              text: dataSet.y_axis,
              font: {
                weight: "bold",
                size: 16,
              },
            },
          },
        },
      },
    });
  }

  //Chart of leave request by employees
  // function employee_leave_chart(dataSet) {
  //   employeeLeaveChart.destroy();

  //   var myChart2 = document.getElementById("employeeLeave");
  //   employeeLeaveChart = new Chart(myChart2, {
  //     type: "bar",
  //     data: {
  //       labels: dataSet.labels,
  //       datasets: dataSet.dataset,
  //     },
  //     options: {
  //       scales: {
  //         x: {
  //           stacked: true,
  //           title: {
  //             display: true,
  //             text: "Employees",
  //             font: {
  //               weight: "bold",
  //               size: 16,
  //             },
  //           },
  //         },
  //         y: {
  //           stacked: true,
  //           title: {
  //             display: true,
  //             text: "Number of days",
  //             font: {
  //               weight: "bold",
  //               size: 16,
  //             },
  //           },
  //         },
  //       },
  //     },
  //   });
  // }
  function employee_leave_chart(dataSet) {
    if (employeeLeaveChart) {
      employeeLeaveChart.destroy();
    }

    const colors = ['#a5b4fc', '#fca5a5', '#fdba74', '#86efac', '#fbbf24', '#c084fc'];
    const myChart2 = document.getElementById("employeeLeave");
    myChart2.height = 250;
    const datasets = dataSet.dataset.map((dataset, index) => ({
      ...dataset,
      backgroundColor: colors[index % colors.length],
      borderRadius: 10,
      barPercentage: 0.8,
      categoryPercentage: 0.6
    }));

    employeeLeaveChart = new Chart(myChart2, {
      type: "bar",
      data: {
        labels: dataSet.labels,
        datasets: datasets,
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: {
          duration: 300
        },
        scales: {
          x: {
            stacked: true,
            ticks: { color: '#6b7280' },
            grid: { display: false },
            title: {
              display: true,
              text: "Employees",
              font: { size: 16, weight: "bold" }
            }
          },
          y: {
            stacked: true,
            beginAtZero: true,
            ticks: {
              stepSize: 5,
              color: '#6b7280'
            },
            grid: { color: '#e5e7eb' },
            title: {
              display: true,
              text: "Number of days",
              font: { size: 16, weight: "bold" }
            }
          }
        },
        plugins: {
          legend: {
            position: 'bottom',
            labels: {
              usePointStyle: true,
              pointStyle: 'circle',
              font: { size: 12 },
              color: '#374151',
              padding: 15
            }
          },
          tooltip: {
            enabled: true
          }
        },
      },
      plugins: [{
        afterRender: (chart) => {
          const allZero = chart.data.datasets.every(ds =>
            ds.data.every(val => val === 0)
          );
          if (allZero) {
            const ctx = chart.canvas.getContext("2d");
            ctx.font = "16px Arial";
            ctx.fillStyle = "#6b7280";
            ctx.textAlign = "center";
            ctx.fillText("No data available", chart.width / 2, chart.height / 2);
          }
        }
      }]
    });
  }

  $.ajax({
    type: "GET",
    url: "/leave/employee-leave-chart",
    dataType: "json",
    success: function (response) {
      dataSet = response.dataset;
      labels = response.labels;

      $.each(dataSet, function (key, item) {
        item["data"] = item.data.slice(start_index, start_index + per_page);
      });
      var values = Object.values(labels).slice(
        start_index,
        start_index + per_page
      );
      dataset = {
        labels: values,
        dataset: dataSet,
      };
      const dataObjects = [
        {
          label: "Draft",
          data: [0, 0, 0],
          backgroundColor: "rgba(255, 99, 132, 1)",
        },
        {
          label: "Review Ongoing",
          data: [0, 0, 0],
          backgroundColor: "rgba(255, 206, 86, 1)",
        },
        {
          label: "Confirmed",
          data: [0, 0, 0],
          backgroundColor: "rgba(54, 162, 235, 1)",
        },
        {
          label: "Paid",
          data: [0, 0, 0],
          backgroundColor: "rgba(75, 242, 182, 1)",
        },
      ];

      if (isChartEmpty(dataSet)) {
        $("#employee_leave_canvas").html(
          `<div style="height: 380px; display:flex;align-items: center;justify-content: center;" class="">
					<div style="" class="">
					<img style=" display: block;width: 70px;margin: 20px auto ;" src="${
            staticUrl + "images/ui/attendance.png"
          }" class="" alt=""/>
					<h3 style="font-size:16px" class="oh-404__subtitle">${response.message}</h3>
					</div>
				</div>`
        );
      } else {
        employee_leave_chart(dataset);
      }
      start_index += per_page;
    },
    error: (error) => {
      console.log("Error", error);
    },
  });

  $.ajax({
    type: "GET",
    url: "/leave/available-leaves",
    dataType: "json",
    success: function (response) {
      if (isChartEmpty(response.dataset)) {
        $("#availableLeaveContainer").html(
          `<div style="height: 310px; display:flex;align-items: center;justify-content: center;" class="">
					<div style="" class="">
					<img style=" display: block;width: 70px;margin: 20px auto ;" src="${
            staticUrl + "images/ui/sunbed outline.png"
          }" class="" alt=""/>
					<h3 style="font-size:16px" class="oh-404__subtitle">${response.message}</h3>
					</div>
				</div>`
        );
      } else {
        available_leave_chart(response);
      }
    },
    error: (error) => {
      console.log("Error", error);
    },
  });
  $.ajax({
    type: "GET",
    url: "/leave/department-leave-chart",
    dataType: "json",
    success: function (response) {
      department_leave_chart(response);
    },
    error: (error) => {
      console.log("Error", error);
    },
  });

  $.ajax({
    type: "GET",
    url: "/leave/leave-type-chart",
    dataType: "json",
    success: function (response) {
      leave_type_chart(response);
    },
    error: (error) => {
      console.log("Error", error);
    },
  });

  $.ajax({
    type: "GET",
    url: "/leave/leave-over-period",
    dataType: "json",
    success: function (response) {
      leave_period_chart(response);
    },
    error: (error) => {
      console.log("Error", error);
    },
  });

  $(".month").on("change", function () {
    month = $(this).val();
    $(this).attr("hx-vals", `{"date":"${month}","dashboard":"true"}`);
  });
  $("#dash_month").on("change", function () {
    let month = $(this).val();
    $.ajax({
      type: "GET",
      url: "/leave/employee-leave-chart",
      dataType: "json",
      data: {
        date: month,
      },
      success: function (response) {
        if (isChartEmpty(response.dataset)) {
          $("#employee_leave_canvas").html(
            `<div style="height: 310px; display:flex;align-items: center;justify-content: center;" class="">
					<div style="" class="">
					<img style=" display: block;width: 70px;margin: 20px auto ;" src="${
            staticUrl + "images/ui/attendance.png"
          }" class="" alt=""/>
					<h3 style="font-size:16px" class="oh-404__subtitle">${response.message}</h3>
					</div>
				</div>`
          );
        } else {
          $("#employee_leave_canvas").html(
            '<canvas id="employeeLeave" class="pointer"></canvas>'
          );
          employee_leave_chart(response);
        }
      },
      error: (error) => {
        console.log("Error", error);
      },
    });
  });

  $("#employee-next").on("click", function () {
    var period = $("#monthYearField").val();
    $.ajax({
      url: "/leave/employee-leave-chart",
      type: "GET",
      dataType: "json",
      headers: {
        "X-Requested-With": "XMLHttpRequest",
      },
      data: {
        period: period,
      },
      success: (response) => {
        dataSet = response.dataset;
        labels = response.labels;

        updated_data = dataSet;
        if (start_index == 0) {
          start_index += per_page;
        }
        $.each(updated_data, function (key, item) {
          item["data"] = item.data.slice(start_index, start_index + per_page);
        });

        var values = Object.values(labels).slice(
          start_index,
          start_index + per_page
        );
        if (values.length > 0) {
          dataset = {
            labels: values,
            dataset: updated_data,
          };
          employee_leave_chart(dataset);
          start_index += per_page;
        }
      },
      error: (error) => {
        console.log("Error", error);
      },
    });
  });

  $("#employee-previous").on("click", function () {
    var period = $("#monthYearField").val();
    $.ajax({
      url: "/leave/employee-leave-chart",
      type: "GET",
      dataType: "json",
      headers: {
        "X-Requested-With": "XMLHttpRequest",
      },
      data: {
        period: period,
      },
      success: (response) => {
        dataSet = response.dataset;
        labels = response.labels;

        if (start_index <= 0) {
          return;
        }
        start_index -= per_page;
        if (start_index > 0) {
          updated_data = dataSet.map((item) => ({
            ...item,
            data: item.data.slice(start_index - per_page, start_index),
          }));
          var values = Object.values(labels).slice(
            start_index - per_page,
            start_index
          );
          dataset = {
            labels: values,
            dataset: updated_data,
          };
          employee_leave_chart(dataset);
        }
      },
      error: (error) => {
        console.log("Error", error);
      },
    });
  });

  // Taking the current year and month in the format YYYY-MM
  const currentDate = new Date();
  const currentYear = currentDate.getFullYear();
  const currentMonth = String(currentDate.getMonth() + 1).padStart(2, "0");
  const formattedDate = `${currentYear}-${currentMonth}`;
  $.ajax({
    type: "GET",
    url: "/leave/department-leave-chart",
    dataType: "json",
    data: {
      date: formattedDate,
    },
    success: function (response) {
      if (isChartEmpty(response.dataset)) {
        $("#department_leave_canvas").html(
          `<div style="height: 310px; display:flex;align-items: center;justify-content: center;" class="">
							<div style="" class="">
							<img style=" display: block;width: 70px;margin: 20px auto ;" src="${
                staticUrl + "images/ui/attendance.png"
              }" class="" alt=""/>
							<h3 style="font-size:16px" class="oh-404__subtitle">${response.message}</h3>
						</div>
					</div>`
        );
      } else {
        $("#department_leave_canvas").html(
          '<canvas id="departmentLeave" class="pointer"></canvas>'
        );
        department_leave_chart(response);
      }
    },
    error: (error) => {
      console.log("Error", error);
    },
  });

  $("#dash_department_month").on("change", function () {
    let month = $(this).val();
    $.ajax({
      type: "GET",
      url: "/leave/department-leave-chart",
      dataType: "json",
      data: {
        date: month,
      },
      success: function (response) {
        if (isChartEmpty(response.dataset)) {
          $("#department_leave_canvas").html(
            `<div style="height: 310px; display:flex;align-items: center;justify-content: center;" class="">
								<div style="" class="">
								<img style=" display: block;width: 70px;margin: 20px auto ;" src="${
                  staticUrl + "images/ui/attendance.png"
                }" class="" alt=""/>
								<h3 style="font-size:16px" class="oh-404__subtitle">${response.message}</h3>
							</div>
						</div>`
          );
        } else {
          $("#department_leave_canvas").html(
            '<canvas id="departmentLeave" class="pointer"></canvas>'
          );
          department_leave_chart(response);
        }
      },
      error: (error) => {
        console.log("Error", error);
      },
    });
  });

  $.ajax({
    type: "GET",
    url: "/leave/leave-type-chart",
    dataType: "json",
    data: {
      date: formattedDate,
    },
    success: function (response) {
      if (isChartEmpty(response.dataset)) {
        $("#leave_type_canvas").html(
          `<div style="height: 310px; display:flex;align-items: center;justify-content: center;" class="">
							<div style="" class="">
							<img style=" display: block;width: 70px;margin: 20px auto ;" src="${
                staticUrl + "images/ui/leave_types.png"
              }" class="" alt=""/>
							<h3 style="font-size:16px" class="oh-404__subtitle">${response.message}</h3>
						</div>
					</div>`
        );
      } else {
        $("#leave_type_canvas").html(
          '<canvas id="leaveType" class="pointer"></canvas>'
        );
        leave_type_chart(response);
      }
    },
    error: (error) => {
      console.log("Error", error);
    },
  });

  $("#dash_leave_type_month").on("change", function () {
    let month = $(this).val();
    $.ajax({
      type: "GET",
      url: "/leave/leave-type-chart",
      dataType: "json",
      data: {
        date: month,
      },
      success: function (response) {
        if (isChartEmpty(response.dataset)) {
          $("#leave_type_canvas").html(
            `<div style="height: 310px; display:flex;align-items: center;justify-content: center;" class="">
								<div style="" class="">
								<img style=" display: block;width: 70px;margin: 20px auto ;" src="${
                  staticUrl + "images/ui/leave_types.png"
                }" class="" alt=""/>
								<h3 style="font-size:16px" class="oh-404__subtitle">${response.message}</h3>
							</div>
						</div>`
          );
        } else {
          $("#leave_type_canvas").html(
            '<canvas id="leaveType" class="pointer"></canvas>'
          );
          leave_type_chart(response);
        }
      },
      error: (error) => {
        console.log("Error", error);
      },
    });
  });
});
