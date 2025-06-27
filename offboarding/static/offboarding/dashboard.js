$(document).ready(function () {
    var departmentChart;
    var joinChart;

    var department_chart = () => {
        $.ajax({
            url: "/offboarding/dashboard-department-chart",
            type: "GET",
            success: function (data) {
                var ctx = $("#departmentChart");
                if (departmentChart) {
                    departmentChart.destroy();
                }

                // Extract colors and create visibility array for dynamic datasets
                const colors = ['#a5b4fc', '#fca5a5', '#fdba74', '#34d399', '#fbbf24', '#c084fc', '#fb7185'];
                const visibility = data.datasets.map(() => true);

                // Apply the new styling to datasets
                const styledDatasets = data.datasets.map((dataset, index) => ({
                    ...dataset,
                    backgroundColor: colors[index % colors.length],
                    borderRadius: 20,
                    barPercentage: 0.6,
                    categoryPercentage: 0.6
                }));

                departmentChart = new Chart(ctx, {
                    type: "bar",
                    data: {
                        labels: data.labels,
                        datasets: styledDatasets
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: { display: false },
                            tooltip: { enabled: true }
                        },
                        scales: {
                            x: {
                                ticks: { display: true },
                                grid: { display: false },
                                border: { display: true, color: '#d1d5db' }
                            },
                            y: {
                                beginAtZero: true,
                                ticks: { stepSize: 10 },
                                grid: { drawBorder: false, color: '#e5e7eb' }
                            }
                        }
                    }
                });

                // Create clickable legend dynamically for multiple datasets
                const legendContainer = $("#departmentLegend");
                legendContainer.empty(); // Clear existing legend

                data.datasets.forEach((dataset, i) => {
                    const item = $(`
                        <div class="flex items-center gap-2 cursor-pointer legend-item" data-index="${i}">
                            <span class="w-4 h-4 rounded-full inline-block legend-dot" style="background:${colors[i % colors.length]}; transition: 0.3s;"></span>
                            <span class="legend-text">${dataset.label}</span>
                        </div>
                    `);

                    item.on('click', function () {
                        const index = parseInt($(this).data('index'));
                        visibility[index] = !visibility[index];

                        // Use Chart.js built-in visibility toggle
                        departmentChart.setDatasetVisibility(index, visibility[index]);
                        departmentChart.update();

                        // Update legend visuals
                        const dot = $(this).find('.legend-dot');
                        const text = $(this).find('.legend-text');
                        dot.css('opacity', visibility[index] ? '1' : '0.4');
                        text.css('text-decoration', visibility[index] ? 'none' : 'line-through');
                    });

                    legendContainer.append(item);
                });
            },
            error: function (xhr, status, error) {
                console.error("Error fetching department chart data:", error);
            },
        });
    };

    var join_chart = (type) => {
        $.ajax({
            url: "/offboarding/dashboard-join-chart",
            type: "GET",
            success: function (data) {
                var ctx = $("#joinChart");
                if (joinChart) {
                    joinChart.destroy();
                }

                // Colors for join chart
                const colors = ['#a5b4fc', '#fca5a5', '#fdba74', '#34d399', '#fbbf24', '#c084fc', '#fb7185'];

                // Style the dataset based on chart type
                const styledDataset = {
                    label: "Employees",
                    data: data.items,
                    backgroundColor: type === 'line' ? '#a5b4fc' : colors.slice(0, data.items.length),
                    borderColor: type === 'line' ? '#a5b4fc' : undefined,
                    borderWidth: type === 'line' ? 2 : undefined,
                    borderRadius: (type === 'bar') ? 20 : undefined,
                    barPercentage: (type === 'bar') ? 0.6 : undefined,
                    categoryPercentage: (type === 'bar') ? 0.6 : undefined,
                    fill: type === 'line' ? false : undefined,
                    tension: type === 'line' ? 0.4 : undefined
                };

                joinChart = new Chart(ctx, {
                    type: type,
                    data: {
                        labels: data.labels,
                        datasets: [styledDataset],
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            // Disable default legend for all chart types
                            legend: { display: false },
                            tooltip: { enabled: true }
                        },
                        scales: (type === 'pie' || type === 'doughnut') ? {} : {
                            x: {
                                ticks: { display: true },
                                grid: { display: false },
                                border: { display: true, color: '#d1d5db' }
                            },
                            y: {
                                beginAtZero: true,
                                ticks: { stepSize: 10 },
                                grid: { drawBorder: false, color: '#e5e7eb' }
                            }
                        }
                    }
                });

                // Create custom legend for all chart types
                const joinLegendContainer = $("#joinLegend");
                joinLegendContainer.empty(); // Clear existing legend

                data.labels.forEach((label, i) => {
                    const item = $(`
                        <div class="flex items-center gap-2 cursor-pointer legend-item" data-index="${i}">
                            <span class="w-4 h-4 rounded-full inline-block legend-dot" style="background:${colors[i % colors.length]}; transition: 0.3s;"></span>
                            <span class="legend-text">${label}</span>
                        </div>
                    `);

                    item.on('click', function () {
                        const index = parseInt($(this).data('index'));
                        const currentData = [...joinChart.data.datasets[0].data];
                        const originalValue = data.items[index];

                        // Toggle visibility by setting data to 0 or original value
                        currentData[index] = currentData[index] === 0 ? originalValue : 0;
                        joinChart.data.datasets[0].data = currentData;
                        joinChart.update();

                        // Update legend visuals
                        const dot = $(this).find('.legend-dot');
                        const text = $(this).find('.legend-text');
                        const isVisible = currentData[index] !== 0;
                        dot.css('opacity', isVisible ? '1' : '0.4');
                        text.css('text-decoration', isVisible ? 'none' : 'line-through');
                    });

                    joinLegendContainer.append(item);
                });
            },
            error: function (xhr, status, error) {
                console.error("Error fetching join chart data:", error);
            },
        });
    };

    $("#joinChartChange").click(function (e) {
        var chartType = joinChart.config.type;
        if (chartType === "line") {
            chartType = "bar";
        } else if (chartType === "bar") {
            chartType = "doughnut";
        } else if (chartType === "doughnut") {
            chartType = "pie";
        } else if (chartType === "pie") {
            chartType = "line";
        }
        join_chart(chartType);
    });

    department_chart();
    join_chart("bar");
});

