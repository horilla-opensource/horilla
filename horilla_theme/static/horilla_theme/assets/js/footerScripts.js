$(function () {
    $(document).tooltip({
        position: {
            my: "center top+8",
            at: "center bottom",
            collision: "flipfit"
        }
    });
});

Toast = Swal.mixin({
    toast: true,
    icon: "success",
    title: "General Title",
    animation: true,
    position: "top-right",
    showConfirmButton: false,
    timer: 3000,
    timerProgressBar: true,
    didOpen: (toast) => {
        toast.addEventListener("mouseenter", Swal.stopTimer);
        toast.addEventListener("mouseleave", Swal.resumeTimer);
    },
});

async function loadComponent(elementId, path) {
    try {
        const response = await fetch(path);
        const html = await response.text();
        document.getElementById(elementId).innerHTML = html;
    } catch (error) {
        console.error("Error loading component:", error);
    }
}

// Gender Chart

// document.addEventListener("DOMContentLoaded", () => {
//     const ctx = document.getElementById("genderChart").getContext("2d");

//     // Load image only once
//     const centerImage = new Image();
//     centerImage.src = "/static/horilla_theme/assets/img/icons/gender.svg";

//     new Chart(ctx, {
//         type: "doughnut",
//         data: {
//             labels: ["Male", "Female", "Others"],
//             datasets: [
//                 {
//                     data: [35, 55, 10],
//                     backgroundColor: ["#cfe9ff", "#ffc9de", "#e6ccff"],
//                     borderWidth: 0,
//                 },
//             ],
//         },
//         options: {
//             cutout: "70%",
//             responsive: true,
//             maintainAspectRatio: false,
//             plugins: {
//                 legend: {
//                     position: "bottom",
//                     labels: {
//                         usePointStyle: true,
//                         pointStyle: "circle",
//                         padding: 20,
//                         font: {
//                             size: 12,
//                         },
//                         color: "#000",
//                     },
//                 },
//             },
//         },
//         plugins: [
//             {
//                 id: "centerIcon",
//                 afterDraw(chart) {
//                     if (!centerImage.complete) return; // Wait till image is loaded
//                     const ctx = chart.ctx;
//                     const size = 70;
//                     ctx.drawImage(
//                         centerImage,
//                         chart.width / 2 - size / 2,
//                         chart.height / 2 - size / 2 - 20,
//                         size,
//                         size
//                     );
//                 },
//             },
//         ],
//     });
// });

// Department chart

// document.addEventListener("DOMContentLoaded", () => {
//     const ctx = document
//         .getElementById("departmentChart")
//         .getContext("2d");

//     const departmentLabels = [
//         "Sales Dept",
//         "IT Dept",
//         "DM Dept",
//         "SEO Dept",
//         "Odoo Dept",
//         "Horilla Dept",
//     ];

//     const departmentColors = [
//         "#facc15",
//         "#f87171",
//         "#ddd6fe",
//         "#a5b4fc",
//         "#93c5fd",
//         "#d1d5db",
//     ];

//     const departmentValues = [1000, 800, 900, 1100, 2000, 1070];

//     const visibility = Array(departmentLabels.length).fill(true);

//     const departmentChart = new Chart(ctx, {
//         type: "doughnut",
//         data: {
//             labels: departmentLabels,
//             datasets: [
//                 {
//                     data: departmentValues,
//                     backgroundColor: departmentColors,
//                     borderWidth: 0,
//                     borderRadius: 10,
//                     hoverOffset: 8,
//                 },
//             ],
//         },
//         options: {
//             cutout: "70%",
//             responsive: true,
//             maintainAspectRatio: false,
//             plugins: {
//                 legend: { display: false },
//                 tooltip: {
//                     backgroundColor: "#111827",
//                     bodyColor: "#f3f4f6",
//                     borderColor: "#e5e7eb",
//                     borderWidth: 1,
//                 },
//             },
//         },
//         plugins: [
//             {
//                 id: "centerText",
//                 afterDraw(chart) {
//                     const { width, height, ctx } = chart;
//                     ctx.save();

