$(document).ready(function () {
	var today = new Date();
	var availableLeaveChart;
	var departmentLeaveChart;
	var leaveTypeChart;
	var leavePeriodChart;
	var myChart2 = document.getElementById("employeeLeave");
	var employeeLeaveChart = new Chart(myChart2, {
		type: "bar",
		data: {
			labels: [],
			datasets: [],
		},
	});
	var start_index = 0;
	var per_page = 10;

	month = ("0" + (today.getMonth() + 1)).slice(-2);
	year = today.getFullYear();
	$(".month").val(`${year}-${month}`);
	$("#dash_month").val(`${year}-${month}`);

	function isChartEmpty(chartData) {
		if (!chartData) {
			return true;
		}
		for (let i = 0; i < chartData.length; i++) {
			const hasNonZeroValues = chartData[i].data.some((value) => value !== 0);
			if (hasNonZeroValues) {
				return false; // Return false if any non-zero value is found
			}
		}
		return true; // Return true if all values are zero
	}

	//Employee wise chart for available leaves
	function available_leave_chart(dataSet) {
		var myChart1 = document.getElementById("availableLeave");
		availableLeaveChart = new Chart(myChart1, {
			type: "pie",
			data: {
				labels: dataSet.labels,
				datasets: dataSet.dataset,
			},
		});
	}

	function department_leave_chart(dataSet) {
		var myChart3 = document.getElementById("departmentLeave");
		departmentLeaveChart = new Chart(myChart3, {
			type: "pie",
			data: {
				labels: dataSet.labels,
				datasets: dataSet.dataset,
			},
		});
	}

	function leave_type_chart(dataSet) {
		var myChart4 = document.getElementById("leaveType");
		leaveTypeChart = new Chart(myChart4, {
			type: "doughnut",
			data: {
				labels: dataSet.labels,
				datasets: dataSet.dataset,
			},
		});
	}

	function leave_period_chart(dataSet) {
		var myChart4 = document.getElementById("leavePeriod");
		leavePeriodChart = new Chart(myChart4, {
			type: "line",
			data: {
				labels: dataSet.labels,
				datasets: dataSet.dataset,
			},
			options: {
				scales: {
					x: {
						//   stacked: true,
						title: {
							display: true,
							text: dataSet.x_axis,
							font: {
								weight: "bold",
								size: 16,
							},
						},
					},
					y: {
						//   stacked: true,
						title: {
							display: true,
							text: dataSet.y_axis,
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

	//Chart of leave request by employees
	function employee_leave_chart(dataSet) {
		employeeLeaveChart.destroy();

		var myChart2 = document.getElementById("employeeLeave");
		employeeLeaveChart = new Chart(myChart2, {
			type: "bar",
			data: {
				labels: dataSet.labels,
				datasets: dataSet.dataset,
			},
			options: {
				scales: {
					x: {
						//   stacked: true,
						title: {
							display: true,
							text: "Employees",
							font: {
								weight: "bold",
								size: 16,
							},
						},
					},
					y: {
						//   stacked: true,
						title: {
							display: true,
							text: "Number of days",
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
	$.ajax({
		type: "GET",
		url: "/leave/employee-leave-chart",
		dataType: "json",
		success: function (response) {
			dataSet = response.dataset;
			labels = response.labels;

			$.each(dataSet, function (key, item) {
				item["data"] = item.data.slice(start_index, start_index + per_page);
			});
			var values = Object.values(labels).slice(
				start_index,
				start_index + per_page
			);
			dataset = {
				labels: values,
				dataset: dataSet,
			};
			const dataObjects = [
				{
					label: "Draft",
					data: [0, 0, 0],
					backgroundColor: "rgba(255, 99, 132, 1)",
				},
				{
					label: "Review Ongoing",
					data: [0, 0, 0],
					backgroundColor: "rgba(255, 206, 86, 1)",
				},
				{
					label: "Confirmed",
					data: [0, 0, 0],
					backgroundColor: "rgba(54, 162, 235, 1)",
				},
				{
					label: "Paid",
					data: [0, 0, 0],
					backgroundColor: "rgba(75, 242, 182, 1)",
				},
			];

			if (isChartEmpty(dataSet)) {
				$("#employee_leave_canvas").html(
					`<div style="height: 380px; display:flex;align-items: center;justify-content: center;" class="">
					<div style="" class="">
					<img style="    display: block;width: 70px;margin: 20px auto ;" src="/static/images/ui/attendance.png" class="" alt=""/>
					<h3 style="font-size:16px" class="oh-404__subtitle">${response.message}</h3>
					</div>
				</div>`
				);
			} else {
				employee_leave_chart(dataset);
			}
			start_index += per_page;
		},
		error: (error) => {
			console.log("Error", error);
		},
	});

	$.ajax({
		type: "GET",
		url: "/leave/available-leaves",
		dataType: "json",
		success: function (response) {
			if (isChartEmpty(response.dataset)) {
				$("#availableLeaveContainer").html(
					`<div style="height: 310px; display:flex;align-items: center;justify-content: center;" class="">
					<div style="" class="">
					<img style="    display: block;width: 70px;margin: 20px auto ;" src="/static/images/ui/sunbed outline.png" class="" alt=""/>
					<h3 style="font-size:16px" class="oh-404__subtitle">${response.message}</h3>
					</div>
				</div>`
				);
			} else {
				available_leave_chart(response);
			}
		},
		error: (error) => {
			console.log("Error", error);
		},
	});
	$.ajax({
		type: "GET",
		url: "/leave/department-leave-chart",
		dataType: "json",
		success: function (response) {
			department_leave_chart(response);
		},
		error: (error) => {
			console.log("Error", error);
		},
	});

	$.ajax({
		type: "GET",
		url: "/leave/leave-type-chart",
		dataType: "json",
		success: function (response) {
			leave_type_chart(response);
		},
		error: (error) => {
			console.log("Error", error);
		},
	});

	$.ajax({
		type: "GET",
		url: "/leave/leave-over-period",
		dataType: "json",
		success: function (response) {
			leave_period_chart(response);
		},
		error: (error) => {
			console.log("Error", error);
		},
	});

	$(".month").on("change", function () {
		month = $(this).val();
		$(this).attr("hx-vals", `{"date":"${month}","dashboard":"true"}`);
	});
	$("#dash_month").on("change", function () {
		let month = $(this).val();
		$.ajax({
			type: "GET",
			url: "/leave/employee-leave-chart",
			dataType: "json",
			data: {
				date: month,
			},
			success: function (response) {
				if (isChartEmpty(response.dataset)) {
					$("#employee_leave_canvas").html(
						`<div style="height: 310px; display:flex;align-items: center;justify-content: center;" class="">
					<div style="" class="">
					<img style="    display: block;width: 70px;margin: 20px auto ;" src="/static/images/ui/attendance.png" class="" alt=""/>
					<h3 style="font-size:16px" class="oh-404__subtitle">${response.message}</h3>
					</div>
				</div>`
					);
				} else {
					$("#employee_leave_canvas").html(
						'<canvas id="employeeLeave" class="pointer"></canvas>'
					);
					employee_leave_chart(response);
				}
			},
			error: (error) => {
				console.log("Error", error);
			},
		});
	});

	$("#employee-next").on("click", function () {
		var period = $("#monthYearField").val();
		$.ajax({
			url: "/leave/employee-leave-chart",
			type: "GET",
			dataType: "json",
			headers: {
				"X-Requested-With": "XMLHttpRequest",
			},
			data: {
				period: period,
			},
			success: (response) => {
				dataSet = response.dataset;
				labels = response.labels;

				updated_data = dataSet;
				if (start_index == 0) {
					start_index += per_page;
				}
				$.each(updated_data, function (key, item) {
					item["data"] = item.data.slice(start_index, start_index + per_page);
				});

				var values = Object.values(labels).slice(
					start_index,
					start_index + per_page
				);
				if (values.length > 0) {
					dataset = {
						labels: values,
						dataset: updated_data,
					};
					employee_leave_chart(dataset);
					start_index += per_page;
				}
			},
			error: (error) => {
				console.log("Error", error);
			},
		});
	});

	$("#employee-previous").on("click", function () {
		var period = $("#monthYearField").val();
		$.ajax({
			url: "/leave/employee-leave-chart",
			type: "GET",
			dataType: "json",
			headers: {
				"X-Requested-With": "XMLHttpRequest",
			},
			data: {
				period: period,
			},
			success: (response) => {
				dataSet = response.dataset;
				labels = response.labels;

				if (start_index <= 0) {
					return;
				}
				start_index -= per_page;
				if (start_index > 0) {
					updated_data = dataSet.map((item) => ({
						...item,
						data: item.data.slice(start_index - per_page, start_index),
					}));
					var values = Object.values(labels).slice(
						start_index - per_page,
						start_index
					);
					dataset = {
						labels: values,
						dataset: updated_data,
					};
					employee_leave_chart(dataset);
				}
			},
			error: (error) => {
				console.log("Error", error);
			},
		});
	});

	$(".filter").on("click", function () {
		$("#back_button").removeClass("d-none");
	});
});
