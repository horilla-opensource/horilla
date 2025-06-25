staticUrl = $("#statiUrl").attr("data-url");
$(document).ready(function () {
 // initializing the department overtime chart.
 var departmentChartData = {
 labels: [],
 datasets: [],
 };
 window["departmentOvertimeChart"] = {};
 const departmentOvertimeChart = document.getElementById(
 "departmentOverChart"
 );
 if (departmentOvertimeChart) {
 var departmentAttendanceChart = new Chart(departmentOvertimeChart, {
 type: "pie",
 data: departmentChartData,
 options: {
 responsive: true,
 maintainAspectRatio: false,
 },
 plugins: [
 {
 afterRender: (departmentAttendanceChart) =>
 emptyOvertimeChart(departmentAttendanceChart),
 },
 ],
 });
 }

 var today = new Date();
 month = ("0" + (today.getMonth() + 1)).slice(-2);
 year = today.getFullYear();
 var day = ("0" + today.getDate()).slice(-2);
 var formattedDate = year + "-" + month + "-" + day;
 var currentWeek = getWeekNumber(today);

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

 // Function to update the department overtime chart according to the response fetched from backend.

 function departmentDataUpdate(response) {
 departmentChartData.labels = response.labels;
 departmentChartData.datasets = response.dataset;
 departmentChartData.message = response.message;
 departmentChartData.emptyImageSrc = response.emptyImageSrc;
 if (departmentAttendanceChart) {
 departmentAttendanceChart.update();
 }
 }

 // Function to update the department overtime chart according to the dates provided.

 function changeDepartmentMonth() {
 let type = $("#department_date_type").val();
 let date = $("#department_month").val();
 let end_date = $("#department_month2").val();
 $.ajax({
 type: "GET",
 url: "/attendance/department-overtime-chart",
 dataType: "json",
 data: {
 date: date,
 type: type,
 end_date: end_date,
 },
 success: function (response) {
 departmentDataUpdate(response);
 },
 error: (error) => {},
 });
 }

 // Function to update the input fields according to type select field.

 function changeDepartmentView(element) {
 var dataType = $(element).val();
 if (dataType === "date_range") {
 $("#department_month").prop("type", "date");
 $("#department_day_input").after(
 '<input type="date" class="mb-2 float-end pointer oh-select ml-2" id="department_month2" style="width: 100px;color:#5e5c5c;"/>'
 );
 $("#department_month").val(formattedDate);
 $("#department_month2").val(formattedDate);
 changeDepartmentMonth();
 } else {
 $("#department_month2").remove();
 if (dataType === "weekly") {
 $("#department_month").prop("type", "week");
 if (currentWeek < 10) {
 $("#department_month").val(`${year}-W0${currentWeek}`);
 } else {
 $("#department_month").val(`${year}-W${currentWeek}`);
 }
 changeDepartmentMonth();
 } else if (dataType === "day") {
 $("#department_month").prop("type", "date");
 $("#department_month").val(formattedDate);
 changeDepartmentMonth();
 } else {
 $("#department_month").prop("type", "month");
 $("#department_month").val(`${year}-${month}`);
 changeDepartmentMonth();
 }
 }
 }

 // Function for empty message for department overtime chart.

 function emptyOvertimeChart(departmentAttendanceChart, args, options) {
 flag = false;
 for (let i = 0; i < departmentAttendanceChart.data.datasets.length; i++) {
 flag =
 flag + departmentAttendanceChart.data.datasets[i].data.some(Boolean);
 }
 if (!flag) {
 const { ctx, canvas } = departmentAttendanceChart;
 departmentAttendanceChart.clear();
 const parent = canvas.parentElement;

 // Set canvas width/height to match
 canvas.width = parent.clientWidth;
 canvas.height = parent.clientHeight;
 // Calculate center position
 const x = canvas.width / 2;
 const y = (canvas.height - 70) / 2;
 var noDataImage = new Image();
 noDataImage.src = departmentAttendanceChart.data.emptyImageSrc
 ? departmentAttendanceChart.data.emptyImageSrc
 : staticUrl + "images/ui/no_records.svg";

 message = departmentAttendanceChart.data.message
 ? departmentAttendanceChart.data.message
 : emptyMessages[languageCode];

 noDataImage.onload = () => {
 // Draw image first at center
 ctx.drawImage(noDataImage, x - 35, y, 70, 70);

 // Draw text below image
 ctx.textAlign = "center";
 ctx.textBaseline = "middle";
 ctx.fillStyle = "hsl(0,0%,45%)";
 ctx.font = "16px Poppins";
 ctx.fillText(message, x, y + 70 + 30);
 };
 }
 }

 // Ajax request to create department overtime chart initially.

 $.ajax({
 url: "/attendance/department-overtime-chart",
 type: "GET",
 dataType: "json",
 headers: {
 "X-Requested-With": "XMLHttpRequest",
 },
 success: (response) => {
 departmentDataUpdate(response);
 },
 error: (error) => {
 console.log("Error", error);
 },
 });

 // Functions to update department overtime chart while changing the date input field and select input field.

 $("#departmentChartCard").on("change", "#department_date_type", function (e) {
 changeDepartmentView($(this));
 });

 $("#departmentChartCard").on("change", "#department_month", function (e) {
 changeDepartmentMonth();
 });

 $("#departmentChartCard").on("change", "#department_month2", function (e) {
 changeDepartmentMonth();
 });
});

