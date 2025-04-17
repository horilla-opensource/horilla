$(document).ready(function(){
    function projectStatusChart(dataSet, labels) {
        const data = {
            labels: labels,
            datasets: dataSet,
        };
        // Create chart using the Chart.js library
        window['projectChart'] = {}
        const ctx = document.getElementById("projectStatusCanvas").getContext("2d");

        projectChart = new Chart(ctx, {
            type: 'bar',
            data: data,
            options: {
            },
        });
    }
        $.ajax({
        url: "/project/project-status-chart",
        type: "GET",
        success: function (response) {
            // Code to handle the response
            // response =  {'dataSet': [{'label': 'Odoo developer 2023-03-30', 'data': [3, 0, 5, 3]}, {'label': 'React developer 2023-03-31', 'data': [0, 1, 1, 0]}, {'label': 'Content Writer 2023-04-01', 'data': [1, 0, 0, 0]}], 'labels': ['Initial', 'Test', 'Interview', 'Hired']}
            dataSet = response.dataSet;
            labels = response.labels;
            projectStatusChart(dataSet, labels);

        },
        });
        $('#projectStatusForward').click(function (e) {
        var chartType = projectChart.config.type
        if (chartType === 'line') {
            chartType = 'bar';
        } else if(chartType==='bar') {
            chartType = 'doughnut';
        } else if(chartType==='doughnut'){
            chartType = 'pie'
        }else if(chartType==='pie'){
            chartType = 'line'
        }
        projectChart.config.type = chartType;
        projectChart.update();
        });

        // for creating task status chart
        function taskStatusChart(dataSet, labels) {
            const data = {
                labels: labels,
                datasets: dataSet,
            };
            // Create chart using the Chart.js library
            window['taskChart'] = {}
            const ctx = document.getElementById("taskStatusCanvas").getContext("2d");

            taskChart = new Chart(ctx, {
                type: 'bar',
                data: data,
                options: {
                },
            });
        }
            $.ajax({
            url: "/project/task-status-chart",
            type: "GET",
            success: function (response) {
                // Code to handle the response
                // response =  {'dataSet': [{'label': 'Odoo developer 2023-03-30', 'data': [3, 0, 5, 3]}, {'label': 'React developer 2023-03-31', 'data': [0, 1, 1, 0]}, {'label': 'Content Writer 2023-04-01', 'data': [1, 0, 0, 0]}], 'labels': ['Initial', 'Test', 'Interview', 'Hired']}
                dataSet = response.dataSet;
                labels = response.labels;
                taskStatusChart(dataSet, labels);

            },
            });
            $('#taskStatusForward').click(function (e) {
            var chartType = taskChart.config.type
            if (chartType === 'line') {
                chartType = 'bar';
            } else if(chartType==='bar') {
                chartType = 'doughnut';
            } else if(chartType==='doughnut'){
                chartType = 'pie'
            }else if(chartType==='pie'){
                chartType = 'line'
            }
            taskChart.config.type = chartType;
            taskChart.update();
            });

});
