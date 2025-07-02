// Get static URL from element
staticUrl = $("#statiUrl").attr("data-url");

$(document).ready(function () {
  // Global variables to store chart instances
  window.attendanceChart = null;
  window.departmentOvertimeChart = null;
  window.pendingHoursChart = null;

  // Initialize department overtime chart data
  var departmentChartData = {
    labels: [],
    datasets: [],
    message: null,
    emptyImageSrc: null
  };

  // Track visibility state for custom legend
  var departmentVisibility = [];

  // Get current date information
  var today = new Date();
  var month = ("0" + (today.getMonth() + 1)).slice(-2);
  var year = today.getFullYear();
  var day = ("0" + today.getDate()).slice(-2);
  var formattedDate = year + "-" + month + "-" + day;
  var currentWeek = getWeekNumber(today);

  // Set initial date values for both attendance and department charts
  $("#attendance_month").val(formattedDate);
  if ($("#department_month").length) {
    $("#department_month").val(formattedDate).prop("type", "date");
  }
  if ($("#department_date_type").length) {
    $("#department_date_type").val("day");
  }

  // Initialize Department Overtime Chart with custom legend approach
  const departmentOvertimeChartCanvas = document.getElementById("departmentOverChart");
  if (departmentOvertimeChartCanvas) {
    window.departmentOvertimeChart = new Chart(departmentOvertimeChartCanvas, {
      type: "doughnut",
      data: departmentChartData,
      options: {
        cutout: '70%',
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false }, // Disable built-in legend
          tooltip: {
            backgroundColor: '#111827',
            bodyColor: '#f3f4f6',
            borderColor: '#e5e7eb',
            borderWidth: 1
          }
        }
      },

      plugins: [
        {
          id: 'centerText',
          afterDraw(chart) {
            const { width, height, ctx } = chart;
            ctx.save();

            // Calculate total from visible data
            let total = 0;
            if (chart.data.datasets[0] && chart.data.datasets[0].data) {
              chart.data.datasets[0].data.forEach((value, index) => {
                if (departmentVisibility[index] !== false) {
                  total += value || 0;
                }
              });
            }

            ctx.font = 'bold 22px sans-serif';
            ctx.fillStyle = '#374151';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillText(total, width / 2, height / 2 - 5);
            ctx.font = '15px sans-serif';
            ctx.fillStyle = '#9ca3af';
            ctx.fillText('Total', width / 2, height / 2 + 20);
            ctx.restore();
          }
        },
        {
          afterRender: (chart) => emptyOvertimeChart(chart),
        },
      ],
    });
  }

  // Function to create custom legend
  function createCustomLegend(labels, colors) {
    const legendContainer = document.getElementById('chartLegend');
    if (!legendContainer) return;

    legendContainer.innerHTML = '';
    departmentVisibility = Array(labels.length).fill(true);

    labels.forEach((label, index) => {
      const legendItem = document.createElement('div');
      legendItem.className = 'flex items-center gap-2 cursor-pointer select-none';
      legendItem.innerHTML = `
        <span class="w-3 h-3 rounded-full inline-block legend-dot" style="background-color: ${colors[index]}"></span>
        <span class="legend-label text-sm text-gray-700">${label}</span>
      `;

      // Add click event listener
      legendItem.addEventListener('click', () => {
        toggleLegendItem(index, legendItem);
      });

      legendContainer.appendChild(legendItem);
    });
  }

  // Function to toggle legend item visibility
  function toggleLegendItem(index, legendElement) {
    if (!window.departmentOvertimeChart) return;

    departmentVisibility[index] = !departmentVisibility[index];

    // Update visual appearance of legend item
    const dot = legendElement.querySelector('.legend-dot');
    const label = legendElement.querySelector('.legend-label');

    if (departmentVisibility[index]) {
      dot.style.opacity = '1';
      label.style.textDecoration = 'none';
      label.style.opacity = '1';
    } else {
      dot.style.opacity = '0.4';
      label.style.textDecoration = 'line-through';
      label.style.opacity = '0.6';
    }

    // Update chart data
    updateChartVisibility();
  }

  // Function to update chart based on visibility state
  function updateChartVisibility() {
    if (!window.departmentOvertimeChart || !window.departmentOvertimeChart.data.datasets[0]) return;

    const originalData = window.departmentOvertimeChart.data.datasets[0].originalData ||
                         window.departmentOvertimeChart.data.datasets[0].data.slice();

    // Store original data if not already stored
    if (!window.departmentOvertimeChart.data.datasets[0].originalData) {
      window.departmentOvertimeChart.data.datasets[0].originalData = originalData;
    }

    // Update data based on visibility
    window.departmentOvertimeChart.data.datasets[0].data = originalData.map((value, index) =>
      departmentVisibility[index] ? value : 0
    );

    window.departmentOvertimeChart.update('none'); // No animation for better performance
  }

  // Initialize Attendance Analytics Chart
  $.ajax({
    url: "/attendance/dashboard-attendance",
    type: "GET",
    success: function (response) {
      createAttendanceChart(response.dataSet, response.labels);
    },
    error: function(xhr, status, error) {
      console.error('Error loading attendance data:', error);
    }
  });

  // Initialize Department Overtime Chart Data
  if ($("#department_date_type").length && $("#department_month").length) {
    $.ajax({
      url: "/attendance/department-overtime-chart",
      type: "GET",
      dataType: "json",
      headers: {
        "X-Requested-With": "XMLHttpRequest",
      },
      data: {
        date: formattedDate,
        type: "day"
      },
      success: (response) => {
        departmentDataUpdate(response);
      },
      error: (error) => {
        console.log("Error loading department overtime data:", error);
      },
    });
  }

  // Department Overtime Chart Functions
  function departmentDataUpdate(response) {
    if (window.departmentOvertimeChart) {
      // Ensure response properties are handled safely
      departmentChartData.labels = response.labels || [];
      departmentChartData.message = response.message || "No data available";
      departmentChartData.emptyImageSrc = response.emptyImageSrc || staticUrl + "images/ui/no_records.svg";

      // Transform dataset for doughnut chart
      if (response.dataset && response.dataset.length > 0 && response.dataset[0].data && response.dataset[0].data.length > 0) {
        const colors = [
          '#facc15',
          '#f87171',
          '#ddd6fe',
          '#a5b4fc',
          '#93c5fd',
          '#d1d5db',
          '#fbbf24',
          '#c084fc',
          '#86efac',
          '#fdba74'
        ];

        departmentChartData.datasets = [{
          data: response.dataset[0].data,
          originalData: response.dataset[0].data.slice(), // Store original data
          backgroundColor: colors.slice(0, response.dataset[0].data.length),
          borderWidth: 0,
          borderRadius: 10,
          hoverOffset: 8
        }];

        // Create custom legend
        createCustomLegend(
          departmentChartData.labels,
          colors.slice(0, response.dataset[0].data.length)
        );
      } else {
        departmentChartData.datasets = [{
          data: [],
          originalData: [],
          backgroundColor: [],
          borderWidth: 0,
          borderRadius: 10,
          hoverOffset: 8
        }];

        // Clear legend
        const legendContainer = document.getElementById('chartLegend');
        if (legendContainer) {
          legendContainer.innerHTML = '';
        }
      }

      window.departmentOvertimeChart.data = departmentChartData;
      window.departmentOvertimeChart.update();
    }
  }

  function changeDepartmentMonth() {
    let type = $("#department_date_type").val();
    let date = $("#department_month").val();
    let end_date = $("#department_month2").val();

    $.ajax({
      type: "GET",
      url: "/attendance/department-overtime-chart",
      dataType: "json",
      data: {
        date: date,
        type: type,
        end_date: end_date,
      },
      success: function (response) {
        departmentDataUpdate(response);
      },
      error: (error) => {
        console.error('Error updating department chart:', error);
      },
    });
  }

  function changeDepartmentView(element) {
    var dataType = $(element).val();

    // Remove existing end date input
    $("#department_month2").remove();

    if (dataType === "date_range") {
      $("#department_month").prop("type", "date");
      $("#department_month").after(
        '<input type="date" class="mb-2 float-end pointer oh-select ml-2" id="department_month2" style="width: 100px;color:#5e5c5c;"/>'
      );
      $("#department_month").val(formattedDate);
      $("#department_month2").val(formattedDate);
    } else if (dataType === "weekly") {
      $("#department_month").prop("type", "week");
      if (currentWeek < 10) {
        $("#department_month").val(`${year}-W0${currentWeek}`);
      } else {
        $("#department_month").val(`${year}-W${currentWeek}`);
      }
    } else if (dataType === "day") {
      $("#department_month").prop("type", "date");
      $("#department_month").val(formattedDate);
    } else {
      $("#department_month").prop("type", "month");
      $("#department_month").val(`${year}-${month}`);
    }

    changeDepartmentMonth();
  }

  function emptyOvertimeChart(chart) {
    let flag = false;
    for (let i = 0; i < chart.data.datasets.length; i++) {
      flag = flag || chart.data.datasets[i].data.some(Boolean);
    }

    if (!flag) {
      const { ctx, canvas } = chart;
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      const parent = canvas.parentElement;
      canvas.width = parent.clientWidth;
      canvas.height = parent.clientHeight;

      const x = canvas.width / 2;
      const y = (canvas.height - 70) / 2;

      var noDataImage = new Image();
      noDataImage.src = chart.data.emptyImageSrc || staticUrl + "images/ui/no_records.svg";

      var message = chart.data.message || "No data available";

      noDataImage.onload = () => {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.drawImage(noDataImage, x - 35, y, 70, 70);
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillStyle = "hsl(0,0%,45%)";
        ctx.font = "16px Poppins";
        ctx.fillText(message, x, y + 70 + 30);
      };

      noDataImage.onerror = () => {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillStyle = "hsl(0,0%,45%)";
        ctx.font = "16px Poppins";
        ctx.fillText(message, x, y + 70 + 30);
      };
    }
  }

  // Event handlers for department overtime chart
  $(document).on("change", "#department_date_type", function (e) {
    changeDepartmentView($(this));
  });

  $(document).on("change", "#department_month", function (e) {
    changeDepartmentMonth();
  });

  $(document).on("change", "#department_month2", function (e) {
    changeDepartmentMonth();
  });

  // Make functions globally available
  window.changeDepartmentView = changeDepartmentView;
  window.changeDepartmentMonth = changeDepartmentMonth;
  window.toggleLegendItem = toggleLegendItem;
});