var data;

function emptyChart(chart) {
 if (chart.data.datasets.every(dataset => dataset.data.every(value => value === 0))) {
 chart.data.datasets = [{
 label: 'No Data',
 data: chart.data.labels.map(() => 0),
 backgroundColor: '#e5e7eb'
 }];
 }
}

function generateUniqueColors(count) {
 const colors = [];
 const hueStep = 360 / count; // Distribute hues evenly
 for (let i = 0; i < count; i++) {
 const hue = i * hueStep;
 // Convert HSL to hex with fixed saturation (40%) and lightness (85%) for pastel colors
 const hslToHex = (h, s, l) => {
 l /= 100;
 const a = s * Math.min(l, 1 - l) / 100;
 const f = n => {
 const k = (n + h / 30) % 12;
 const color = l - a * Math.max(Math.min(k - 3, 9 - k, 1), -1);
 return Math.round(255 * color).toString(16).padStart(2, '0');
 };
 return `#${f(0)}${f(8)}${f(4)}`;
 };
 colors.push(hslToHex(hue, 40, 85));
 }
 return colors;
}

function createAttendanceChart(dataSet, labels) {
 const colors = generateUniqueColors(dataSet.length);

 const modifiedDataSet = dataSet.map((dataset, index) => ({
 ...dataset,
 backgroundColor: colors[index],
 borderRadius: 10,
 barPercentage: 0.8,
 categoryPercentage: 0.6
 }));

 const data = {
 labels: labels,
 datasets: modifiedDataSet,
 };

 if (document.getElementById("dailyAnalytic")) {
 const ctx = document.getElementById("dailyAnalytic").getContext("2d");
 if (window["attendanceChart"]) {
 window["attendanceChart"].destroy();
 }

 window["attendanceChart"] = new Chart(ctx, {
 type: "bar",
 data: data,
 options: {
 responsive: true,
 maintainAspectRatio: false,
 scales: {
 y: {
 beginAtZero: true,
 ticks: {
 stepSize: 5,
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
 let parms = "?department=" + datasetLabel + "&type=" + label.toLowerCase().replace(/\s/g, "_");
 let type = $("#type").val();
 const dateStr = $("#attendance_month").val();

 if (type === "weekly") {
 const [year, week] = dateStr.split("-W");
 parms += `&week=${week}&year=${year}`;
 } else if (type === "monthly") {
 const [year, month] = dateStr.split("-");
 parms += `&month=${month}&year=${year}`;
 } else if (type === "day") {
 parms += `&attendance_date=${dateStr}`;
 } else if (type === "date_range") {
 const start_date = dateStr;
 const end_date = $("#attendance_month2").val();
 parms += `&attendance_date__gte=${start_date}&attendance_date__lte=${end_date}`;
 }

 localStorage.removeItem("savedFilters");
 if (label === "On Time") {
 $.ajax({
 url: "/attendance/on-time-view" + parms,
 type: "GET",
 data: { input_type: type },
 headers: { "X-Requested-With": "XMLHttpRequest" },
 success: (response) => {
 $("#back_button").removeClass("d-none");
 $("#dashboard").html(response);
 },
 error: (error) => console.error('Ajax error:', error),
 });
 } else {
 window.location.href = "/attendance/late-come-early-out-view" + parms;
 }
 }
 },
 },
 plugins: [{
 afterRender: (chart) => emptyChart(chart),
 }],
 });
 }
}

function getWeekNumber(date) {
 const clonedDate = new Date(date);
 clonedDate.setHours(0, 0, 0, 0);
 clonedDate.setDate(clonedDate.getDate() + 4 - (clonedDate.getDay() || 7));
 const yearStart = new Date(clonedDate.getFullYear(), 0, 1);
 return Math.ceil(((clonedDate - yearStart) / 86400000 + 1) / 7);
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
 end_date: type === "date_range" ? end_date : undefined,
 },
 success: function (response) {
 if (window["attendanceChart"]) {
 window["attendanceChart"].destroy();
 }
 createAttendanceChart(response.dataSet, response.labels);
 },
 error: (error) => console.error('Ajax error:', error),
 });
}

