$(document).ready(function () {
	$.ajax({
		type: "GET",
		url: "/onboarding/onboard-candidate-chart",
		success: function (response) {
			const ctx = document.getElementById("onboardCandidate")?.getContext("2d");
			if (!ctx || !response?.data || !response?.labels) return;

			const labels = response.labels;
			const values = response.data;
			const colors = [
				"#a5b4fc", "#fca5a5", "#fdba74", "#8de5b3", "#fcd34d", "#c2c7cc"
			];
			const visibility = Array(labels.length).fill(true);

			const onboardChartInstance = new Chart(ctx, {
				type: "bar",
				data: {
					labels: labels,
					datasets: [{
						label: "Onboarding Candidates",
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
						window.location.href = `/recruitment/candidate-view?recruitment=${encodeURIComponent(label)}&start_onboard=true`;
					},
					plugins: {
						legend: { display: false },
						tooltip: {
							enabled: true,
							callbacks: {
								title: tooltipItems => labels[tooltipItems[0].dataIndex],
								label: tooltipItem => `Onboarding Candidates: ${tooltipItem.raw}`
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
							border: { display: true, color: "#d1d5db" }
						}
					}
				},
				plugins: [{
					afterRender: (chart) => {
						if (typeof emptyChart === "function") emptyChart(chart);
					}
				}]
			});

			// 🧩 Generate Custom Legend (same style as departmentChart)
			const $legendContainer = $("#onboardCandidateLegend");
			$legendContainer.empty();

			labels.forEach((label, index) => {
				const color = colors[index % colors.length];

				const $item = $(`
					<div style="display: flex; align-items: center; margin-bottom: 6px; cursor: pointer;">
						<span style="
							display: inline-block;
							width: 12px;
							height: 12px;
							border-radius: 50%;
							background-color: ${color};
							margin-right: 8px;
							transition: opacity 0.3s;
						"></span>
						<span class="legend-label" style="color: #111827; font-size: 14px;">${label}</span>
					</div>
				`);

				$legendContainer.append($item);

				$item.on("click", function () {
					visibility[index] = !visibility[index];

					onboardChartInstance.data.datasets[0].data = values.map((val, i) =>
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

					onboardChartInstance.update();
				});
			});
		},
		error: function (xhr, status, error) {
			console.error("Error fetching data:", error);
		}
	});

});

// $(document).ready(function () {
// 	//Hired candididates recruitment wise chart


// 	//onboarding started candidate chart
// 	$.ajax({
// 		type: "GET",
// 		url: "/onboarding/onboard-candidate-chart",
// 		success: function (response) {
// 			const ctx = document.getElementById("onboardCandidate");
// 			if (ctx) {
// 				new Chart(ctx, {
// 					type: "bar",
// 					data: {
// 						labels: response.labels,
// 						datasets: [
// 							{
// 								label: "#onboarding candidates",
// 								data: response.data,
// 								backgroundColor: response.background_color,
// 								borderColor: response.border_color,
// 								borderWidth: 1,
// 							},
// 						],
// 						// message:response.message,
// 						// emptyImageSrc:'/static/images/ui/sunbed.png'
// 					},
// 					options: {
// 						responsive: true,

// 						scales: {
// 							y: {
// 								beginAtZero: true,
// 							},
// 						},
// 						onClick: (e, activeEls) => {
// 							let datasetIndex = activeEls[0].datasetIndex;
// 							let dataIndex = activeEls[0].index;
// 							let datasetLabel = e.chart.data.datasets[datasetIndex].label;
// 							let value = e.chart.data.datasets[datasetIndex].data[dataIndex];
// 							let label = e.chart.data.labels[dataIndex];
// 							localStorage.removeItem("savedFilters");
// 							window.location.href =
// 								"/recruitment/candidate-view" +
// 								"?recruitment=" +
// 								label +
// 								"&start_onboard=true";
// 						},
// 					},
// 					plugins: [
// 						{
// 							afterRender: (chart) => emptyChart(chart),
// 						},
// 					],
// 				});
// 			}
// 		},
// 	});
// });
