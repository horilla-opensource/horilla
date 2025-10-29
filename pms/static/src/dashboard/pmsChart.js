$(document).ready(function() {
const objectiveChart = document.getElementById("objectiveChart");
// data dictionary
var objectiveStatusData = {
	labels: [],
	datasets: [
		{
			label: "objective",
			data: [],
			backgroundColor: ["#8de5b3", "#f0a8a6", "#8ed1f7", "#f8e08e", "#c2c7cc"],
			hoverOffset: 3,
		},
	],
	message:"",
};

// chart constructor
if (objectiveChart != null) {
	var objectiveStatusChart = new Chart(objectiveChart, {
		type: "doughnut",
		data: objectiveStatusData,
		options: {
			responsive: true,
			maintainAspectRatio:false,
			onClick: (e, activeEls) => {
				let datasetIndex = activeEls[0].datasetIndex;
				let dataIndex = activeEls[0].index;
				let datasetLabel = e.chart.data.datasets[datasetIndex].label;
				let value = e.chart.data.datasets[datasetIndex].data[dataIndex];
				let label = e.chart.data.labels[dataIndex];
				let params = "?status=" + label + "&archive=false" + "&dashboard=True";

				$.ajax({
					url: "/pms/objective-dashboard-view" + params,
					type: "GET",
					headers: {
						"X-Requested-With": "XMLHttpRequest",
					},
					success: (response) => {
						$("#dashboard").html(response);
					},
					error: (error) => {
						console.log("Error", error);
					},
				});
				$("#back_button").removeClass("d-none");
			},
		},
		plugins: [{
			afterRender: (chart)=>emptyChart(chart)
		}],
	});
}

function objectiveStatusDataUpdate(data) {
	objectiveStatusData.labels = data.objective_label;
	objectiveStatusData.datasets[0].data = data.objective_value;
	objectiveStatusData.message = data.message;
	if (objectiveStatusChart){
		objectiveStatusChart.update();
	}
}

$.ajax({
	url: "/pms/dashboard-objective-status",
	type: "GET",
	dataType: "json",
	headers: {
		"X-Requested-With": "XMLHttpRequest",
	},
	success: (response) => {
		objectiveStatusDataUpdate(response);
	},
	error: (error) => {
		console.log("Error", error);
	},
});

// chart change
$("#objective-status-chart").click(function (e) {
	var chartType = objectiveStatusChart.config.type;
	if (chartType === "line") {
		chartType = "bar";
	} else if (chartType === "bar") {
		chartType = "doughnut";
	} else if (chartType === "doughnut") {
		chartType = "pie";
	} else if (chartType === "pie") {
		chartType = "line";
	}
	objectiveStatusChart.config.type = chartType;
	if (objectiveStatusChart){
		objectiveStatusChart.update();
	}

});

// objecitve chart section end

const keyResultStatusChartCtx = document.getElementById("keyResultChart");

// data dictionary
var keyResultStatusData = {
	labels: [],
	datasets: [
		{
			label: "key result",
			data: [],
			backgroundColor: ["#8de5b3", "#f0a8a6", "#8ed1f7", "#f8e08e", "#c2c7cc"],
			hoverOffset: 3,
		},
	],
	message:"",
};

// chart constructor
if (keyResultStatusChartCtx != null) {
	var keyResultStatusChart = new Chart(keyResultStatusChartCtx, {
		type: "pie",
		data: keyResultStatusData,
		options: {
			responsive: true,
			maintainAspectRatio:false,
			onClick: (e, activeEls) => {
				let datasetIndex = activeEls[0].datasetIndex;
				let dataIndex = activeEls[0].index;
				let datasetLabel = e.chart.data.datasets[datasetIndex].label;
				let value = e.chart.data.datasets[datasetIndex].data[dataIndex];
				let label = e.chart.data.labels[dataIndex];
				let params = "?field=employee_objective_id__employee_id"+"&status=" + label + "&archive=false"
				let statusValue = params.split("&")[1].split("=")[1];
				$('input[name="status"]').val(decodeURIComponent(statusValue));
				$('#dashboardKeyresult button').click();
				$("#back_button").removeClass("d-none");
				$("#employeeKeyRes").removeClass("d-none");


			},
		},
		plugins: [{
			afterRender: (chart)=>emptyChart(chart)
		}],
	});
}

function keyResultStatusDataUpdate(data) {
	keyResultStatusData.labels = data.key_result_label;
	keyResultStatusData.datasets[0].data = data.key_result_value;
	keyResultStatusData.message = data.message;
	if(keyResultStatusChart){
		keyResultStatusChart.update();
	}
}

$.ajax({
	url: "/pms/dashbord-key-result-status",
	type: "GET",
	dataType: "json",
	headers: {
		"X-Requested-With": "XMLHttpRequest",
	},
	success: (response) => {
		keyResultStatusDataUpdate(response);
	},
	error: (error) => {
		console.log("Error", error);
	},
});

// chart change
$("#key-result-status-chart").click(function (e) {
	var chartType = keyResultStatusChart.config.type;
	if (chartType === "line") {
		chartType = "bar";
	} else if (chartType === "bar") {
		chartType = "doughnut";
	} else if (chartType === "doughnut") {
		chartType = "pie";
	} else if (chartType === "pie") {
		chartType = "line";
	}
	keyResultStatusChart.config.type = chartType;
	if(keyResultStatusChart){
		keyResultStatusChart.update();
	}
});

// key result chart section

const feedbackStatusChartCtx = document.getElementById("feedbackChart");

// data dictionary
var feedbackStatusData = {
	labels: [],
	datasets: [
		{
			label: "Feedback",
			data: [],
			backgroundColor: ["#8de5b3", "#f0a8a6", "#8ed1f7", "#f8e08e", "#c2c7cc"],
			hoverOffset: 3,
		},
	],
	message:"",
};

// chart constructor
if (feedbackStatusChartCtx != null) {
	var feedbackStatusChart = new Chart(feedbackStatusChartCtx, {
		type: "pie",
		data: feedbackStatusData,
		options: {
			responsive: true,
			maintainAspectRatio:false,
			onClick: (e, activeEls) => {
				let datasetIndex = activeEls[0].datasetIndex;
				let dataIndex = activeEls[0].index;
				let datasetLabel = e.chart.data.datasets[datasetIndex].label;
				let value = e.chart.data.datasets[datasetIndex].data[dataIndex];
				let label = e.chart.data.labels[dataIndex];
				let params = "?status=" + label + "&archive=false";
				window.location.href = "/pms/feedback-view" + params;
			},
		},
		plugins: [{
			afterRender: (chart)=>emptyChart(chart)
		}],
	});
}

function feedbackStatusDataUpdate(data) {
	feedbackStatusData.labels = data.feedback_label;
	feedbackStatusData.datasets[0].data = data.feedback_value;
	feedbackStatusData.message = data.message;
	if (feedbackStatusChart){
		feedbackStatusChart.update();
	}
}

$.ajax({
	url: "/pms/dashboard-feedback-status",
	type: "GET",
	dataType: "json",
	headers: {
		"X-Requested-With": "XMLHttpRequest",
	},
	success: (response) => {
		feedbackStatusDataUpdate(response);
	},
	error: (error) => {
		console.log("Error", error);
	},
});

// chart change
$("#feedback-status-chart").click(function (e) {
	var chartType = feedbackStatusChart.config.type;
	if (chartType === "line") {
		chartType = "bar";
	} else if (chartType === "bar") {
		chartType = "doughnut";
	} else if (chartType === "doughnut") {
		chartType = "pie";
	} else if (chartType === "pie") {
		chartType = "line";
	}
	feedbackStatusChart.config.type = chartType;
	if (feedbackStatusChart){
		feedbackStatusChart.update();
	}
});
});
