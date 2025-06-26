$(document).ready(function(){
    // function projectStatusChart(dataSet, labels) {
    //     const data = {
    //         labels: labels,
    //         datasets: dataSet,
    //     };
    //     // Create chart using the Chart.js library
    //     window['projectChart'] = {}
    //     const ctx = document.getElementById("projectStatusCanvas").getContext("2d");

    //     projectChart = new Chart(ctx, {
    //         type: 'bar',
    //         data: data,
    //         options: {
    //         },
    //     });
    // }

    function projectStatusChart(dataSet, labels) {
        const defaultColors = [
            '#a5b4fc', // Light purple
            '#fca5a5', // Light red
            '#fdba74', // Light orange
            '#86efac', // Light green
            '#7dd3fc', // Light blue
            '#f9a8d4', // Light pink
            '#fde68a', // Light yellow
            '#c4b5fd', // Light violet
        ];

        // Apply enhanced styling to all datasets and assign default colors if not provided
        const enhancedDatasets = dataSet.map((dataset, index) => ({
            ...dataset,
            backgroundColor: dataset.backgroundColor || defaultColors[index % defaultColors.length],
            borderRadius: 20,
            barPercentage: 0.9,
            categoryPercentage: 0.9
        }));

        const data = {
            labels: labels,
            datasets: enhancedDatasets,
        };

        // Create chart using the Chart.js library with enhanced styling
        window['projectChart'] = {};
        const ctx = document.getElementById("projectStatusCanvas").getContext("2d");

        projectChart = new Chart(ctx, {
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
                        max: Math.max(...dataSet.flatMap(set => set.data)) + 20,
                        ticks: { stepSize: 20 },
                        grid: { drawBorder: false, color: '#e5e7eb' }
                    },
                    x: {
                        ticks: { display: false },
                        grid: { display: false },
                        border: { display: true, color: '#d1d5db' }
                    }
                }
            },
        });

        // Create clickable legend for datasets
        const legendContainer = document.getElementById('projectLegend');
        if (legendContainer) {
            // Clear existing legend items
            legendContainer.innerHTML = '';

            enhancedDatasets.forEach((dataset, i) => {
                const item = document.createElement('div');
                item.className = 'flex items-center gap-2 cursor-pointer';
                const color = dataset.backgroundColor || defaultColors[i % defaultColors.length];
                item.innerHTML = `
                    <span class="w-4 h-4 rounded-full inline-block" style="background:${color}; transition: 0.3s;"></span>
                    <span>${dataset.label || `Dataset ${i + 1}`}</span>
                `;

                item.addEventListener('click', () => {
                    // Toggle dataset visibility
                    const meta = projectChart.getDatasetMeta(i);
                    meta.hidden = meta.hidden === null ? !projectChart.data.datasets[i].hidden : null;
                    projectChart.update();

                    // Update legend visuals
                    const dot = item.querySelector('span');
                    const text = item.querySelectorAll('span')[1];
                    const isHidden = meta.hidden;
                    dot.style.opacity = isHidden ? '0.4' : '1';
                    text.style.textDecoration = isHidden ? 'line-through' : 'none';
                });

                legendContainer.appendChild(item);
            });
        }
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
        // function taskStatusChart(dataSet, labels) {
        //     const data = {
        //         labels: labels,
        //         datasets: dataSet,
        //     };
        //     // Create chart using the Chart.js library
        //     window['taskChart'] = {}
        //     const ctx = document.getElementById("taskStatusCanvas").getContext("2d");

        //     taskChart = new Chart(ctx, {
        //         type: 'bar',
        //         data: data,
        //         options: {
        //         },
        //     });
        // }
        function taskStatusChart(dataSet, labels) {
            const defaultColors = [
                '#a5b4fc', // Light purple
                '#fca5a5', // Light red
                '#fdba74', // Light orange
                '#86efac', // Light green
                '#7dd3fc', // Light blue
                '#f9a8d4', // Light pink
                '#fde68a', // Light yellow
                '#c4b5fd', // Light violet
            ];

            // Apply enhanced styling to all datasets and assign default colors if not provided
            const enhancedDatasets = dataSet.map((dataset, index) => ({
                ...dataset,
                backgroundColor: dataset.backgroundColor || defaultColors[index % defaultColors.length],
                borderRadius: 20,
                barPercentage: 0.9,
                categoryPercentage: 0.9
            }));

            const data = {
                labels: labels,
                datasets: enhancedDatasets,
            };

            // Create chart using the Chart.js library with enhanced styling
            window['taskChart'] = {};
            const ctx = document.getElementById("taskStatusCanvas").getContext("2d");

            taskChart = new Chart(ctx, {
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
                            max: Math.max(...dataSet.flatMap(set => set.data)) + 20,
                            ticks: { stepSize: 20 },
                            grid: { drawBorder: false, color: '#e5e7eb' }
                        },
                        x: {
                            ticks: { display: false },
                            grid: { display: false },
                            border: { display: true, color: '#d1d5db' }
                        }
                    }
                },
            });

            // Create clickable legend for datasets
            const legendContainer = document.getElementById('taskLegend');
            if (legendContainer) {
                // Clear existing legend items
                legendContainer.innerHTML = '';

                enhancedDatasets.forEach((dataset, i) => {
                    const item = document.createElement('div');
                    item.className = 'flex items-center gap-2 cursor-pointer';
                    const color = dataset.backgroundColor || defaultColors[i % defaultColors.length];
                    item.innerHTML = `
                        <span class="w-4 h-4 rounded-full inline-block" style="background:${color}; transition: 0.3s;"></span>
                        <span>${dataset.label || `Dataset ${i + 1}`}</span>
                    `;

                    item.addEventListener('click', () => {
                        // Toggle dataset visibility
                        const meta = taskChart.getDatasetMeta(i);
                        meta.hidden = meta.hidden === null ? !taskChart.data.datasets[i].hidden : null;
                        taskChart.update();

                        // Update legend visuals
                        const dot = item.querySelector('span');
                        const text = item.querySelectorAll('span')[1];
                        const isHidden = meta.hidden;
                        dot.style.opacity = isHidden ? '0.4' : '1';
                        text.style.textDecoration = isHidden ? 'line-through' : 'none';
                    });

                    legendContainer.appendChild(item);
                });
            }
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
