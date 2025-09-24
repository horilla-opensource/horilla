$(document).ready(function () {
    // function employeeChart(dataSet, labels) {
    //     const data = {
    //         labels: labels,
    //         datasets: dataSet,
    //     };
    //     // Create chart using the Chart.js library
    //     window["myChart"] = {};
    //     if (document.getElementById("totalEmployees")) {
    //         const ctx = document.getElementById("totalEmployees").getContext("2d");
    //         employeeChart = new Chart(ctx, {
    //             type: "doughnut",
    //             data: data,
    //             options: {
    //                 responsive: true,
    //                 maintainAspectRatio: false,
    //                 onClick: (e, activeEls) => {
    //                     let datasetIndex = activeEls[0].datasetIndex;
    //                     let dataIndex = activeEls[0].index;
    //                     let datasetLabel = e.chart.data.datasets[datasetIndex].label;
    //                     let value = e.chart.data.datasets[datasetIndex].data[dataIndex];
    //                     let label = e.chart.data.labels[dataIndex];
    //                     var active = "False";
    //                     if (label.toLowerCase() == "active") {
    //                         active = "True";
    //                     }
    //                     localStorage.removeItem("savedFilters");
    //                     window.location.href = "/employee/employee-view?is_active=" + active;
    //                 },
    //             },
    //             plugins: [
    //                 {
    //                     afterRender: (chart) => emptyChart(chart),
    //                 },
    //             ],
    //         });
    //     }
    // }

    // function genderChart(dataSet, labels) {
    //     const data = {
    //         labels: labels,
    //         datasets: dataSet,
    //     };
    //     console.log(data)
    //     // Create chart using the Chart.js library
    //     window["genderChart"] = {};
    //     if (document.getElementById("genderChart")) {
    //         const ctx = document.getElementById("genderChart").getContext("2d");
    //         genderChart = new Chart(ctx, {
    //             type: "doughnut",
    //             data: data,
    //             options: {
    //                 responsive: true,
    //                 maintainAspectRatio: false,
    //                 onClick: (e, activeEls) => {
    //                     let datasetIndex = activeEls[0].datasetIndex;
    //                     let dataIndex = activeEls[0].index;
    //                     let datasetLabel = e.chart.data.datasets[datasetIndex].label;
    //                     let value = e.chart.data.datasets[datasetIndex].data[dataIndex];
    //                     let label = e.chart.data.labels[dataIndex];
    //                     localStorage.removeItem("savedFilters");
    //                     window.location.href =
    //                         "/employee/employee-view?gender=" + label.toLowerCase();
    //                 },
    //             },
    //             plugins: [
    //                 {
    //                     afterRender: (chart) => emptyChart(chart),
    //                 },
    //             ],
    //         });
    //     }
    // }

    // function departmentChart(dataSet, labels) {
    //     console.log(dataSet);
    //     console.log(labels);
    //     const data = {
    //         labels: labels,
    //         datasets: dataSet,
    //     };
    //     // Create chart using the Chart.js library
    //     window["departmentChart"] = {};
    //     if (document.getElementById("departmentChart")) {
    //         const ctx = document.getElementById("departmentChart").getContext("2d");
    //         departmentChart = new Chart(ctx, {
    //             type: "doughnut",
    //             data: data,
    //             options: {
    //                 responsive: true,
    //                 maintainAspectRatio: false,
    //                 onClick: (e, activeEls) => {
    //                     let datasetIndex = activeEls[0].datasetIndex;
    //                     let dataIndex = activeEls[0].index;
    //                     let datasetLabel = e.chart.data.datasets[datasetIndex].label;
    //                     let value = e.chart.data.datasets[datasetIndex].data[dataIndex];
    //                     let label = e.chart.data.labels[dataIndex];
    //                     localStorage.removeItem("savedFilters");
    //                     window.location.href =
    //                         "/employee/employee-view?department=" + label;

    //                 },
    //             },
    //             plugins: [
    //                 {
    //                     afterRender: (chart) => emptyChart(chart),
    //                 },
    //             ],
    //         });
    //     }
    // }

    function employeeChart(dataSet, labels) {
        $(document).ready(function () {
            const ctx = document.getElementById("totalEmployees")?.getContext("2d");
            if (!ctx) return;

            const values = dataSet[0].data;
            const colors = [
                "#34d399", // Active - green
                "#f87171", // Inactive - red
            ];
            const visibility = Array(labels.length).fill(true);

            // Create chart instance
            const employeeChartInstance = new Chart(ctx, {
                type: "doughnut",
                data: {
                    labels: labels,
                    datasets: [
                        {
                            ...dataSet[0],
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

                        const dataIndex = activeEls[0].index;
                        const label = labels[dataIndex];
                        let active = label.toLowerCase() === "active" ? "True" : "False";

                        localStorage.removeItem("savedFilters");
                        window.location.href = "/employee/employee-view?is_active=" + active;
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

                            const total = chart.data.datasets[0].data.reduce(
                                (sum, val) => sum + val,
                                0
                            );

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
                    {
                        afterRender: (chart) => {
                            if (typeof emptyChart === "function") {
                                emptyChart(chart);
                            }
                        },
                    },
                ],
            });

            // 🧩 Custom Legend Generation
            const $legendContainer = $("#employeeChartLegend"); // Make sure to have this element in DOM
            $legendContainer.empty();

            labels.forEach((label, index) => {
                const color = colors[index % colors.length];

                const $item = $(`
                    <div style="display: flex; align-items: center; margin-bottom: 6px; cursor: pointer;">
                        <span style="display: inline-block; width: 12px; height: 12px; border-radius: 50%; background-color: ${color}; margin-right: 8px;"></span>
                        <span class="legend-label">${label}</span>
                    </div>
                `);

                $legendContainer.append($item);

                $item.on("click", function () {
                    visibility[index] = !visibility[index];

                    employeeChartInstance.data.datasets[0].data = values.map((val, i) =>
                        visibility[i] ? val : 0
                    );

                    const $dot = $(this).find("span").first();
                    const $label = $(this).find(".legend-label");

                    if (visibility[index]) {
                        $dot.css("opacity", "1");
                        $label.css("text-decoration", "none");
                    } else {
                        $dot.css("opacity", "0.4");
                        $label.css("text-decoration", "line-through");
                    }

                    employeeChartInstance.update();
                });
            });
        });
    }

    function genderChart(dataSet, labels) {
        const centerImage = new Image();
        centerImage.src = "/static/horilla_theme/assets/img/icons/gender.svg";

        if (document.getElementById("genderChart")) {
            const ctx = document.getElementById("genderChart").getContext("2d");

            // Override dataset background colors with new design colors
            const updatedDataSet = dataSet.map((ds) => ({
                ...ds,
                backgroundColor: ["#cfe9ff", "#ffc9de", "#e6ccff"],
                borderWidth: 0,
            }));

            window["genderChart"] = new Chart(ctx, {
                type: "doughnut",
                data: {
                    labels: labels,
                    datasets: updatedDataSet,
                },
                options: {
                    cutout: "70%",
                    responsive: true,
                    maintainAspectRatio: false,
                    onClick: (e, activeEls) => {
                        if (activeEls.length > 0) {
                            let datasetIndex = activeEls[0].datasetIndex;
                            let dataIndex = activeEls[0].index;
                            let label = e.chart.data.labels[dataIndex];
                            localStorage.removeItem("savedFilters");
                            window.location.href = "/employee/employee-view?gender=" + label.toLowerCase();
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
                                    return context.parsed; // This shows only "13", not "Employees: 13"
                                },
                            },
                        },
                    },
                },
                plugins: [
                    {
                        id: "centerIcon",
                        afterDatasetsDraw(chart) {
                            if (!centerImage.complete) return;
                            const ctx = chart.ctx;
                            const size = 70;
                            ctx.drawImage(
                                centerImage,
                                chart.width / 2 - size / 2,
                                chart.height / 2 - size / 2 - 20,
                                size,
                                size
                            );
                        },
                    },
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
    }

    function departmentChart(dataSet, labels) {
        $(document).ready(function () {
            const ctx = $("#departmentChart")[0]?.getContext("2d");
            if (!ctx) return;

            const values = dataSet[0].data;
            const colors = [
                "#facc15",
                "#f87171",
                "#ddd6fe",
                "#a5b4fc",
                "#93c5fd",
                "#d1d5db",
            ];
            const visibility = Array(labels.length).fill(true);

            // Create the chart instance
            const departmentChartInstance = new Chart(ctx, {
                type: "doughnut",
                data: {
                    labels: labels,
                    datasets: [
                        {
                            ...dataSet[0],
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
                        const dataIndex = activeEls[0].index;
                        const label = labels[dataIndex];

                        localStorage.removeItem("savedFilters");
                        window.location.href = "/employee/employee-view?department=" + label;
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

                            const total = chart.data.datasets[0].data.reduce(
                                (sum, val) => sum + val,
                                0
                            );

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
                    {
                        afterRender: (chart) => {
                            if (typeof emptyChart === "function") {
                                emptyChart(chart);
                            }
                        }
                    }
                ],
            });

            // 🧩 Generate Custom Legend
            const $legendContainer = $("#chartLegend");
            $legendContainer.empty();

            labels.forEach((label, index) => {
                const color = colors[index % colors.length];

                const $item = $(`
                    <div style="display: flex; align-items: center; margin-bottom: 6px; cursor: pointer;">
                        <span style="display: inline-block; width: 12px; height: 12px; border-radius: 50%; background-color: ${color}; margin-right: 8px;"></span>
                        <span class="legend-label">${label}</span>
                    </div>
                `);

                $legendContainer.append($item);

                $item.on("click", function () {
                    visibility[index] = !visibility[index];

                    departmentChartInstance.data.datasets[0].data = values.map((val, i) =>
                        visibility[i] ? val : 0
                    );

                    const $dot = $(this).find("span").first();
                    const $label = $(this).find(".legend-label");

                    if (visibility[index]) {
                        $dot.css("opacity", "1");
                        $label.css("text-decoration", "none");
                    } else {
                        $dot.css("opacity", "0.4");
                        $label.css("text-decoration", "line-through");
                    }

                    departmentChartInstance.update();
                });
            });
        });
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