// Rest of the code remains the same...
// [Include all the other functions like generateUniqueColors, emptyChart, createAttendanceChart, etc.]

// Attendance Analytics Chart Functions
function generateUniqueColors(count) {
  const colors = [];
  const hueStep = 360 / count;
  for (let i = 0; i < count; i++) {
    const hue = i * hueStep;
    const hslToHex = (h, s, l) => {
      l /= 100;
      const a = s * Math.min(l, 1 - l) / 100;
      const f = n => {
        const k = (n + h / 30) % 12;
        const color = l - a * Math.max(Math.min(k - 3, 9 - k, 1), -1);
        return Math.round(255 * color).toString(16).padStart(2, '0');
      };
      return `#${f(0)}${f(8)}${f(4)}`;
    };
    colors.push(hslToHex(hue, 40, 85));
  }
  return colors;
}

function emptyChart(chart) {
  if (chart.data.datasets.every(dataset => dataset.data.every(value => value === 0))) {
    chart.data.datasets = [{
      label: 'No Data',
      data: chart.data.labels.map(() => 0),
      backgroundColor: '#e5e7eb'
    }];
  }
}

function createAttendanceChart(dataSet, labels) {
  const colors = generateUniqueColors(dataSet.length);

  const modifiedDataSet = dataSet.map((dataset, index) => ({
    ...dataset,
    backgroundColor: colors[index],
    borderRadius: 10,
    barPercentage: 0.8,
    categoryPercentage: 0.6
  }));

  const attendanceChartCanvas = document.getElementById("dailyAnalytic");
  if (attendanceChartCanvas) {
    const ctx = attendanceChartCanvas.getContext("2d");

    if (window.attendanceChart) {
      window.attendanceChart.destroy();
    }

    window.attendanceChart = new Chart(ctx, {
      type: "bar",
      data: {
        labels: labels,
        datasets: modifiedDataSet,
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          y: {
            beginAtZero: true,
            ticks: {
              stepSize: 5,
              color: '#6b7280'
            },
            grid: {
              color: '#e5e7eb'
            }
          },
          x: {
            ticks: {
              color: '#6b7280'
            },
            grid: {
              display: false
            }
          }
        },
        plugins: {
          legend: {
            position: 'bottom',
            labels: {
              usePointStyle: true,
              pointStyle: 'circle',
              font: {
                size: 12
              },
              color: '#374151',
              padding: 15
            }
          },
          tooltip: {
            enabled: true
          }
        },
        onClick: (e, activeEls) => {
          if (activeEls.length > 0) {
            let datasetLabel = e.chart.data.datasets[activeEls[0].datasetIndex].label;
            let value = e.chart.data.datasets[activeEls[0].datasetIndex].data[activeEls[0].index];
            let label = e.chart.data.labels[activeEls[0].index];
            let parms = "?department=" + datasetLabel + "&type=" + label.toLowerCase().replace(/\s/g, "_");
            let type = $("#type").val();
            const dateStr = $("#attendance_month").val();

            if (type === "weekly") {
              const [year, week] = dateStr.split("-W");
              parms += `&week=${week}&year=${year}`;
            } else if (type === "monthly") {
              const [year, month] = dateStr.split("-");
              parms += `&month=${month}&year=${year}`;
            } else if (type === "day") {
              parms += `&attendance_date=${dateStr}`;
            } else if (type === "date_range") {
              const start_date = dateStr;
              const end_date = $("#attendance_month2").val();
              parms += `&attendance_date__gte=${start_date}&attendance_date__lte=${end_date}`;
            }

            if (typeof(Storage) !== "undefined") {
              localStorage.removeItem("savedFilters");
            }

            if (label === "On Time") {
              $.ajax({
                url: "/attendance/on-time-view" + parms,
                type: "GET",
                data: { input_type: type },
                headers: { "X-Requested-With": "XMLHttpRequest" },
                success: (response) => {
                  $("#back_button").removeClass("d-none");
                  $("#dashboard").html(response);
                },
                error: (error) => console.error('Ajax error:', error),
              });
            } else {
              window.location.href = "/attendance/late-come-early-out-view" + parms;
            }
          }
        },
      },
      plugins: [{
        afterRender: (chart) => emptyChart(chart),
      }],
    });
  }
}

