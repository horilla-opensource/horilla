// time-runner
function secondsToDuration(seconds) {
    var hours = Math.floor(seconds / 3600);
    var minutes = Math.floor((seconds % 3600) / 60);
    var remainingSeconds = Math.floor(seconds % 60);

    // add leading zeros if necessary
    var formattedHours = (hours < 10) ? "0" + hours : hours;
    var formattedMinutes = (minutes < 10) ? "0" + minutes : minutes;
    var formattedSeconds = (remainingSeconds < 10) ? "0" + remainingSeconds : remainingSeconds;

    return formattedHours + ":" + formattedMinutes + ":" + formattedSeconds;
}
// accessing initial worked hours from the user
$(".time-runner").not("title").html(secondsToDuration(at_work_seconds));
$("title.time-runner").html("{{white_label_company_name}} | " + secondsToDuration(at_work_seconds));
setInterval(() => {
    if (run) {
        at_work_seconds = at_work_seconds + 1
        $("div.time-runner").html(secondsToDuration(at_work_seconds));
        $("title").html("{{white_label_company_name}} | " + secondsToDuration(at_work_seconds));
    }
}, 1000);

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