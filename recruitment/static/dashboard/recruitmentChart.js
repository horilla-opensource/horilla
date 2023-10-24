$(document).ready(function () {
	function isChartEmpty(chartData) {
		if (!chartData) {
			return true;
		}
		for (let i = 0; i < chartData.length; i++) {
			if (chartData[i] && chartData[i].data) {
				const hasNonZeroValues = chartData[i].data.some((value) => value !== 0);
				if (hasNonZeroValues) {
					return false;
				}
			}
		}
		return true;
	}

	function recruitmentChart(dataSet, labels) {
		const data = {
			labels: labels,
			datasets: dataSet,
		};
		// Create chart using the Chart.js library
		window["myChart"] = {};
		const ctx = document.getElementById("recruitmentChart1").getContext("2d");
		myChart = new Chart(ctx, {
			type: "bar",
			data: data,
			options: {
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
		});
	}
	$.ajax({
		url: "/recruitment/dashboard-pipeline",
		type: "GET",
		success: function (response) {
			// Code to handle the response
			dataSet = response.dataSet;
			labels = response.labels;
			if (isChartEmpty(dataSet)) {
				$("#recruitmentChart1")
					.parent()
					.html(
						`<div style="height: 325px; display:flex;align-items: center;justify-content: center;" class="">
					<div style="" class="">
					<img style="display: block;width: 70px;margin: 20px auto ;" src="/static/images/ui/joiningchart.png" class="" alt=""/>
					<h3 style="font-size:16px" class="oh-404__subtitle">${response.message}</h3>
					</div>
				</div>`
					);
			} else {
				recruitmentChart(dataSet, labels);
			}
		},
	});

	$("#chart1").click(function (e) {
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
