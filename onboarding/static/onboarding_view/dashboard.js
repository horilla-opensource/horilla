$(document).ready(function () {
	var index = 0;
	var onboardingChart;

	function isChartEmpty(chartData) {
		if (!chartData) {
			return true;
		}
		for (let i = 0; i < chartData.data.length; i++) {
			const hasNonZeroValues = chartData.data.some((value) => value !== 0);
			if (hasNonZeroValues) {
				return false; // Return false if any non-zero value is found
			}
		}
		return true; // Return true if all values are zero
	}

	function stage_chart(data) {
		const stages = data.labels;
		const candidatesPerStage = data.data;
		const backgroundColor = data.background_color;
		const borderColor = data.border_color;
		var recruitment_name = data.recruitment;

		const ctx = document.getElementById("onboardingChart").getContext("2d");

		onboardingChart = new Chart(ctx, {
			type: "bar",
			data: {
				labels: stages,
				datasets: [
					{
						label: "Candidates per Stage",
						data: candidatesPerStage,
						backgroundColor: backgroundColor,
						borderColor: borderColor,
						borderWidth: 1,
					},
				],
			},
			options: {
				scales: {
					y: {
						title: {
							display: true,
							text: "Number of Candidates",
							font: {
								weight: "bold",
								size: 16,
							},
						},
					},
					x: {
						title: {
							display: true,
							text: recruitment_name,
							font: {
								weight: "bold",
								size: 16,
							},
						},
					},
				},
			},
		});
	}

	function stage_chart_view(recuitment) {
		$.ajax({
			url: "/onboarding/stage-chart?recruitment=" + recuitment,
			type: "GET",
			dataType: "json",
			headers: {
				"X-Requested-With": "XMLHttpRequest",
			},
			success: (response) => {
				if (onboardingChart) {
					onboardingChart.destroy();
				}
				if (isChartEmpty(response)) {
					$("#onboarding_canvas_body").html(
						`<div style="height: 310px; display:flex;align-items: center;justify-content: center;" class="">
                        <div style="" class="">
                        <img style="display: block;width: 90px;margin: 10px auto ;" src="/static/images/ui/no_candidate.png" alt=""/>
                        <h3 style="font-size:16px" class="oh-404__subtitle">${response.message}</h3>
                        </div>
                    </div>`
					);
				} else {
					stage_chart(response);
				}
			},
			error: (error) => {
				console.log("Error", error);
			},
		});
	}

	stage_chart_view(recruitment[index]);

	$("#stage-chart-next").on("click", function () {
		if (index < Object.keys(recruitment).length - 1) {
			index += 1;
		} else {
			index = 0;
		}
		stage_chart_view(recruitment[index]);
	});
	$("#stage-chart-previous").on("click", function () {
		if (index > 0) {
			index -= 1;
		} else {
			index = Object.keys(recruitment).length - 1;
		}
		stage_chart_view(recruitment[index]);
	});
});
