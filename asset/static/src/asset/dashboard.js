staticUrl = $("#statiUrl").attr("data-url");
$(document).ready(function () {
    // function available_asset_chart(dataSet) {
    //     var Asset_available_chart = document.getElementById("assetAvailableChart");
    //     if (Asset_available_chart) {
    //         var assetAvailableChartChart = new Chart(Asset_available_chart, {
    //             type: "pie",
    //             data: {
    //                 labels: dataSet.labels,
    //                 datasets: dataSet.dataset,
    //                 emptyImageSrc: dataSet.emptyImageSrc,
    //                 message: dataSet.message,
    //             },
    //             plugins: [
    //                 {
    //                     afterRender: (assetAvailableChartChart) => emptyAssetAvialabeChart(assetAvailableChartChart),
    //                 },
    //             ],
    //         });
    //     }
    // }

    function available_asset_chart(dataSet) {
        var Asset_available_chart = document.getElementById("assetAvailableChart");
        if (Asset_available_chart) {
            const ctx = Asset_available_chart.getContext('2d');

            // Load center icon image
            const centerImage = new Image();
            centerImage.src = "/static/horilla_theme/assets/img/icons/asset-chart.svg"; // Adjust path as needed

            var assetAvailableChartChart = new Chart(ctx, {
                type: "doughnut", // Changed from pie to doughnut
                data: {
                    labels: dataSet.labels,
                    datasets: [{
                        data: dataSet.dataset[0].data, // Assuming your dataset structure
                        backgroundColor: dataSet.dataset[0].backgroundColor || ['#cfe9ff', '#ffc9de', '#e6ccff', '#ffeb99', '#d4edda'], // Default colors
                        borderWidth: 0
                    }],
                    emptyImageSrc: dataSet.emptyImageSrc,
                    message: dataSet.message,
                },
                options: {
                    cutout: '70%', // Creates the doughnut hole
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: {
                                usePointStyle: true,
                                pointStyle: 'circle',
                                padding: 20,
                                font: {
                                    size: 12
                                },
                                color: '#000'
                            }
                        }
                    }
                },
                plugins: [
                    {
                        id: 'centerIcon',
                        afterDraw(chart) {
                            if (!centerImage.complete) return; // Wait till image is loaded
                            const ctx = chart.ctx;
                            const size = 70;
                            const centerX = chart.getDatasetMeta(0).data[0].x; // Center X of the doughnut
                            const centerY = chart.getDatasetMeta(0).data[0].y; // Center Y of the doughnut
                            ctx.drawImage(
                                centerImage,
                                centerX - size / 2,
                                centerY - size / 2,
                                size,
                                size
                            );
                        }
                    },
                    {
                        afterRender: (assetAvailableChartChart) => emptyAssetAvialabeChart(assetAvailableChartChart),
                    }
                ]
            });
        }
    }

    // function asset_category_chart(dataSet) {
    //     var Asset_category_chart = document.getElementById("assetCategoryChart");
    //     if (Asset_category_chart) {
    //         var assetCategoryChart = new Chart(Asset_category_chart, {
    //             type: "bar",
    //             data: {
    //                 labels: dataSet.labels,
    //                 datasets: dataSet.dataset,
    //                 emptyImageSrc: dataSet.emptyImageSrc,
    //                 message: dataSet.message,
    //             },
    //             plugins: [
    //                 {
    //                     afterRender: (assetCategoryChart) => emptyAssetAvialabeChart(assetCategoryChart),
    //                 },
    //             ],
    //         });
    //     }
    // }
    function asset_category_chart(dataSet) {
        const ctx = document.getElementById('assetCategoryChart');
        if (!ctx) return;

        const chartCtx = ctx.getContext('2d');
        const labels = dataSet.labels || [];

        // Extract data from your existing dataset structure
        const datasets = dataSet.dataset || [];
        const values = datasets.length > 0 ? datasets[0].data || [] : [];

        // Different pastel colors for each item
        const colors = [
          '#a5b4fc',
          '#fca5a5',
          '#fcd34d',
          '#c084fc',
          '#7dd3fc',
          '#bef264',
          '#fdba74'
        ];

        const visibility = new Array(labels.length).fill(true);

        const chart = new Chart(chartCtx, {
          type: 'bar',
          data: {
            labels: labels,
            datasets: [{
              label: datasets.length > 0 ? datasets[0].label || 'Asset Count' : 'Asset Count',
              data: values,
              backgroundColor: colors,
              borderRadius: 20,
              barPercentage: 0.6,
              categoryPercentage: 0.6
            }]
          },
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
                max: Math.max(...values) + 20 || 100,
                ticks: {
                  stepSize: 5,
                  color: '#6b7280',
                  font: { size: 12 }
                },
                grid: {
                  drawBorder: false,
                  color: '#e5e7eb',
                  display: true // Show Y-axis grid lines
                }
              },
              x: {
                ticks: { display: false },
                grid: { display: false },
                border: { display: true, color: '#d1d5db' }
              }
            }
          }
        });

        // Create legend dynamically
        const legendContainer = document.getElementById('assetCategoryLegend');
        if (legendContainer) {
          // Clear existing legend
          legendContainer.innerHTML = '';

          // Create legend items flowing naturally like "Joinings Per Month"
          const legendWrapper = document.createElement('div');
          legendWrapper.className = 'mt-4 flex justify-center flex-wrap gap-3 text-xs';

          labels.forEach((label, index) => {
            const legendItem = document.createElement('div');
            legendItem.className = 'flex items-center gap-2 cursor-pointer';

            const colorDot = document.createElement('span');

            colorDot.style.cssText = `
            background:${colors[index]}; transition: 0.3s;`;
            colorDot.className ='w-4 h-4 rounded-full inline-block';

            const labelText = document.createElement('span');
            labelText.textContent = label;
            labelText.style.cssText = 'font-size: 14px; color: #374151; font-weight: 400; transition: text-decoration 0.3s; white-space: nowrap;';

            legendItem.appendChild(colorDot);
            legendItem.appendChild(labelText);
            legendWrapper.appendChild(legendItem);

            // Add click event listener
            legendItem.addEventListener('click', () => {
              visibility[index] = !visibility[index];

              // Update chart data
              chart.data.datasets[0].data = values.map((val, i) => visibility[i] ? val : 0);
              chart.data.datasets[0].backgroundColor = colors.map((col, i) => visibility[i] ? col : '#e5e7eb');
              chart.update();

              // Update legend visuals
              colorDot.style.opacity = visibility[index] ? '1' : '0.4';
              labelText.style.textDecoration = visibility[index] ? 'none' : 'line-through';
            });
          });

          // Append the wrapper to the container
          legendContainer.appendChild(legendWrapper);
        }
      }

    $.ajax({
        type: "GET",
        url: "/asset/asset-available-chart",
        dataType: "json",
        success: function (response) {
            available_asset_chart(response);
        },
        error: (error) => {
            console.log("Error", error);
        },
    });

    $.ajax({
        type: "GET",
        url: "/asset/asset-category-chart",
        dataType: "json",
        success: function (response) {
            asset_category_chart(response);
        },
        error: (error) => {
            console.log("Error", error);
        },
    });
});