function getWeekNumber(date) {
  const clonedDate = new Date(date);
  clonedDate.setHours(0, 0, 0, 0);
  clonedDate.setDate(clonedDate.getDate() + 4 - (clonedDate.getDay() || 7));
  const yearStart = new Date(clonedDate.getFullYear(), 0, 1);
  return Math.ceil(((clonedDate - yearStart) / 86400000 + 1) / 7);
}

function changeMonth() {
  let type = $("#type").val();
  let date = $("#attendance_month").val();
  let end_date = $("#attendance_month2").val();

  $.ajax({
    type: "GET",
    url: "/attendance/dashboard-attendance",
    dataType: "json",
    data: {
      date: date,
      type: type,
      end_date: type === "date_range" ? end_date : undefined,
    },
    success: function (response) {
      if (window.attendanceChart) {
        window.attendanceChart.destroy();
      }
      createAttendanceChart(response.dataSet, response.labels);
    },
    error: (error) => console.error('Ajax error:', error),
  });
}

function changeView(element) {
  const dataType = $(element).val();
  const today = new Date();
  const month = ("0" + (today.getMonth() + 1)).slice(-2);
  const year = today.getFullYear();
  const day = ("0" + today.getDate()).slice(-2);
  const formattedDate = `${year}-${month}-${day}`;
  const currentWeek = getWeekNumber(today);

  $("#attendance_month2").remove();

  if (dataType === "date_range") {
    $("#attendance_month").prop("type", "date");
    $("#attendance_month").after(
      '<input type="date" class="mb-2 float-end pointer oh-select ml-2" id="attendance_month2" style="width: 100px;color:#5e5c5c;" onchange="changeMonth()"/>'
    );
    $("#attendance_month").val(formattedDate);
    $("#attendance_month2").val(formattedDate);
  } else if (dataType === "weekly") {
    $("#attendance_month").prop("type", "week");
    $("#attendance_month").val(`${year}-W${currentWeek.toString().padStart(2, '0')}`);
  } else if (dataType === "day") {
    $("#attendance_month").prop("type", "date");
    $("#attendance_month").val(formattedDate);
  } else if (dataType === "monthly") {
    $("#attendance_month").prop("type", "month");
    $("#attendance_month").val(`${year}-${month}`);
  }

  changeMonth();
}