function changeView(element) {
 const dataType = $(element).val();
 const today = new Date();
 const month = ("0" + (today.getMonth() + 1)).slice(-2);
 const year = today.getFullYear();
 const day = ("0" + today.getDate()).slice(-2);
 const formattedDate = `${year}-${month}-${day}`;
 const currentWeek = getWeekNumber(today);

 if (dataType === "date_range") {
 $("#attendance_month").prop("type", "date");
 $("#attendance_month2").remove();
 $("#day_input").after(
 '<input type="date" class="mb-2 float-end pointer oh-select ml-2" id="attendance_month2" style="width: 100px;color:#5e5c5c;" onchange="changeMonth()"/>'
 );
 $("#attendance_month").val(formattedDate);
 $("#attendance_month2").val(formattedDate);
 } else {
 $("#attendance_month2").remove();
 if (dataType === "weekly") {
 $("#attendance_month").prop("type", "week");
 $("#attendance_month").val(`${year}-W${currentWeek.toString().padStart(2, '0')}`);
 } else if (dataType === "day") {
 $("#attendance_month").prop("type", "date");
 $("#attendance_month").val(formattedDate);
 } else if (dataType === "monthly") {
 $("#attendance_month").prop("type", "month");
 $("#attendance_month").val(`${year}-${month}`);
 }
 }
 changeMonth();
}

// function getWeekNumber(date) {
// // Clone the date object to avoid modifying the original
// var clonedDate = new Date(date);
// clonedDate.setHours(0, 0, 0, 0);

// // Set to nearest Thursday: current date + 4 - current day number
// // Make Sunday's day number 7
// clonedDate.setDate(clonedDate.getDate() + 4 - (clonedDate.getDay() || 7));

// // Get first day of year
// var yearStart = new Date(clonedDate.getFullYear(), 0, 1);

// // Calculate full weeks to nearest Thursday
// var weekNumber = Math.ceil(((clonedDate - yearStart) / 86400000 + 1) / 7);

// return weekNumber;
// }

// var today = new Date();
// month = ("0" + (today.getMonth() + 1)).slice(-2);
// year = today.getFullYear();
// var day = ("0" + today.getDate()).slice(-2);
// var formattedDate = year + "-" + month + "-" + day;
// var currentWeek = getWeekNumber(today);

// function createAttendanceChart(dataSet, labels) {
// data = {
// labels: labels,
// datasets: dataSet,
// };
// // Create chart using the Chart.js library
// window["attendanceChart"] = {};
// if (document.getElementById("dailyAnalytic")) {
// const ctx = document.getElementById("dailyAnalytic").getContext("2d");
// attendanceChart = new Chart(ctx, {
// type: "bar",
// data: data,
// options: {
// responsive: true,
// onClick: (e, activeEls) => {
// let datasetIndex = activeEls[0].datasetIndex;
// let dataIndex = activeEls[0].index;
// let datasetLabel = e.chart.data.datasets[datasetIndex].label;
// let value = e.chart.data.datasets[datasetIndex].data[dataIndex];
// let label = e.chart.data.labels[dataIndex];
// var parms =
// "?department=" +
// datasetLabel +
// "&type=" +
// label.toLowerCase().replace(/\s/g, "_");
// var type = $("#type").val();
// const dateStr = $("#attendance_month").val();
// if (type == "weekly") {
// const [year, week] = dateStr.split("-W");
// parms = parms + "&week=" + week + "&year=" + year;
// } else if (type == "monthly") {
// const [year, month] = dateStr.split("-");
// parms = parms + "&month=" + month + "&year=" + year;
// } else if (type == "day") {
// parms = parms + "&attendance_date=" + dateStr;
// } else if (type == "date_range") {
// var start_date = dateStr;
// var end_date = $("#attendance_month2").val();
// parms =
// parms +
// "&attendance_date__gte=" +
// start_date +
// "&attendance_date__lte=" +
// end_date;
// }
// localStorage.removeItem("savedFilters");
// if (label == "On Time") {
// $.ajax({
// url: "/attendance/on-time-view" + parms,
// type: "GET",
// data: {
// input_type: type,
// },
// headers: {
// "X-Requested-With": "XMLHttpRequest",
// },
// success: (response) => {
// $("#back_button").removeClass("d-none");
// $("#dashboard").html(response);
// },
// error: (error) => {},
// });
// } else {
// window.location.href =
// "/attendance/late-come-early-out-view" + parms;
// }
// },
// },
// plugins: [
// {
// afterRender: (chart) => emptyChart(chart),
// },
// ],
// });
// }
// }


