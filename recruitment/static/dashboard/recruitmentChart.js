$(document).ready(function () {
	function recruitmentChart(dataSet, labels) {
		const data = {
			labels: labels,
			datasets: dataSet,
		};
		// Create chart using the Chart.js library
		window["myChart"] = {};
		if (document.getElementById("recruitmentChart1")){
			const ctx = document.getElementById("recruitmentChart1").getContext("2d");
			myChart = new Chart(ctx, {
				type: "bar",
				data: data,
				options: {
					responsive: true,

					onClick: (e, activeEls) => {
						let datasetIndex = activeEls[0].datasetIndex;
						let dataIndex = activeEls[0].index;
						let datasetLabel = e.chart.data.datasets[datasetIndex].label;
						let value = e.chart.data.datasets[datasetIndex].data[dataIndex];
						let label = e.chart.data.labels[dataIndex];
						localStorage.removeItem("savedFilters");
						window.location.href =
							"/recruitment/candidate-view" +
							"?recruitment=" +
							datasetLabel +
							"&stage_id__stage_type=" +
							label.toLowerCase();
					},
				},
				plugins: [
					{
						afterRender: (chart) => emptyChart(chart),
					},
				],
			});
		}
	}
	$.ajax({
		url: "/recruitment/dashboard-pipeline",
		type: "GET",
		success: function (response) {
			// Code to handle the response
			dataSet = response.dataSet;
			labels = response.labels;
			recruitmentChart(dataSet, labels);
		},
	});

	$("#chart1").click(function (e) {
		var chartType = myChart.config.type;
		if (chartType === "line") {
			chartType = "bar";
		} else if (chartType === "bar") {
			chartType = "line";
		}
		myChart.config.type = chartType;
		myChart.update();
	});
	$.ajax({
		type: "GET",
		url: "/recruitment/hired-candidate-chart",
		success: function (response) {
			const ctx = document.getElementById("hiredCandidate");
			if (ctx) {
				new Chart(ctx, {
					type: "bar",
					data: {
						labels: response.labels,
						datasets: [
							{
								label: "#Hired candidates",
								data: response.data,
								backgroundColor: response.background_color,
								borderColor: response.border_color,
								borderWidth: 1,
							},
						],
					},
					options: {
						responsive: true,

						scales: {
							y: {
								beginAtZero: true,
							},
						},
						onClick: (e, activeEls) => {
							let datasetIndex = activeEls[0].datasetIndex;
							let dataIndex = activeEls[0].index;
							let datasetLabel = e.chart.data.datasets[datasetIndex].label;
							let value = e.chart.data.datasets[datasetIndex].data[dataIndex];
							let label = e.chart.data.labels[dataIndex];
							localStorage.removeItem("savedFilters");
							window.location.href =
								"/recruitment/candidate-view" +
								"?recruitment=" +
								label +
								"&hired=true";
						},
					},
					plugins: [
						{
							afterRender: (chart) => emptyChart(chart),
						},
					],
				});
			}
		},
	});
});
