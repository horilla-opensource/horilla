$(document).ready(function () {
	//Hired candididates recruitment wise chart
	function isChartEmpty(chartData) {
		if (!chartData) {
			return true;
		}
		for (let i = 0; i < chartData.length; i++) {
			
			if (chartData[i]) {
				const hasNonZeroValues = chartData.some((value) => value !== 0);
				if (hasNonZeroValues) {
					return false;
				}
			}
		}
		return true;
	}

	$.ajax({
		type: "GET",
		url: "/onboarding/hired-candidate-chart",
		success: function (response) {
			const ctx = document.getElementById("hiredCandidate");
			if (isChartEmpty(response.data)) {
				$("#hiredCandidate")
					.parent()
					.html(
						`<div style="height: 320px; display:flex;align-items: center;justify-content: center;" class="">
					<div style="" class="">
					<img style="display: block;width: 70px;margin: 20px auto ;" src="/static/images/ui/joiningchart.png" class="" alt=""/>
					<h3 style="font-size:16px" class="oh-404__subtitle">${response.message}</h3>
					</div>
				</div>`
					);
			} else {
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
				});
			}
		},
	});

	//onboarding started candidate chart
	$.ajax({
		type: "GET",
		url: "/onboarding/onboard-candidate-chart",
		success: function (response) {
			const ctx = document.getElementById("onboardCandidate");
			if (isChartEmpty(response.data)) {
				$("#onboardCandidate")
					.parent()
					.html(
						`<div style="height: 220px; display:flex;align-items: center;justify-content: center;" class="">
					<div style="" class="">
					<img style="display: block;width: 70px;margin: 20px auto ;" src="/static/images/ui/joiningchart.png" class="" alt=""/>
					<h3 style="font-size:16px" class="oh-404__subtitle">${response.message}</h3>
					</div>
				</div>`
					);
			} else {
				new Chart(ctx, {
					type: "bar",
					data: {
						labels: response.labels,
						datasets: [
							{
								label: "#onboarding candidates",
								data: response.data,
								backgroundColor: response.background_color,
								borderColor: response.border_color,
								borderWidth: 1,
							},
						],
					},
					options: {
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
								"&start_onboard=true";
						},
					},
				});
			}
		},
	});
});