//                     const total =
//                         chart.data.datasets[0].data.reduce(
//                             (sum, val) => sum + val,
//                             0
//                         );

//                     ctx.font = "bold 22px sans-serif";
//                     ctx.fillStyle = "#374151";
//                     ctx.textAlign = "center";
//                     ctx.textBaseline = "middle";
//                     ctx.fillText(total, width / 2, height / 2 - 5);

//                     ctx.font = "15px sans-serif";
//                     ctx.fillStyle = "#9ca3af";
//                     ctx.fillText(
//                         "Total",
//                         width / 2,
//                         height / 2 + 20
//                     );

//                     ctx.restore();
//                 },
//             },
//         ],
//     });

//     // Make custom legend items clickable
//     const legendItems =
//         document.querySelectorAll("#chartLegend > div");

//     legendItems.forEach((item, index) => {
//         item.style.cursor = "pointer";

//         item.addEventListener("click", () => {
//             visibility[index] = !visibility[index];

//             // Update chart dataset
//             departmentChart.data.datasets[0].data =
//                 departmentValues.map((val, i) =>
//                     visibility[i] ? val : 0
//                 );

//             // Dim legend dot and strike-through label
//             const span = item.querySelector("span");
//             if (visibility[index]) {
//                 span.style.opacity = "1";
//                 item.style.textDecoration = "none";
//             } else {
//                 span.style.opacity = "0.4";
//                 item.style.textDecoration = "line-through";
//             }

//             departmentChart.update();
//         });
//     });
// });

// Onboarding Chart

// document.addEventListener("DOMContentLoaded", () => {
//     const ctx = document.getElementById("recruitmentChart").getContext("2d");

//     const labels = [
//         "Recruitment drive",
//         "Future force recruitment",
//         "Administrative assistant",
//     ];
//     const colors = ["#a5b4fc", "#fca5a5", "#fdba74"];
//     const dataValues = [35, 45, 38];
//     const visibility = [true, true, true];

//     const chart = new Chart(ctx, {
//         type: "bar",
//         data: {
//             labels: labels,
//             datasets: [
//                 {
//                     label: "Recruitment Count",
//                     data: dataValues,
//                     backgroundColor: colors,
//                     borderRadius: 20,
//                     barPercentage: 0.6,
//                     categoryPercentage: 0.6,
//                 },
//             ],
//         },
//         options: {
//             responsive: true,
//             maintainAspectRatio: false,
//             plugins: {
//                 legend: { display: false },
//                 tooltip: { enabled: true },
//             },
//             scales: {
//                 y: {
//                     beginAtZero: true,
//                     max: 100,
//                     ticks: { stepSize: 20 },
//                     grid: { drawBorder: false, color: "#e5e7eb" },
//                 },
//                 x: {
//                     ticks: { display: false },
//                     grid: { display: false },
//                     border: { display: true, color: "#d1d5db" },
//                 },
//             },
//         },
//     });

//     // Create clickable legend dynamically
//     const legendContainer = document.getElementById("recruitmentLegend");
//     labels.forEach((label, i) => {
//         const item = document.createElement("div");
//         item.className = "flex items-center gap-2 cursor-pointer";
//         item.innerHTML = `
//       <span class="w-4 h-4 rounded-full inline-block" style="background:${colors[i]}; transition: 0.3s;"></span>
//       <span>${label}</span>
//     `;
//         item.addEventListener("click", () => {
//             visibility[i] = !visibility[i];

//             // Update data & bar color
//             chart.data.datasets[0].data = dataValues.map((val, index) =>
//                 visibility[index] ? val : 0
//             );
//             chart.data.datasets[0].backgroundColor = colors.map(
//                 (color, index) => (visibility[index] ? color : "#e5e7eb")
//             );
//             chart.update();

//             // Update legend visuals
//             const dot = item.querySelector("span");
//             const text = item.querySelectorAll("span")[1];
//             dot.style.opacity = visibility[i] ? "1" : "0.4";
//             text.style.textDecoration = visibility[i] ? "none" : "line-through";
//         });

