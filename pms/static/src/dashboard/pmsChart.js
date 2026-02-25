// PMS dashboard Charts.js

$(document).ready(function () {

    /* ============================================================
       CONFIG
    ============================================================ */

    const COLORS = ["#8de5b3", "#f0a8a6", "#8ed1f7", "#f8e08e", "#c2c7cc"];
    const CHART_TYPES = ["line", "bar", "doughnut", "pie"];


    /* ============================================================
       UTILITIES
    ============================================================ */

    function cycleChartType(chart) {
        if (!chart) return;

        const currentIndex = CHART_TYPES.indexOf(chart.config.type);
        const nextIndex = (currentIndex + 1) % CHART_TYPES.length;

        chart.config.type = CHART_TYPES[nextIndex];
        chart.update();
    }

    function fetchChartData(url, onSuccess) {
        $.ajax({
            url,
            type: "GET",
            dataType: "json",
            headers: { "X-Requested-With": "XMLHttpRequest" },
            success: onSuccess,
            error: (error) => console.error("Chart Error:", error)
        });
    }


    /* ============================================================
       CHART FACTORY
    ============================================================ */

    function createStatusChart({
        elementId,
        label,
        defaultType,
        dataUrl,
        viewUrl,
        labelKey,
        valueKey,
        useAjaxNavigation = true,
        extraParams = ""
    }) {

        const ctx = document.getElementById(elementId);
        if (!ctx) return null;

        const themedOptions = ChartTheme.getThemedOptions();

        const chartData = {
            labels: [],
            datasets: [{
                label,
                data: [],
                backgroundColor: COLORS,
                hoverOffset: 3,
                borderRadius: 10,
                borderWidth: 0
            }],
            message: ""
        };

        const chart = new Chart(ctx, {
            type: defaultType,
            data: chartData,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    ...themedOptions.plugins,
                    legend: {
                        ...themedOptions.plugins?.legend,
                        position: "bottom",
                        labels: {
                            ...themedOptions.plugins?.legend?.labels,
                            usePointStyle: true,
                            pointStyle: "circle",
                            padding: 15
                        }
                    }
                },
                onClick: (e, activeEls) => {
                    if (!activeEls?.length) return;

                    const index = activeEls[0].index;
                    const selectedLabel = e.chart.data.labels[index];

                    const params =
                        `?status=${encodeURIComponent(selectedLabel)}&archive=false${extraParams}`;

                    if (!viewUrl) return

                    if (useAjaxNavigation) {
                        $.ajax({
                            url: viewUrl + params,
                            type: "GET",
                            headers: { "X-Requested-With": "XMLHttpRequest" },
                            success: (response) => {
                                $("#dashboard").html(response);
                                $("#back_button").removeClass("d-none");
                            },
                            error: (error) => console.error("Navigation Error:", error)
                        });
                    } else {
                        window.location.href = viewUrl + params;
                    }
                }
            },
            plugins: [{
                afterRender: (chartInstance) => {
                    if (typeof emptyChart === "function") {
                        emptyChart(chartInstance);
                    }
                }
            }]
        });

        function updateData(data) {
            chartData.labels = Array.isArray(data?.[labelKey]) ? data[labelKey] : [];
            chartData.datasets[0].data = Array.isArray(data?.[valueKey]) ? data[valueKey] : [];
            chartData.message = data?.message || "";
            chart.update();
        }

        fetchChartData(dataUrl, updateData);

        return chart;
    }


    /* ============================================================
       INITIALIZE CHARTS
    ============================================================ */

    const objectiveChart = createStatusChart({
        elementId: "objectiveChart",
        label: "Objective",
        defaultType: "doughnut",
        dataUrl: "/pms/dashboard-objective-status",
        labelKey: "objective_label",
        valueKey: "objective_value",
        extraParams: "&dashboard=True"
    });

    const keyResultChart = createStatusChart({
        elementId: "keyResultChart",
        label: "Key Result",
        defaultType: "pie",
        dataUrl: "/pms/dashbord-key-result-status",
        viewUrl: "/pms/key-result-view",
        labelKey: "key_result_label",
        valueKey: "key_result_value"
    });

    const feedbackChart = createStatusChart({
        elementId: "feedbackChart",
        label: "Feedback",
        defaultType: "pie",
        dataUrl: "/pms/dashboard-feedback-status",
        viewUrl: "/pms/feedback-view",
        labelKey: "feedback_label",
        valueKey: "feedback_value",
        useAjaxNavigation: false
    });


    /* ============================================================
       CHART TYPE TOGGLE HANDLERS
    ============================================================ */

    $("#objective-status-chart").click(() => cycleChartType(objectiveChart));
    $("#key-result-status-chart").click(() => cycleChartType(keyResultChart));
    $("#feedback-status-chart").click(() => cycleChartType(feedbackChart));


    /* ============================================================
       OPTIONAL: Expose Globally (if needed)
    ============================================================ */

    window.objectiveStatusChart = objectiveChart;
    window.keyResultStatusChart = keyResultChart;
    window.feedbackStatusChart = feedbackChart;

    if (objectiveChart) ChartTheme.observe("objectiveStatusChart");
    if (keyResultChart) ChartTheme.observe("keyResultStatusChart");
    if (feedbackChart) ChartTheme.observe("feedbackStatusChart");

});