// $(document).ready(function () {
//     var departmentChart;
//     var joinChart;

//     var department_chart = () => {
//         $.ajax({
//             url: "/offboarding/dashboard-department-chart",
//             type: "GET",
//             success: function (data) {
//                 var ctx = $("#departmentChart");
//                 if (departmentChart) {
//                     departmentChart.destroy();
//                 }
//                 departmentChart = new Chart(ctx, {
//                     type: "bar",
//                     data: {
//                         labels: data.labels,
//                         datasets: data.datasets,
//                     },
//                     options: {
//                         responsive: true,
//                         maintainAspectRatio: false,
//                         scales: {
//                             x: {
//                                 stacked: true,
//                             },
//                             y: {
//                                 stacked: true,
//                             },
//                         },
//                     },
//                     plugins: [
//                         {
//                             afterRender: (chart) => emptyChart(chart),
//                         },
//                     ],
//                 });
//             },
//             error: function (xhr, status, error) {
//                 console.error("Error fetching department chart data:", error);
//             },
//         });
//     };

//     var join_chart = (type) => {
//         $.ajax({
//             url: "/offboarding/dashboard-join-chart",
//             type: "GET",
//             success: function (data) {
//                 var ctx = $("#joinChart");
//                 if (joinChart) {
//                     joinChart.destroy();
//                 }
//                 joinChart = new Chart(ctx, {
//                     type: type,
//                     data: {
//                         labels: data.labels,
//                         datasets: [
//                             {
//                                 label: "Employees",
//                                 data: data.items,
//                             },
//                         ],
//                     },
//                     options: {
//                         responsive: true,
//                         maintainAspectRatio: false,
//                     },
//                     plugins: [
//                         {
//                             afterRender: (chart) => emptyChart(chart),
//                         },
//                     ],
//                 });
//             },
//             error: function (xhr, status, error) {
//                 console.error("Error fetching department chart data:", error);
//             },
//         });
//     };

//     $("#joinChartChange").click(function (e) {
//         var chartType = joinChart.config.type;
//         if (chartType === "line") {
//             chartType = "bar";
//         } else if (chartType === "bar") {
//             chartType = "doughnut";
//         } else if (chartType === "doughnut") {
//             chartType = "pie";
//         } else if (chartType === "pie") {
//             chartType = "line";
//         }
//         join_chart(chartType);
//     });

//     department_chart("pie");
//     join_chart("bar");
// });