//         legendContainer.appendChild(item);
//     });
// });

// Recruitment Chart

// document.addEventListener("DOMContentLoaded", () => {
//     const ctx = document
//         .getElementById("recruitmentFlowChart")
//         .getContext("2d");

//     new Chart(ctx, {
//         type: "bar",
//         data: {
//             labels: [
//                 "Initial",
//                 "Applied",
//                 "Test",
//                 "Interview",
//                 "Cancelled",
//                 "Hired",
//             ],
//             datasets: [
//                 {
//                     label: "Recruitment Drive",
//                     data: [55, 35, 0, 0, 28, 90],
//                     backgroundColor: "#a5b4fc",
//                     borderRadius: 10,
//                     barPercentage: 0.8,
//                     categoryPercentage: 0.6,
//                 },
//                 {
//                     label: "Future Force Recruitment",
//                     data: [0, 15, 0, 0, 0, 65],
//                     backgroundColor: "#fca5a5",
//                     borderRadius: 10,
//                     barPercentage: 0.8,
//                     categoryPercentage: 0.6,
//                 },
//                 {
//                     label: "Administrative Assistant",
//                     data: [0, 0, 0, 0, 0, 15],
//                     backgroundColor: "#fdba74",
//                     borderRadius: 10,
//                     barPercentage: 0.8,
//                     categoryPercentage: 0.6,
//                 },
//             ],
//         },
//         options: {
//             responsive: true,
//             maintainAspectRatio: false,
//             scales: {
//                 y: {
//                     beginAtZero: true,
//                     ticks: {
//                         stepSize: 20,
//                         color: "#6b7280",
//                     },
//                     grid: {
//                         color: "#e5e7eb",
//                     },
//                 },
//                 x: {
//                     ticks: {
//                         color: "#6b7280",
//                     },
//                     grid: {
//                         display: false,
//                     },
//                 },
//             },
//             plugins: {
//                 legend: {
//                     position: "bottom",
//                     labels: {
//                         usePointStyle: true,
//                         pointStyle: "circle",
//                         font: {
//                             size: 12,
//                         },
//                         color: "#374151",
//                         padding: 15,
//                     },
//                 },
//                 tooltip: {
//                     enabled: true,
//                 },
//             },
//         },
//     });
// });


// document.addEventListener("DOMContentLoaded", () => {
//     const ctx = document.getElementById("hiredChart").getContext("2d");

//     const labels = [
//         "Recruitment drive",
//         "Future force recruitment",
//         "Administrative assistant",
//     ];
//     const colors = ["#a5b4fc", "#fca5a5", "#fdba74"];
//     const values = [35, 45, 38];
//     const visibility = [true, true, true];

//     const chart = new Chart(ctx, {
//         type: "bar",
//         data: {
//             labels: labels,
//             datasets: [
//                 {
//                     label: "Recruitment Count",
//                     data: values,
//                     backgroundColor: colors,
//                     borderRadius: 20,
//                     barPercentage: 0.6,
//                     categoryPercentage: 0.6,
//                 },
//             ],
//         },
//         options: {
//             responsive: true,
//             maintainAspectRatio: false,
//             plugins: {
//                 legend: { display: false },
//                 tooltip: { enabled: true },
//             },
//             scales: {
//                 y: {
//                     beginAtZero: true,
//                     max: 100,
//                     ticks: { stepSize: 20 },
//                     grid: { drawBorder: false, color: "#e5e7eb" },
//                 },
//                 x: {
//                     ticks: { display: false },
//                     grid: { display: false },
//                     border: { display: true, color: "#d1d5db" },
//                 },
//             },
//         },
//     });

//     // Toggle bars and strike text
//     const legendItems = document.querySelectorAll("#hiredLegend > div");
//     legendItems.forEach((item, i) => {
//         item.addEventListener("click", () => {
//             visibility[i] = !visibility[i];