// Pending Hours Chart Functions
document.addEventListener('DOMContentLoaded', () => {
  let isLoading = false;

  const monthNames = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
  ];

  const colors = ['#a5b4fc', '#fca5a5', '#fdba74', '#86efac', '#fbbf24', '#c084fc'];

  const currentDate = new Date();
  const currentMonthNumber = currentDate.getMonth();
  const currentMonth = monthNames[currentMonthNumber];
  const currentYear = currentDate.getFullYear();
  const currentYearMonth = currentDate.toISOString().slice(0, 7);

  const monthSelector = document.getElementById("hourAccountMonth");
  if (monthSelector) {
    monthSelector.value = currentYearMonth;
  }

  function pendingHourChart(year, month) {
    if (isLoading) return;

    const ctx = document.getElementById("pendingHoursCanvas");
    if (!ctx) return;

    isLoading = true;

    $.ajax({
      type: "GET",
      url: "/attendance/pending-hours",
      data: { month, year },
      cache: true,
      success: function (response) {
        if (window.pendingHoursChart) {
          window.pendingHoursChart.destroy();
          window.pendingHoursChart = null;
        }

        const datasets = response.data.datasets.map((dataset, index) => ({
          ...dataset,
          backgroundColor: colors[index % colors.length],
          borderRadius: 10,
          barPercentage: 0.8,
          categoryPercentage: 0.6
        }));

        window.pendingHoursChart = new Chart(ctx, {
          type: "bar",
          data: {
            ...response.data,
            datasets
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: {
              duration: 300
            },
            scales: {
              x: {
                ticks: { color: '#6b7280' },
                grid: { display: false }
              },
              y: {
                beginAtZero: true,
                ticks: {
                  stepSize: 20,
                  color: '#6b7280'
                },
                grid: { color: '#e5e7eb' }
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
                animation: {
                  duration: 0
                }
              }
            },
            onClick: (e, activeEls) => {
              if (activeEls?.length) {
                const { datasetIndex, index: dataIndex } = activeEls[0];
                const datasetLabel = e.chart.data.datasets[datasetIndex].label;
                const label = e.chart.data.labels[dataIndex];

                const params = new URLSearchParams({
                  year,
                  month,
                  department_name: label,
                  [datasetLabel.toLowerCase() === "worked hours" ? "worked_hours__gte" : "pending_hours__gte"]: "1"
                });

                window.location.href = `/attendance/attendance-overtime-view?${params}`;
              }
            }
          },
          plugins: [{
            afterRender: () => emptyChart(window.pendingHoursChart)
          }]
        });

        isLoading = false;
      },
      error: () => {
        isLoading = false;
      }
    });
  }

  function dynamicMonth(element) {
    const value = element.val();
    if (!value || isLoading) return;

    const [year, monthStr] = value.split("-");
    const monthIndex = parseInt(monthStr) - 1;

    if (monthIndex >= 0 && monthIndex < 12) {
      pendingHourChart(parseInt(year), monthNames[monthIndex]);
    }
  }

  window.dynamicMonth = dynamicMonth;

  if (document.getElementById("pendingHoursCanvas")) {
    pendingHourChart(currentYear, currentMonth);
  }
});