function emptyAssetAvialabeChart(assetAvailableChartChart, args, options) {
    flag = false;
    for (let i = 0; i < assetAvailableChartChart.data.datasets.length; i++) {
        flag = flag + assetAvailableChartChart.data.datasets[i].data.some(Boolean);
    }
    if (!flag) {
        const { ctx, canvas } = assetAvailableChartChart;
        assetAvailableChartChart.clear();
        const parent = canvas.parentElement;

        // Set canvas width/height to match
        canvas.width = parent.clientWidth;
        canvas.height = parent.clientHeight;
        // Calculate center position
        const x = canvas.width / 2;
        const y = (canvas.height - 70) / 2;
        var noDataImage = new Image();
        noDataImage.src = assetAvailableChartChart.data.emptyImageSrc
            ? assetAvailableChartChart.data.emptyImageSrc
            : staticUrl + "images/ui/no_records.svg";

        message = assetAvailableChartChart.data.message
            ? assetAvailableChartChart.data.message
            : emptyMessages[languageCode];

        noDataImage.onload = () => {
            // Draw image first at center
            ctx.drawImage(noDataImage, x - 35, y, 70, 70);

            // Draw text below image
            ctx.textAlign = "center";
            ctx.textBaseline = "middle";
            ctx.fillStyle = "hsl(0,0%,45%)";
            ctx.font = "16px Poppins";
            ctx.fillText(message, x, y + 70 + 30);
        };
    }
}