// function changeMonth() {
// let type = $("#type").val();
// let date = $("#attendance_month").val();
// let end_date = $("#attendance_month2").val();
// $.ajax({
// type: "GET",
// url: "/attendance/dashboard-attendance",
// dataType: "json",
// data: {
// date: date,
// type: type,
// end_date: end_date,
// },
// success: function (response) {
// attendanceChart.destroy();
// createAttendanceChart(response.dataSet, response.labels);
// },
// error: (error) => {},
// });
// }

// function changeView(element) {
// var dataType = $(element).val();
// if (dataType === "date_range") {
// $("#attendance_month").prop("type", "date");
// $("#day_input").after(
// '<input type="date" class="mb-2 float-end pointer oh-select ml-2" id="attendance_month2" style="width: 100px;color:#5e5c5c;" onchange="changeMonth(this)"/>'
// );
// $("#attendance_month").val(formattedDate);
// $("#attendance_month2").val(formattedDate);
// changeMonth();
// } else {
// $("#attendance_month2").remove();
// if (dataType === "weekly") {
// $("#attendance_month").prop("type", "week");
// if (currentWeek < 10) {
// $("#attendance_month").val(`${year}-W0${currentWeek}`);
// } else {
// $("#attendance_month").val(`${year}-W${currentWeek}`);
// }
// changeMonth();
// } else if (dataType === "day") {
// $("#attendance_month").prop("type", "date");
// $("#attendance_month").val(formattedDate);
// changeMonth();
// } else {
// $("#attendance_month").prop("type", "month");
// $("#attendance_month").val(`${year}-${month}`);
// changeMonth();
// }
// }
// }


document.addEventListener('DOMContentLoaded', () => {
 let pendingHoursCanvas = null;
 let isLoading = false;

 const monthNames = [
 "January", "February", "March", "April", "May", "June",
 "July", "August", "September", "October", "November", "December"
 ];

 const colors = ['#a5b4fc', '#fca5a5', '#fdba74', '#86efac', '#fbbf24', '#c084fc'];

 const currentDate = new Date();
 const currentMonthNumber = currentDate.getMonth();
 const currentMonth = monthNames[currentMonthNumber];
 const currentYear = currentDate.getFullYear();
 const currentYearMonth = currentDate.toISOString().slice(0, 7);

 const monthSelector = document.getElementById("hourAccountMonth");
 if (monthSelector) {
 monthSelector.value = currentYearMonth;
 }

 function pendingHourChart(year, month) {
 if (isLoading) return;

 const ctx = document.getElementById("pendingHoursCanvas");
 if (!ctx) return;

 isLoading = true;

 $.ajax({
 type: "GET",
 url: "/attendance/pending-hours",
 data: { month, year },
 cache: true,
 success: function (response) {
 if (pendingHoursCanvas) {
 pendingHoursCanvas.destroy();
 pendingHoursCanvas = null;
 }

 const datasets = response.data.datasets.map((dataset, index) => ({
 ...dataset,
 backgroundColor: colors[index % colors.length],
 borderRadius: 10,
 barPercentage: 0.8,
 categoryPercentage: 0.6
 }));

 pendingHoursCanvas = new Chart(ctx, {
 type: "bar",
 data: {
 ...response.data,
 datasets
 },
 options: {
 responsive: true,
 maintainAspectRatio: false,
 animation: {
 duration: 300
 },
 scales: {
 x: {
 ticks: { color: '#6b7280' },
 grid: { display: false }
 },
 y: {
 beginAtZero: true,
 ticks: {
 stepSize: 20,
 color: '#6b7280'
 },
 grid: { color: '#e5e7eb' }
 }
 },
 plugins: {
 legend: {
 position: 'bottom',
 labels: {
 usePointStyle: true,
 pointStyle: 'circle',
 font: { size: 12 },
 color: '#374151',
 padding: 15
 }
 },
 tooltip: {
 animation: {
 duration: 0
 }
 }
 },
 onClick: (e, activeEls) => {
 if (activeEls?.length) {
 const { datasetIndex, index: dataIndex } = activeEls[0];
 const datasetLabel = e.chart.data.datasets[datasetIndex].label;
 const label = e.chart.data.labels[dataIndex];

 const params = new URLSearchParams({
 year,
 month,
 department_name: label,
 [datasetLabel.toLowerCase() === "worked hours" ? "worked_hours__gte" : "pending_hours__gte"]: "1"
 });

 window.location.href = `/attendance/attendance-overtime-view?${params}`;
 }
 }
 },
 plugins: [{
 afterRender: () => emptyChart(pendingHoursCanvas)
 }]
 });

 isLoading = false;
 },
 error: () => {
 isLoading = false;
 }
 });
 }

 function dynamicMonth(element) {
 const value = element.val();
 if (!value || isLoading) return;

 const [year, monthStr] = value.split("-");
 const monthIndex = parseInt(monthStr) - 1;

 if (monthIndex >= 0 && monthIndex < 12) {
 pendingHourChart(parseInt(year), monthNames[monthIndex]);
 }
 }

 window.dynamicMonth = dynamicMonth;

 if (document.getElementById("pendingHoursCanvas")) {
 pendingHourChart(currentYear, currentMonth);
 }
});

