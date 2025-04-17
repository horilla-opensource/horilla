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
                departmentChart = new Chart(ctx, {
                    type: "bar",
                    data: {
                        labels: data.labels,
                        datasets: data.datasets,
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            x: {
                                stacked: true,
                            },
                            y: {
                                stacked: true,
                            },
                        },
                    },
                    plugins: [
                        {
                            afterRender: (chart) => emptyChart(chart),
                        },
                    ],
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
                joinChart = new Chart(ctx, {
                    type: type,
                    data: {
                        labels: data.labels,
                        datasets: [
                            {
                                label: "Employees",
                                data: data.items,
                            },
                        ],
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                    },
                    plugins: [
                        {
                            afterRender: (chart) => emptyChart(chart),
                        },
                    ],
                });
            },
            error: function (xhr, status, error) {
                console.error("Error fetching department chart data:", error);
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

    department_chart("pie");
    join_chart("bar");
});
