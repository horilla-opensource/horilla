$(document).ready(function() {
	if (document.getElementById("objectiveChart")) {
		const ctx = document.getElementById("objectiveChart")?.getContext("2d");

		let objectiveChartInstance = null;


		function renderObjectiveChart(dataSet, labels) {
		const updatedDataSet = dataSet.map((ds) => ({
			...ds,
			backgroundColor: ["#f8e08e", "#c2c7cc","#8de5b3", "#f0a8a6", "#8ed1f7"],
			borderWidth: 0,
		}));

		if (objectiveChartInstance) {
			objectiveChartInstance.destroy();
		}

		objectiveChartInstance = new Chart(ctx, {
			type: "doughnut",
			data: {
			labels: labels,
			datasets: updatedDataSet,
			},
			options: {
			cutout: "70%",
			responsive: true,
			maintainAspectRatio: false,
			onClick: (e, activeEls) => {
				if (!activeEls.length) return;

				const dataIndex = activeEls[0].index;
				const label = labels[dataIndex];
				const params = `?status=${label}&archive=false&dashboard=True`;

				$.ajax({
				url: "/pms/objective-dashboard-view" + params,
				type: "GET",
				headers: { "X-Requested-With": "XMLHttpRequest" },
				success: (response) => {
					$("#dashboard").html(response);
					$("#back_button").removeClass("d-none");
				},
				error: (error) => {
					console.error("Error loading dashboard:", error);
				},
				});
			},
			plugins: {
				legend: {
				position: "bottom",
				labels: {
					usePointStyle: true,
					pointStyle: "circle",
					padding: 20,
					font: { size: 12 },
					color: "#000",
				},
				},
				tooltip: {
				padding: 10,
				cornerRadius: 4,
				backgroundColor: "#333",
				titleColor: "#fff",
				bodyColor: "#fff",
				callbacks: {
					label: function (context) {
					return context.parsed;
					},
				},
				},
			},
			},
			plugins: [
			{
				afterRender: (chart) => {
				if (typeof emptyChart === "function") {
					emptyChart(chart);
				}
				},
			},
			],
		});
		}

		// Update chart data and redraw
		function updateObjectiveChart(data) {
		const dataset = [{
			label: "Objective",
			data: data.objective_value,
		}];
		renderObjectiveChart(dataset, data.objective_label);
		}

		// Initial fetch
		$.ajax({
		url: "/pms/dashboard-objective-status",
		type: "GET",
		dataType: "json",
		headers: { "X-Requested-With": "XMLHttpRequest" },
		success: (response) => {
			updateObjectiveChart(response);
		},
		error: (error) => {
			console.error("Error loading objective chart data:", error);
		},
		});

		// Optional chart type toggle (pie/bar/doughnut etc.)
		$("#objective-status-chart").click(function () {
		const types = ["bar", "doughnut", "pie", "line"];
		const current = types.indexOf(objectiveChartInstance.config.type);
		const nextType = types[(current + 1) % types.length];
		objectiveChartInstance.config.type = nextType;
		objectiveChartInstance.update();
		});
	}
// const objectiveChart = document.getElementById("objectiveChart");
// // data dictionary
// var objectiveStatusData = {
// 	labels: [],
// 	datasets: [
// 		{
// 			label: "objective",
// 			data: [],
// 			backgroundColor: ["#8de5b3", "#f0a8a6", "#8ed1f7", "#f8e08e", "#c2c7cc"],
// 			hoverOffset: 3,
// 		},
// 	],
// 	message:"",
// };

// // chart constructor
// if (objectiveChart != null) {
// 	var objectiveStatusChart = new Chart(objectiveChart, {
// 		type: "doughnut",
// 		data: objectiveStatusData,
// 		options: {
// 			responsive: true,
// 			maintainAspectRatio:false,
// 			onClick: (e, activeEls) => {
// 				let datasetIndex = activeEls[0].datasetIndex;
// 				let dataIndex = activeEls[0].index;
// 				let datasetLabel = e.chart.data.datasets[datasetIndex].label;
// 				let value = e.chart.data.datasets[datasetIndex].data[dataIndex];
// 				let label = e.chart.data.labels[dataIndex];
// 				let params = "?status=" + label + "&archive=false" + "&dashboard=True";

// 				$.ajax({
// 					url: "/pms/objective-dashboard-view" + params,
// 					type: "GET",
// 					headers: {
// 						"X-Requested-With": "XMLHttpRequest",
// 					},
// 					success: (response) => {
// 						$("#dashboard").html(response);
// 					},
// 					error: (error) => {
// 						console.log("Error", error);
// 					},
// 				});
// 				$("#back_button").removeClass("d-none");
// 			},
// 		},
// 		plugins: [{
// 			afterRender: (chart)=>emptyChart(chart)
// 		}],
// 	});
// }

// function objectiveStatusDataUpdate(data) {
// 	objectiveStatusData.labels = data.objective_label;
// 	objectiveStatusData.datasets[0].data = data.objective_value;
// 	objectiveStatusData.message = data.message;
// 	if (objectiveStatusChart){
// 		objectiveStatusChart.update();
// 	}
// }

// $.ajax({
// 	url: "/pms/dashboard-objective-status",
// 	type: "GET",
// 	dataType: "json",
// 	headers: {
// 		"X-Requested-With": "XMLHttpRequest",
// 	},
// 	success: (response) => {
// 		objectiveStatusDataUpdate(response);
// 	},
// 	error: (error) => {
// 		console.log("Error", error);
// 	},
// });

// // chart change
// $("#objective-status-chart").click(function (e) {
// 	var chartType = objectiveStatusChart.config.type;
// 	if (chartType === "line") {
// 		chartType = "bar";
// 	} else if (chartType === "bar") {
// 		chartType = "doughnut";
// 	} else if (chartType === "doughnut") {
// 		chartType = "pie";
// 	} else if (chartType === "pie") {
// 		chartType = "line";
// 	}
// 	objectiveStatusChart.config.type = chartType;
// 	if (objectiveStatusChart){
// 		objectiveStatusChart.update();
// 	}

// });

// objecitve chart section end

// const keyResultStatusChartCtx = document.getElementById("keyResultChart");

// // data dictionary
// var keyResultStatusData = {
// 	labels: [],
// 	datasets: [
// 		{
// 			label: "key result",
// 			data: [],
// 			backgroundColor: ["#8de5b3", "#f0a8a6", "#8ed1f7", "#f8e08e", "#c2c7cc"],
// 			hoverOffset: 3,
// 		},
// 	],
// 	message:"",
// };

// // chart constructor
// if (keyResultStatusChartCtx != null) {
// 	var keyResultStatusChart = new Chart(keyResultStatusChartCtx, {
// 		type: "pie",
// 		data: keyResultStatusData,
// 		options: {
// 			responsive: true,
// 			maintainAspectRatio:false,
// 			onClick: (e, activeEls) => {
// 				let datasetIndex = activeEls[0].datasetIndex;
// 				let dataIndex = activeEls[0].index;
// 				let datasetLabel = e.chart.data.datasets[datasetIndex].label;
// 				let value = e.chart.data.datasets[datasetIndex].data[dataIndex];
// 				let label = e.chart.data.labels[dataIndex];
// 				let params = "?field=employee_objective_id__employee_id"+"&status=" + label + "&archive=false"
// 				let statusValue = params.split("&")[1].split("=")[1];
// 				$('input[name="status"]').val(decodeURIComponent(statusValue));
// 				$('#dashboardKeyresult button').click();
// 				$("#back_button").removeClass("d-none");
// 				$("#employeeKeyRes").removeClass("d-none");


// 			},
// 		},
// 		plugins: [{
// 			afterRender: (chart)=>emptyChart(chart)
// 		}],
// 	});
// }

// function keyResultStatusDataUpdate(data) {
// 	keyResultStatusData.labels = data.key_result_label;
// 	keyResultStatusData.datasets[0].data = data.key_result_value;
// 	keyResultStatusData.message = data.message;
// 	if(keyResultStatusChart){
// 		keyResultStatusChart.update();
// 	}
// }

// $.ajax({
// 	url: "/pms/dashbord-key-result-status",
// 	type: "GET",
// 	dataType: "json",
// 	headers: {
// 		"X-Requested-With": "XMLHttpRequest",
// 	},
// 	success: (response) => {
// 		keyResultStatusDataUpdate(response);
// 	},
// 	error: (error) => {
// 		console.log("Error", error);
// 	},
// });

// // chart change
// $("#key-result-status-chart").click(function (e) {
// 	var chartType = keyResultStatusChart.config.type;
// 	if (chartType === "line") {
// 		chartType = "bar";
// 	} else if (chartType === "bar") {
// 		chartType = "doughnut";
// 	} else if (chartType === "doughnut") {
// 		chartType = "pie";
// 	} else if (chartType === "pie") {
// 		chartType = "line";
// 	}
// 	keyResultStatusChart.config.type = chartType;
// 	if(keyResultStatusChart){
// 		keyResultStatusChart.update();
// 	}
// });

const keyResultStatusChartCtx = document.getElementById("keyResultChart");

// Data structure setup
var keyResultStatusData = {
  labels: [],
  datasets: [
    {
      label: "key result",
      data: [],
      backgroundColor: ["#cfe9ff", "#ffc9de", "#e6ccff", "#fde68a", "#d1d5db"],
      borderWidth: 0,
      hoverOffset: 4,
    },
  ],
  message: "",
};

let keyResultStatusChart = null;

if (keyResultStatusChartCtx) {
  keyResultStatusChart = new Chart(keyResultStatusChartCtx, {
    type: "doughnut",
    data: keyResultStatusData,
    options: {
      cutout: "70%",
      responsive: true,
      maintainAspectRatio: false,
      onClick: (e, activeEls) => {
        if (activeEls.length > 0) {
          const dataIndex = activeEls[0].index;
          const label = e.chart.data.labels[dataIndex];
          const params = `?field=employee_objective_id__employee_id&status=${label}&archive=false`;
          const statusValue = params.split("&")[1].split("=")[1];
          $('input[name="status"]').val(decodeURIComponent(statusValue));
          $('#dashboardKeyresult button').click();
          $("#back_button, #employeeKeyRes").removeClass("d-none");
        }
      },
      plugins: {
        legend: {
          position: "bottom",
          labels: {
            usePointStyle: true,
            pointStyle: "circle",
            padding: 20,
            font: { size: 12 },
            color: "#000",
          },
        },
      },
    },
    plugins: [
      {
        afterRender: (chart) => {
          if (typeof emptyChart === "function") {
            emptyChart(chart);
          }
        },
      },
    ],
  });
}

// Update function for AJAX response
function keyResultStatusDataUpdate(data) {
  keyResultStatusData.labels = data.key_result_label;
  keyResultStatusData.datasets[0].data = data.key_result_value;
  keyResultStatusData.message = data.message;

  if (keyResultStatusChart) {
    keyResultStatusChart.update();
  }
}

// Load data via AJAX
$.ajax({
  url: "/pms/dashbord-key-result-status",
  type: "GET",
  dataType: "json",
  headers: { "X-Requested-With": "XMLHttpRequest" },
  success: keyResultStatusDataUpdate,
  error: (err) => console.error("Error fetching chart data:", err),
});

// Toggle chart type on click
$("#key-result-status-chart").click(() => {
  if (!keyResultStatusChart) return;

  const typeOrder = ["line", "bar", "doughnut", "pie"];
  let idx = typeOrder.indexOf(keyResultStatusChart.config.type);
  keyResultStatusChart.config.type = typeOrder[(idx + 1) % typeOrder.length];
  keyResultStatusChart.update();
});

// key result chart section

// const feedbackStatusChartCtx = document.getElementById("feedbackChart");

// // data dictionary
// var feedbackStatusData = {
// 	labels: [],
// 	datasets: [
// 		{
// 			label: "Feedback",
// 			data: [],
// 			backgroundColor: ["#8de5b3", "#f0a8a6", "#8ed1f7", "#f8e08e", "#c2c7cc"],
// 			hoverOffset: 3,
// 		},
// 	],
// 	message:"",
// };

// // chart constructor
// if (feedbackStatusChartCtx != null) {
// 	var feedbackStatusChart = new Chart(feedbackStatusChartCtx, {
// 		type: "pie",
// 		data: feedbackStatusData,
// 		options: {
// 			responsive: true,
// 			maintainAspectRatio:false,
// 			onClick: (e, activeEls) => {
// 				let datasetIndex = activeEls[0].datasetIndex;
// 				let dataIndex = activeEls[0].index;
// 				let datasetLabel = e.chart.data.datasets[datasetIndex].label;
// 				let value = e.chart.data.datasets[datasetIndex].data[dataIndex];
// 				let label = e.chart.data.labels[dataIndex];
// 				let params = "?status=" + label + "&archive=false";
// 				window.location.href = "/pms/feedback-view" + params;
// 			},
// 		},
// 		plugins: [{
// 			afterRender: (chart)=>emptyChart(chart)
// 		}],
// 	});
// }

// function feedbackStatusDataUpdate(data) {
// 	feedbackStatusData.labels = data.feedback_label;
// 	feedbackStatusData.datasets[0].data = data.feedback_value;
// 	feedbackStatusData.message = data.message;
// 	if (feedbackStatusChart){
// 		feedbackStatusChart.update();
// 	}
// }

// $.ajax({
// 	url: "/pms/dashboard-feedback-status",
// 	type: "GET",
// 	dataType: "json",
// 	headers: {
// 		"X-Requested-With": "XMLHttpRequest",
// 	},
// 	success: (response) => {
// 		feedbackStatusDataUpdate(response);
// 	},
// 	error: (error) => {
// 		console.log("Error", error);
// 	},
// });

// // chart change
// $("#feedback-status-chart").click(function (e) {
// 	var chartType = feedbackStatusChart.config.type;
// 	if (chartType === "line") {
// 		chartType = "bar";
// 	} else if (chartType === "bar") {
// 		chartType = "doughnut";
// 	} else if (chartType === "doughnut") {
// 		chartType = "pie";
// 	} else if (chartType === "pie") {
// 		chartType = "line";
// 	}
// 	feedbackStatusChart.config.type = chartType;
// 	if (feedbackStatusChart){
// 		feedbackStatusChart.update();
// 	}
// });

if (document.getElementById("feedbackChart")) {
	const ctx = document.getElementById("feedbackChart")?.getContext("2d");
	let feedbackChartInstance = null;
	let visibility = [];

	function renderFeedbackChart(dataSet, labels) {
	const values = dataSet[0].data;
	const colors = [
		"#93c5fd",
		"#facc15",
		"#f87171",
		"#ddd6fe",
		"#a5b4fc",
		"#d1d5db",
	];
	let label_length = labels ? labels.length : 0
	visibility = Array(label_length).fill(true);

	// Destroy previous chart if it exists
	if (feedbackChartInstance) {
		feedbackChartInstance.destroy();
	}

	feedbackChartInstance = new Chart(ctx, {
		type: "doughnut",
		data: {
		labels: labels,
		datasets: [
			{
			...dataSet[0],
			backgroundColor: colors.slice(0, label_length),
			borderWidth: 0,
			borderRadius: 10,
			hoverOffset: 8,
			},
		],
		},
		options: {
		cutout: "70%",
		responsive: true,
		maintainAspectRatio: false,
		onClick: function (e, activeEls) {
			if (!activeEls.length) return;

			const dataIndex = activeEls[0].index;
			const label = labels[dataIndex];
			const params = "?status=" + label + "&archive=false";
			window.location.href = "/pms/feedback-view" + params;
		},
		plugins: {
			legend: { display: false },
			tooltip: {
			backgroundColor: "#111827",
			bodyColor: "#f3f4f6",
			borderColor: "#e5e7eb",
			borderWidth: 1,
			},
		},
		},
		plugins: [
		{
			afterRender: (chart) => {
			if (typeof emptyChart === "function") {
				emptyChart(chart);
			}
			},
		},
		],
	});

	// 🧩 Custom Legend Generation
	const $legendContainer = $("#feedbackChartLegend");
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

		feedbackChartInstance.data.datasets[0].data = values.map((val, i) =>
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

		feedbackChartInstance.update();
		});
	});
	}

	// 🔄 Load data via AJAX
	function fetchFeedbackData() {
	$.ajax({
		url: "/pms/dashboard-feedback-status",
		type: "GET",
		dataType: "json",
		headers: {
		"X-Requested-With": "XMLHttpRequest",
		},
		success: function (response) {
		const dataset = [
			{
			label: "Feedback",
			data: response.feedback_value,
			},
		];
		renderFeedbackChart(dataset, response.feedback_label);
		},
		error: function (error) {
		console.error("Error loading feedback chart:", error);
		},
	});
	}

	fetchFeedbackData();
}

});
