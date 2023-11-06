$(document).ready(function () {
	$("#attendance_month").val(formattedDate);

	$.ajax({
		url: "/attendance/dashboard-attendance",
		type: "GET",
		success: function (response) {
			// Code to handle the response
			dataSet = response.dataSet;
			labels = response.labels;
			createAttendanceChart(response.dataSet, response.labels);
		},
	});
});

var data;

function getWeekNumber(date) {
	// Clone the date object to avoid modifying the original
	var clonedDate = new Date(date);
	clonedDate.setHours(0, 0, 0, 0);

	// Set to nearest Thursday: current date + 4 - current day number
	// Make Sunday's day number 7
	clonedDate.setDate(clonedDate.getDate() + 4 - (clonedDate.getDay() || 7));

	// Get first day of year
	var yearStart = new Date(clonedDate.getFullYear(), 0, 1);

	// Calculate full weeks to nearest Thursday
	var weekNumber = Math.ceil(((clonedDate - yearStart) / 86400000 + 1) / 7);

	return weekNumber;
}

var today = new Date();
month = ("0" + (today.getMonth() + 1)).slice(-2);
year = today.getFullYear();
var day = ("0" + today.getDate()).slice(-2);
var formattedDate = year + "-" + month + "-" + day;
var currentWeek = getWeekNumber(today);

function createAttendanceChart(dataSet, labels) {
	data = {
		labels: labels,
		datasets: dataSet,
	};
	// Create chart using the Chart.js library
	window["attendanceChart"] = {};
	const ctx = document.getElementById("dailyAnalytic").getContext("2d");
	attendanceChart = new Chart(ctx, {
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
				var parms =
					"?department=" +
					datasetLabel +
					"&type=" +
					label.toLowerCase().replace(/\s/g, "_");
				var type = $("#type").val();
				const dateStr = $("#attendance_month").val();
				if (type == "weekly") {
					const [year, week] = dateStr.split("-W");
					parms = parms + "&week=" + week + "&year=" + year;
				} else if (type == "monthly") {
					const [year, month] = dateStr.split("-");
					parms = parms + "&month=" + month + "&year=" + year;
				} else if (type == "day") {
					parms = parms + "&attendance_date=" + dateStr;
				} else if (type == "date_range") {
					var start_date = dateStr;
					var end_date = $("#attendance_month2").val();
					parms =
						parms +
						"&attendance_date__gte=" +
						start_date +
						"&attendance_date__lte=" +
						end_date;
				}
				localStorage.removeItem("savedFilters");
				if (label == "On Time") {
					$.ajax({
						url: "/attendance/on-time-view" + parms,
						type: "GET",
						data: {
							input_type: type,
						},
						headers: {
							"X-Requested-With": "XMLHttpRequest",
						},
						success: (response) => {
							$("#back_button").removeClass("d-none");
							$("#dashboard").html(response);
						},
						error: (error) => {},
					});
				} else {
					window.location.href = "/attendance/late-come-early-out-view" + parms;
				}
			},
		},
		plugins: [
			{
				afterRender: (chart) => emptyChart(chart),
			},
		],
	});
}

function changeMonth() {
	let type = $("#type").val();
	let date = $("#attendance_month").val();
	let end_date = $("#attendance_month2").val();
	$.ajax({
		type: "GET",
		url: "/attendance/dashboard-attendance",
		dataType: "json",
		data: {
			date: date,
			type: type,
			end_date: end_date,
		},
		success: function (response) {
			
				attendanceChart.destroy()
				createAttendanceChart(response.dataSet, response.labels);
			
		},
		error: (error) => {},
	});
}

function changeView(element) {
	var dataType = $(element).val();
	if (dataType === "date_range") {
		$("#attendance_month").prop("type", "date");
		$("#day_input").before(
			'<input type="date" class="mb-2 float-end pointer oh-select ml-2" id="attendance_month2" style="width: 100px;color:#5e5c5c;" onchange="changeMonth(this)"/>'
		);
		$("#attendance_month").val(formattedDate);
		$("#attendance_month2").val(formattedDate);
		changeMonth();
	} else {
		$("#attendance_month2").remove();
		if (dataType === "weekly") {
			$("#attendance_month").prop("type", "week");
			$("#attendance_month").val(`${year}-W${currentWeek}`);
			changeMonth();
		} else if (dataType === "day") {
			$("#attendance_month").prop("type", "date");
			$("#attendance_month").val(formattedDate);
			changeMonth();
		} else {
			$("#attendance_month").prop("type", "month");
			$("#attendance_month").val(`${year}-${month}`);
			changeMonth();
		}
	}
}