//             // Update chart data
//             chart.data.datasets[0].data = values.map((val, index) =>
//                 visibility[index] ? val : 0
//             );
//             chart.data.datasets[0].backgroundColor = colors.map((col, index) =>
//                 visibility[index] ? col : "#e5e7eb"
//             );
//             chart.update();

//             // Update legend visuals
//             const dot = item.querySelectorAll("span")[0];
//             const text = item.querySelectorAll("span")[1];

//             dot.style.opacity = visibility[i] ? "1" : "0.4";
//             text.style.textDecoration = visibility[i] ? "none" : "line-through";
//         });
//     });
// });

function validateFile(element, fileTarget, reload = false) {
    var fileInput = document.getElementById(fileTarget);
    var filePath = fileInput.value;
    var allowedExtensions = /(\.xlsx|\.csv)$/i;

    if (!allowedExtensions.exec(filePath)) {
        Swal.fire({
            icon: "error",
            title: "Invalid File",
            text: "Please upload a valid XLSX file.",
            customClass: {
                popup: "file-xlsx-validation",
            },
        }).then((result) => {
            if (result.isConfirmed && reload) {
                $(".oh-modal--show").removeClass("oh-modal--show");
                window.location.reload();
            }
        });
        fileInput.value = "";
        return false;
    }
    $(this).closest("form").submit();
}

function initSidebarToggle() {
    // Reusable Sidebar Toggle
    document.querySelectorAll(".toggleSidemenu").forEach((button) => {
        button.addEventListener("click", () => {
            const sidebarId = button.getAttribute("data-sidebar");
            const sidebar = document.getElementById(sidebarId);
            if (sidebar) {
                sidebar.classList.toggle("active");
                document.body.classList.toggle("overflow-hidden");
            }
        });
    });

    document.querySelectorAll(".closeSidemenu").forEach((button) => {
        button.addEventListener("click", () => {
            const sidebarId = button.getAttribute("data-sidebar");
            const sidebar = document.getElementById(sidebarId);
            if (sidebar) {
                sidebar.classList.remove("active");
                document.body.classList.remove("overflow-hidden");
            }
        });
    });
}

function switchTab(e) {
    let parentContainerEl = e.target.closest(".oh-tabs");
    let tabElement = e.target.closest(".oh-tabs__tab");
    let targetSelector = e.target.dataset.target;
    let targetEl = parentContainerEl
        ? parentContainerEl.querySelector(targetSelector)
        : null;

    // Highlight active tabs
    if (tabElement && !tabElement.classList.contains("oh-tabs__tab--active")) {
        parentContainerEl
            .querySelectorAll(".oh-tabs__tab--active")
            .forEach(function (item) {
                item.classList.remove("oh-tabs__tab--active");
            });

        if (!tabElement.classList.contains("oh-tabs__new-tab")) {
            tabElement.classList.add("oh-tabs__tab--active");
        }
    }

    // Switch tabs
    if (targetEl && !targetEl.classList.contains("oh-tabs__content--active")) {
        parentContainerEl
            .querySelectorAll(".oh-tabs__content--active")
            .forEach(function (item) {
                item.classList.remove("oh-tabs__content--active");
            });
        targetEl.classList.add("oh-tabs__content--active");
    }
}

function toggleAccordion(btn) {

    //  * This function is intended to be called explicitly via `hx-on:click` in HTMX-rendered content,
    const panel = btn.nextElementSibling;
    const icon = btn.querySelector(".icon");
    const isOpen = panel.style.maxHeight && panel.style.maxHeight !== "0px";

    // Collapse all other panels
    document.querySelectorAll(".accordion-panel").forEach((p) => {
        p.style.maxHeight = null;
        const prevBtn = p.previousElementSibling;
        const prevIcon = prevBtn.querySelector(".icon");
        if (prevIcon) prevIcon.textContent = "+";
        prevBtn.classList.remove("bg-[#e54f38]", "text-white");
        prevBtn.classList.add("bg-[#fff5f1]", "text-[#e54f38]");
    });

    // Toggle current panel
    if (!isOpen) {
        panel.style.maxHeight = "500px";
        if (icon) icon.textContent = "−";
        // btn.classList.remove("bg-[#fff5f1]", "text-[#e54f38]");
        // btn.classList.add("bg-[#e54f38]", "text-white");
    } else {
        panel.style.maxHeight = null;
        if (icon) icon.textContent = "+";
        // btn.classList.remove("bg-[#e54f38]", "text-white");
        // btn.classList.add("bg-[#fff5f1]", "text-[#e54f38]");
    }
}

