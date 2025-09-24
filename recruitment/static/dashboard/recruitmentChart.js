
$(document).ready(function () {
	function recruitmentChart(dataSet, labels) {
		const styledDataSets = dataSet.map((dataset, index) => {
			const colors = ['#a5b4fc', '#fca5a5', '#fdba74', '#34d399', '#fbbf24', '#fb7185', '#60a5fa'];
			return {
				...dataset,
				backgroundColor: colors[index % colors.length],
				borderRadius: 10,
				barPercentage: 0.6,
				categoryPercentage: 0.8
			};
		});

		const data = {
			labels: labels,
			datasets: styledDataSets,
		};

		// Create chart using the Chart.js library
		window["myChart"] = {};
		if (document.getElementById("recruitmentChart1")) {
			const ctx = document.getElementById("recruitmentChart1").getContext("2d");
			myChart = new Chart(ctx, {
				type: "bar",
				data: data,
				options: {
					responsive: true,
					maintainAspectRatio: false,
					scales: {
						y: {
							beginAtZero: true,
							ticks: {
								stepSize: 20,
								color: '#6b7280'
							},
							grid: {
								color: '#e5e7eb'
							}
						},
						x: {
							ticks: {
								color: '#6b7280'
							},
							grid: {
								display: false
							}
						}
					},
					plugins: {
						legend: {
							position: 'bottom',
							labels: {
								usePointStyle: true,
								pointStyle: 'circle',
								font: {
									size: 12
								},
								color: '#374151',
								padding: 15
							},
							onClick: (e, legendItem, legend) => {
								const index = legendItem.datasetIndex;
								const chart = legend.chart;
								if (chart.isDatasetVisible(index)) {
									chart.hide(index);
									legendItem.hidden = true;
								} else {
									chart.show(index);
									legendItem.hidden = false;
								}
								chart.update();
							}
						},
						tooltip: {
							enabled: true
						}
					},
					onClick: (e, activeEls) => {
						if (activeEls.length > 0) {
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
						}
					},
				},
				plugins: [{
					afterRender: (chart) => {
						if (typeof emptyChart === "function") {
							emptyChart(chart);
						}
					}
				}]

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
			const ctx = document.getElementById("hiredCandidate")?.getContext("2d");
			if (!ctx || !response?.labels || !response?.data) return;

			const labels = response.labels;
			const values = response.data;
			const colors = [
				"#facc15",
                "#f87171",
                "#ddd6fe",
                "#a5b4fc",
                "#93c5fd",
                "#d1d5db",
			];
			const visibility = Array(labels.length).fill(true);

			const hiredCandidateInstance = new Chart(ctx, {
				type: "bar",
				data: {
					labels: labels,
					datasets: [{
						label: "Hired Candidates",
						data: values,
						backgroundColor: colors,
						borderRadius: 20,
						barPercentage: 0.8,
						categoryPercentage: 0.8,
					}]
				},
				options: {
					responsive: true,
					maintainAspectRatio: false,
					onClick: (e, activeEls) => {
						if (!activeEls.length) return;
						const dataIndex = activeEls[0].index;
						const label = labels[dataIndex];

						localStorage.removeItem("savedFilters");
						window.location.href =
							`/recruitment/candidate-view?recruitment=${label}&hired=true`;
					},
					plugins: {
						legend: { display: false },
						tooltip: {
							enabled: true,
							callbacks: {
								title: tooltipItems => labels[tooltipItems[0].dataIndex],
								label: tooltipItem => `Hired Candidates: ${tooltipItem.raw}`
							}
						}
					},
					scales: {
						y: {
							beginAtZero: true,
							ticks: { stepSize: 1, color: "#6b7280" },
							grid: { drawBorder: false, color: "#e5e7eb" }
						},
						x: {
							ticks: { display: false },
							grid: { display: false },
							border: { display: false }
						}
					}
				},
				plugins: [{
					afterRender: (chart) => {
						if (typeof emptyChart === "function") {
							emptyChart(chart);
						}
					}
				}]
			});

			// 🧩 Generate Custom Legend
			const $legendContainer = $("#hiredLegend");
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

					// Toggle bar value visibility
					hiredCandidateInstance.data.datasets[0].data = values.map((val, i) =>
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

					hiredCandidateInstance.update();
				});
			});

		},
		error: function (xhr, status, error) {
			console.error("Chart data fetch failed:", error);
		}
	});


//og
	// $.ajax({
	// 	type: "GET",
	// 	url: "/recruitment/hired-candidate-chart",
	// 	success: function (response) {
	// 		const ctx = document.getElementById("hiredCandidate");
	// 		if (ctx) {
	// 			new Chart(ctx, {
	// 				type: "bar",
	// 				data: {
	// 					labels: response.labels,
	// 					datasets: [
	// 						{
	// 							label: "#Hired candidates",
	// 							data: response.data,
	// 							backgroundColor: response.background_color,
	// 							borderColor: response.border_color,
	// 							borderWidth: 1,
	// 						},
	// 					],
	// 				},
	// 				options: {
	// 					responsive: true,

	// 					scales: {
	// 						y: {
	// 							beginAtZero: true,
	// 						},
	// 					},
	// 					onClick: (e, activeEls) => {
	// 						let datasetIndex = activeEls[0].datasetIndex;
	// 						let dataIndex = activeEls[0].index;
	// 						let datasetLabel = e.chart.data.datasets[datasetIndex].label;
	// 						let value = e.chart.data.datasets[datasetIndex].data[dataIndex];
	// 						let label = e.chart.data.labels[dataIndex];
	// 						localStorage.removeItem("savedFilters");
	// 						window.location.href =
	// 							"/recruitment/candidate-view" +
	// 							"?recruitment=" +
	// 							label +
	// 							"&hired=true";
	// 					},
	// 				},
	// 				plugins: [
	// 					{
	// 						afterRender: (chart) => emptyChart(chart),
	// 					},
	// 				],
	// 			});
	// 		}
	// 	},
	// });
});