// if (document.getElementById("pendingHoursCanvas")) {
// var chart = new Chart(document.getElementById("pendingHoursCanvas"), {});
// }
// window["pendingHoursCanvas"] = chart;
// function pendingHourChart(year, month) {
// $.ajax({
// type: "get",
// url: "/attendance/pending-hours",
// data: { month: month, year: year },
// success: function (response) {
// var ctx = document.getElementById("pendingHoursCanvas");
// if (ctx) {
// pendingHoursCanvas.destroy();
// pendingHoursCanvas = new Chart(ctx, {
// type: "bar", // Bar chart type
// data: response.data,
// options: {
// responsive: true,
// aspectRatio: false,
// indexAxis: "x",
// scales: {
// x: {
// stacked: true, // Stack the bars on the x-axis
// },
// y: {
// beginAtZero: true,
// stacked: true,
// },
// },
// onClick: (e, activeEls) => {
// let datasetIndex = activeEls[0].datasetIndex;
// let dataIndex = activeEls[0].index;
// let datasetLabel = e.chart.data.datasets[datasetIndex].label;
// let value = e.chart.data.datasets[datasetIndex].data[dataIndex];
// let label = e.chart.data.labels[dataIndex];
// parms =
// "?year=" +
// year +
// "&month=" +
// month +
// "&department_name=" +
// label +
// "&";
// if (datasetLabel.toLowerCase() == "worked hours") {
// parms = parms + "worked_hours__gte=1&";
// } else {
// parms = parms + "pending_hours__gte=1&";
// }
// window.location.href =
// "/attendance/attendance-overtime-view" + parms;
// },
// },
// plugins: [
// {
// afterRender: (chart) => {
// emptyChart(pendingHoursCanvas);
// },
// },
// ],
// });
// }
// },
// });
// }

// // Create a new Date object
// var currentDate = new Date();

// // Get the current month (returns a number, where January is 0 and December is 11)
// var currentMonthNumber = currentDate.getMonth();
// // Create an array of month names
// var monthNames = [
// "January",
// "February",
// "March",
// "April",
// "May",
// "June",
// "July",
// "August",
// "September",
// "October",
// "November",
// "December",
// ];

// // Get the current month name
// var currentMonth = monthNames[currentMonthNumber];

// var currentYearMonth = currentDate.toISOString().slice(0, 7);

// $("#hourAccountMonth").val(currentYearMonth);
// var currentYear = currentDate.getFullYear();
// pendingHourChart(currentYear, currentMonth);
// function dynamicMonth(element) {
// var value = element.val(); // Get the input value
// if (!value || !value.match(/^\d{4}-\d{2}$/)) {
// console.error("Invalid date format. Expected YYYY-MM, got:", value);
// return; // Exit if the value is invalid
// }
// var dateArray = value.split("-");
// var year = parseInt(dateArray[0], 10);
// var monthIndex = parseInt(dateArray[1], 10) - 1; // Convert to zero-based index
// if (monthIndex < 0 || monthIndex >= monthNames.length) {
// console.error("Invalid month number:", dateArray[1]);
// return;
// }
// pendingHourChart(year, monthNames[monthIndex]);
// }