document.querySelectorAll('.accordion-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
        const panel = btn.nextElementSibling;
        const icon = btn.querySelector('.icon');
        const isOpen = panel.style.maxHeight && panel.style.maxHeight !== "0px";

        // Collapse all others (optional — comment this block if you want multiple open)
        document.querySelectorAll('.accordion-panel').forEach(p => {
            p.style.maxHeight = null;
            p.previousElementSibling.querySelector('.icon').textContent = '+';
            p.previousElementSibling.classList.remove("bg-[#e54f38]", "text-white");
            p.previousElementSibling.classList.add("bg-[#fff5f1]", "text-[#e54f38]");
        });

        // Toggle current
        if (!isOpen) {
            panel.style.maxHeight = panel.scrollHeight + 'px';
            icon.textContent = '-';
            // btn.classList.remove("bg-[#fff5f1]", "text-[#e54f38]");
            // btn.classList.add("bg-[#e54f38]", "text-white");
        } else {
            panel.style.maxHeight = null;
            icon.textContent = '+';
            // btn.classList.remove("bg-[#e54f38]", "text-white");
            // btn.classList.add("bg-[#fff5f1]", "text-[#e54f38]");
        }
    });
});

$(document).on("htmx:afterSettle", function (event) {
    // $(".dropdown-toggle").on("click", function () {
    //     const dropdownMenu = $(this).next(".dropdown-menu");
    //     const isOpen = dropdownMenu.is(":visible");

    //     $(".dropdown-menu").not(dropdownMenu).hide();

    //     if (isOpen) {
    //         dropdownMenu.hide();
    //     } else {
    //         dropdownMenu.show();
    //     }
    // });

    // method for sticky issue
    const $fixedTable = $('.fixed-table');
    if ($fixedTable.length === 0) return;

    const bulk_select_option = $fixedTable.data('bulk-select-option');
    if (bulk_select_option) {
        $('tr').each(function () {
            const $cells = $(this).find('th, td');
            if ($cells.length > 0) {
                $cells.eq(0).addClass('stickyleft');
                $cells.eq(1).addClass('stickyleft-second');
            }
        });
    } else {
        $('tr').each(function () {
            const $cells = $(this).find('th, td');
            if ($cells.length > 0) {
                $cells.eq(0).addClass('stickyleft');
            }
        });
    };

    if ($(".oh-permission-table--toggle").length > 0) {
        $(".oh-permission-table--toggle").each(function () {
            $(this).closest("tr").addClass("oh-permission-table--collapsed")
        });
    }
});

$(".oh-password-input--toggle").on("click", function (e) {
    e.preventDefault();

    const $toggle = $(this);
    const $passwordInput = $toggle.siblings(".oh-input--password");
    const $showIcon = $toggle.find(".oh-password-input__show-icon");
    const $hideIcon = $toggle.find(".oh-password-input__hide-icon");

    if ($passwordInput.attr("type") === "password") {
        $passwordInput.attr("type", "text");
        $showIcon.addClass("hidden");
        $hideIcon.removeClass("hidden");
    } else {
        $passwordInput.attr("type", "password");
        $showIcon.removeClass("hidden");
        $hideIcon.addClass("hidden");
    }
});

$(".oh-modal__close").on("click", function(){
    $(this).closest(".oh-modal--show").removeClass("oh-modal--show")
})

$(document).on("click", ".oh-accordion-header", function(event) {
    event.stopImmediatePropagation();
    $(this).closest(".oh-accordion").toggleClass("oh-accordion--show");
});
