
// $(document).ready(function () {
//     function hiringChart(dataSet, labels) {
//       const data = {
//         labels: labels,
//         datasets: dataSet,
//       };
//       // Create chart using the Chart.js library
//       // $("#hiringChart").html("<canvas id='hiring'></canvas>")
//       window['myChart1'] = {}
//       var ctx = document.getElementById("hiringChart");

//       if (ctx != null) {
//         ctx = ctx.getContext("2d")
//         myChart1 = new Chart(ctx, {
//           type: 'bar',
//           data: data,
//           options: {
//           },
//         });
//       }
//     }

//     function joining(){
//       var year = $("#year").val()

//       $.ajax({
//         url: "/recruitment/dashboard-hiring",
//         type: "GET",
//         data: {
//           id : year
//         },
//         success: function (response) {
//           dataSet = response.dataSet;
//           labels = response.labels;
//           hiringChart(dataSet, labels);
//         },
//       });
//     }

//     $("#year").on("change", function (e) {
//       myChart1.destroy();
//       joining()
//     });

//     joining()

//     $('#chart2').click(function (e) {
//       var chartType = myChart1.config.type
//       if (chartType === 'line') {
//         chartType = 'bar';
//       } else if(chartType==='bar') {
//           chartType = 'line';
//       }
//       myChart1.config.type = chartType;
//       myChart1.update();
//     });

//   });

$(document).ready(function () {
  let myChart1 = null;
  let currentDataValues = [];
  let currentLabels = [];
  let visibility = [];
  const colors = [
    '#a3bffa', // January - Soft Blue
    '#f4a8a1', // February - Gentle Red
    '#f7d7b0', // March - Creamy Peach (revised)
    '#90ee90', // April - Light Green
    '#fff3a3', // May - Pale Yellow
    '#f6b6d0', // June - Delicate Pink
    '#b0a8ff', // July - Gentle Indigo (revised)
    '#87ceeb', // August - Sky Cyan
    '#d4a5fa', // September - Soft Violet
    '#7fe5b7', // October - Fresh Emerald
    '#f0c4a3', // November - Muted Coral (revised)
    '#f0b3d6'  // December - Pale Lilac (revised)
  ];
  function hiringChart(dataSet, labels) {
      // Store current data
      currentLabels = labels;
      currentDataValues = dataSet[0]?.data || [];
      visibility = new Array(labels.length).fill(true);

      const data = {
          labels: labels,
          datasets: [{
              label: 'Recruitment Count',
              data: currentDataValues,
              backgroundColor: colors.slice(0, labels.length),
              borderRadius: 20,
              barPercentage: 0.6,
              categoryPercentage: 0.6
          }]
      };

      var ctx = document.getElementById("hiringChart");
      if (ctx != null) {
          ctx = ctx.getContext("2d");
          myChart1 = new Chart(ctx, {
              type: 'bar',
              data: data,
              options: {
                  responsive: true,
                  maintainAspectRatio: false,
                  plugins: {
                      legend: { display: false },
                      tooltip: { enabled: true }
                  },
                  scales: {
                      y: {
                          beginAtZero: true,
                          max: Math.max(...currentDataValues) + 20,
                          ticks: { stepSize: 20 },
                          grid: { drawBorder: false, color: '#e5e7eb' }
                      },
                      x: {
                          ticks: { display: false },
                          grid: { display: false },
                          border: { display: true, color: '#d1d5db' }
                      }
                  }
              }
          });

          // Create clickable legend
          createClickableLegend();
      }
  }

  function createClickableLegend() {
      const legendContainer = document.getElementById('recruitmentLegend');
      if (!legendContainer) return;

      // Clear existing legend
      legendContainer.innerHTML = '';

      currentLabels.forEach((label, i) => {
          const item = document.createElement('div');
          item.className = 'flex items-center gap-2 cursor-pointer';
          item.innerHTML = `
              <span class="w-4 h-4 rounded-full inline-block" style="background:${colors[i]}; transition: 0.3s;"></span>
              <span>${label}</span>
          `;

          item.addEventListener('click', () => {
              visibility[i] = !visibility[i];

              // Update data & bar color
              myChart1.data.datasets[0].data = currentDataValues.map((val, index) => visibility[index] ? val : 0);
              myChart1.data.datasets[0].backgroundColor = colors.slice(0, currentLabels.length).map((color, index) => visibility[index] ? color : '#e5e7eb');
              myChart1.update();

              // Update legend visuals
              const dot = item.querySelector('span');
              const text = item.querySelectorAll('span')[1];
              dot.style.opacity = visibility[i] ? '1' : '0.4';
              text.style.textDecoration = visibility[i] ? 'none' : 'line-through';
          });

          legendContainer.appendChild(item);
      });
  }

  function joining() {
      var year = $("#year").val();

      $.ajax({
          url: "/recruitment/dashboard-hiring",
          type: "GET",
          data: {
              id: year
          },
          success: function (response) {
              const dataSet = response.dataSet;
              const labels = response.labels;
              hiringChart(dataSet, labels);
          },
      });
  }

  $("#year").on("change", function (e) {
      if (myChart1) {
          myChart1.destroy();
      }
      joining();
  });

  // Chart type toggle removed - keeping only bar chart

  // Initialize the chart
  joining();
});
