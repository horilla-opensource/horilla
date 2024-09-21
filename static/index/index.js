var confirmModal = {
    ar: "تأكيد",
    de: "Bestätigen",
    es: "Confirmar",
    en: "Confirm",
    fr: "Confirmer",
};

var cancelModal = {
    ar: "إلغاء",
    de: "Abbrechen",
    es: "Cancelar",
    en: "Cancel",
    fr: "Annuler",
};

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== "") {
        const cookies = document.cookie.split(";");
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) === name + "=") {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function addToSelectedId(newIds) {
    ids = JSON.parse(
        $("#selectedInstances").attr("data-ids") || "[]"
    );

    ids = [...ids, ...newIds.map(String)]
    ids = Array.from(new Set(ids));
    $("#selectedInstances").attr("data-ids", JSON.stringify(ids))
}

function attendanceDateChange(selectElement) {
    var selectedDate = selectElement.val()
    let parentForm = selectElement.parents().closest("form")
    var shiftId = parentForm.find("[name=shift_id]").val()

    $.ajax({
        type: "post",
        url: "/attendance/update-date-details",
        data: {
            csrfmiddlewaretoken: getCookie("csrftoken"),
            "attendance_date": selectedDate,
            "shift_id": shiftId
        },
        success: function (response) {
            parentForm.find("[name=minimum_hour]").val(response.minimum_hour)

        }
    });
}

function getAssignedLeave(employeeElement) {
    var employeeId = employeeElement.val()
    $.ajax({
        type: "get",
        url: "/payroll/get-assigned-leaves",
        data: { "employeeId": employeeId },
        dataType: "json",
        success: function (response) {
            let rows = ""
            for (let index = 0; index < response.length; index++) {
                const element = response[index];
                rows = rows + `<tr class="toggle-highlight"><td>${element.leave_type_id__name
                    }</td><td>${element.available_days}</td><td>${element.carryforward_days}</td></tr>`
            }
            $("#availableTableBody").html($(rows))
            let newLeaves = ""
            for (let index = 0; index < response.length; index++) {
                const leave = response[index];
                newLeaves = newLeaves + `<option value="${leave.leave_type_id__id
                    }">${leave.leave_type_id__name}</option>`
            }
            $('#id_leave_type_id').html(newLeaves)
            removeHighlight()
        }
    });
}

function selectSelected(viewId) {
    ids = JSON.parse(
        $("#selectedInstances").attr("data-ids") || "[]"
    );
    $.each(ids, function (indexInArray, valueOfElement) {
        $(`${viewId} .oh-sticky-table__tbody .list-table-row[value=${valueOfElement}]`).prop("checked", true).change()
    });
    $(`${viewId} .oh-sticky-table__tbody .list-table-row`).change(function (
        e
    ) {
        id = $(this).val()
        ids = JSON.parse(
            $("#selectedInstances").attr("data-ids") || "[]"
        );
        ids = Array.from(new Set(ids));
        let index = ids.indexOf(id);
        if (!ids.includes(id)) {
            ids.push(id);
        } else {
            if (!$(this).is(":checked")) {
                ids.splice(index, 1);
            }
        }
        $("#selectedInstances").attr("data-ids", JSON.stringify(ids));
    }
    );
    reloadSelectedCount($('#count_{{view_id|safe}}'));

}

// Switch General Tab
function switchGeneralTab(e) {
    // DO NOT USE GENERAL TABS TWICE ON A SINGLE PAGE.
    e.preventDefault();
    e.stopPropagation();
    let clickedEl = e.target.closest(".oh-general__tab-link");
    let targetSelector = clickedEl.dataset.target;

    // Remove active class from all the tabs
    $(".oh-general__tab-link").removeClass("oh-general__tab-link--active");
    // Remove active class to the clicked tab
    clickedEl.classList.add("oh-general__tab-link--active");

    // Hide all the general tabs
    $(".oh-general__tab-target").addClass("d-none");
    // Show the tab with the chosen target
    $(`.oh-general__tab-target${targetSelector}`).removeClass("d-none");
}

function toggleReimbursmentType(element) {
    if (element.val() == 'reimbursement') {
        $('#objectCreateModalTarget [name=attachment]').parent().show()
        $('#objectCreateModalTarget [name=attachment]').attr("required", true)
        $('#objectCreateModalTarget [name=leave_type_id]').parent().hide().attr("required", false)
        $('#objectCreateModalTarget [name=cfd_to_encash]').parent().hide().attr("required", false)
        $('#objectCreateModalTarget [name=ad_to_encash]').parent().hide().attr("required", false)
        $('#objectCreateModalTarget [name=amount]').parent().show().attr("required", true)
        $('#objectCreateModalTarget #availableTable').hide().attr("required", false)
        $('#objectCreateModalTarget [name=bonus_to_encash]').parent().hide().attr("required", false)

    } else if (element.val() == 'leave_encashment') {
        $('#objectCreateModalTarget [name=attachment]').parent().hide()
        $('#objectCreateModalTarget [name=attachment]').attr("required", false)
        $('#objectCreateModalTarget [name=leave_type_id]').parent().show().attr("required", true)
        $('#objectCreateModalTarget [name=cfd_to_encash]').parent().show().attr("required", true)
        $('#objectCreateModalTarget [name=ad_to_encash]').parent().show().attr("required", true)
        $('#objectCreateModalTarget [name=amount]').parent().hide().attr("required", false)
        $('#objectCreateModalTarget #availableTable').show().attr("required", true)
        $('#objectCreateModalTarget [name=bonus_to_encash]').parent().hide().attr("required", false)

    } else if (element.val() == 'bonus_encashment') {
        $('#objectCreateModalTarget [name=attachment]').parent().hide()
        $('#objectCreateModalTarget [name=attachment]').attr("required", false)
        $('#objectCreateModalTarget [name=leave_type_id]').parent().hide().attr("required", false)
        $('#objectCreateModalTarget [name=cfd_to_encash]').parent().hide().attr("required", false)
        $('#objectCreateModalTarget [name=ad_to_encash]').parent().hide().attr("required", false)
        $('#objectCreateModalTarget [name=amount]').parent().hide().attr("required", false)
        $('#objectCreateModalTarget #availableTable').hide().attr("required", false)
        $('#objectCreateModalTarget [name=bonus_to_encash]').parent().show().attr("required", true)


    }
}

function reloadSelectedCount(targetElement) {
    count = JSON.parse($("#selectedInstances").attr("data-ids") || "[]").length
    id = targetElement.attr("id")
    if (id) {
        id = id.split("count_")[1]
    }
    if (count) {
        targetElement.html(count)
        targetElement.parent().removeClass("d-none");
        $(`#unselect_${id}, #export_${id}, #bulk_udate_${id}`).removeClass("d-none");


    } else {
        targetElement.parent().addClass("d-none")
        $(`#unselect_${id}, #export_${id}, #bulk_udate_${id}`).addClass("d-none")

    }
}



function removeHighlight() {
    setTimeout(function () {
        $(".toggle-highlight").removeClass("toggle-highlight")
    }, 200);
}

function removeId(element) {
    id = element.val();
    viewId = element.attr("data-view-id")
    ids = JSON.parse($("#selectedInstances").attr("data-ids") || "[]")
    let elementToRemove = 5;
    if (ids[ids.length - 1] === id) {
        ids.pop();
    }
    ids = JSON.stringify(ids)
    $("#selectedInstances").attr("data-ids", ids);

}

function bulkStageUpdate(canIds, stageId, preStageId) {
    $.ajax({
        type: "POST",
        url: "/recruitment/candidate-stage-change?bulk=True",
        data: {
            csrfmiddlewaretoken: getCookie("csrftoken"),
            canIds: JSON.stringify(canIds),
            stageId: stageId,
        },
        success: function (response, textStatus, jqXHR) {
            if (jqXHR.status === 200) {
                $(`#stageLoad` + preStageId).click();
                $(`#stageLoad` + stageId).click();
            }
            if (response.message) {
                Swal.fire({
                    title: response.message,
                    text: `Total vacancy is ${response.vacancy}.`, // Using template literals
                    icon: 'info',
                    confirmButtonText: 'Ok',
                });
            }
        },
    });
}

function updateCandStage(canIds, stageId, preStageId) {
    $.ajax({
        type: "POST",
        url: "/recruitment/candidate-stage-change?bulk=false",
        data: {
            csrfmiddlewaretoken: getCookie("csrftoken"),
            canIds: canIds,
            stageId: stageId,
        },
        success: function (response, textStatus, jqXHR) {
            if (jqXHR.status === 200) {
                $(`#stageLoad` + preStageId).click();
                $(`#stageLoad` + stageId).click();
            }
            if (response.message) {
                Swal.fire({
                    title: response.message,
                    text: `Total vacancy is ${response.vacancy}.`, // Using template literals
                    icon: 'info',
                    confirmButtonText: 'Ok',
                });
            }
        },
    });
}

function checkSequence(element) {
    var preStageId = $(element).data("stage_id")
    var canIds = $(element).data("cand_id")
    var stageOrderJson = $(element).attr("data-stage_order")
    var stageId = $(element).val()

    var parsedStageOrder = JSON.parse(stageOrderJson);

    var stage = parsedStageOrder.find(stage => stage.id == stageId);
    var preStage = parsedStageOrder.find(stage => stage.id == preStageId);
    var stageOrder = parsedStageOrder.map(stage => stage.id);

    if (stageOrder.indexOf(parseInt(stageId)) != stageOrder.indexOf(parseInt(preStageId)) + 1 && stage.type != "cancelled") {
        Swal.fire({
            title: "Confirm",
            text: `Are you sure to change the candidate from ${preStage.stage} stage to ${stage.stage} stage`,
            icon: 'info',
            showCancelButton: true,
            confirmButtonColor: "#008000",
            cancelButtonColor: "#d33",
            confirmButtonText: "Confirm",
        }).then(function (result) {
            if (result.isConfirmed) {
                updateCandStage(canIds, stageId, preStageId)
            }
        });
    }
    else {
        updateCandStage(canIds, stageId, preStageId)
    }
}

var originalConfirm = window.confirm;
// Override the default confirm function with SweetAlert
window.confirm = function (message) {
    var event = window.event || {};
    event.preventDefault();
    var languageCode = null;
    languageCode = $("#main-section-data").attr("data-lang");
    var confirm =
        confirmModal[languageCode] ||
        ((languageCode = "en"), confirmModal[languageCode]);
    var cancel =
        cancelModal[languageCode] ||
        ((languageCode = "en"), cancelModal[languageCode]);
    // Add event listener to "Confirm" button
    $("#confirmModalBody").html(message);
    var submit = false;
    Swal.fire({
        text: message,
        icon: "question",
        showCancelButton: true,
        confirmButtonColor: "#008000",
        cancelButtonColor: "#d33",
        confirmButtonText: confirm,
        cancelButtonText: cancel,
    }).then((result) => {
        if (result.isConfirmed) {
            if (event.target.tagName.toLowerCase() === "form") {
                if (event.target["htmx-internal-data"]) {
                    var path = event.target["htmx-internal-data"].path;
                    var verb = event.target["htmx-internal-data"].verb;
                    var hxTarget = $(event.target).attr("hx-target");
                    if (verb === "post") {
                        htmx.ajax("POST", path, hxTarget);
                    } else {
                        htmx.ajax("GET", path, hxTarget);
                    }
                } else {
                    event.target.submit();
                }
            } else if (event.target.tagName.toLowerCase() === "a") {
                if (event.target.href) {
                    window.location.href = event.target.href;
                } else {
                    var path = event.target["htmx-internal-data"].path;
                    var verb = event.target["htmx-internal-data"].verb;
                    var hxTarget = $(event.target).attr("hx-target");
                    if (verb === "post") {
                        // hx.post(path)
                        htmx.ajax("POST", path, hxTarget);
                    } else {
                        htmx.ajax("GET", path, hxTarget);
                    }
                }
            } else {
                var path = event.target["htmx-internal-data"].path;
                var verb = event.target["htmx-internal-data"].verb;
                var hxTarget = $(event.target).attr("hx-target");
                if (verb === "post") {
                    htmx.ajax("POST", path, hxTarget);
                } else {
                    htmx.ajax("GET", path, hxTarget);
                }
            }
        } else {
        }
    });
};

setTimeout(() => { $("[name='search']").focus() }, 100);

$("#close").attr(
    "class",
    "oh-activity-sidebar__header-icon me-2 oh-activity-sidebar__close md hydrated"
);

$('body').on('click', '.select2-search__field', function (e) {
    //When click on Select2 fields in filter form,Auto close issue
    e.stopPropagation();
});

var nav = $("section.oh-wrapper.oh-main__topbar");
nav.after(
    $(
        `
  <div id="filterTagContainerSectionNav" class="oh-titlebar-container__filters mb-2 mt-0 oh-wrapper"></div>
  `
    )
);

$(document).on("htmx:beforeRequest", function (event, data) {
    var response = event.detail.xhr.response;
    var target = $(event.detail.elt.getAttribute("hx-target"));
    var avoid_target = ["BiometricDeviceTestFormTarget", "reloadMessages", "infinite"];
    if (!target.closest("form").length && avoid_target.indexOf(target.attr("id")) === -1) {
        target.html(`<div class="animated-background"></div>`);
    }
});

$(document).on('keydown', function (event) {
    // Check if the cursor is not focused on an input field
    var isInputFocused = $(document.activeElement).is('input, textarea, select');

    if (event.keyCode === 27) {
        // Key code 27 for Esc in keypad
        $('.oh-modal--show').removeClass('oh-modal--show');
        $('.oh-activity-sidebar--show').removeClass('oh-activity-sidebar--show')
    }

    if (event.keyCode === 46) {
        // Key code 46 for delete in keypad
        // If there have any objectDetailsModal with oh-modal--show
        // take delete button inside that else take the delete button from navbar Actions
        if (!isInputFocused) {
            var $modal = $('.oh-modal--show');
            var $deleteButton = $modal.length ? $modal.find('[data-action="delete"]') : $('.oh-dropdown').find('[data-action="delete"]');
            if ($deleteButton.length) {
                $deleteButton.click();
                $deleteButton[0].click();
            }
        }
    }
    else if (event.keyCode === 107) { // Key code for the + key on the numeric keypad
        if (!isInputFocused) {
            // Click the create option from navbar of current page
            $('[data-action="create"]').click();
        }
    }
    else if (event.keyCode === 39) { // Key code for the right arrow key
        if (!isInputFocused) {
            var $modal = $('.oh-modal--show');
            var $nextButton = $modal.length ? $modal.find('[data-action="next"]') : $('[data-action="next"]');  // Click on the next button in detail view modal
            if ($nextButton.length) {
                $nextButton[0].click()
            }
        }
    }
    else if (event.keyCode === 37) { // Key code for the left arrow key
        if (!isInputFocused) {
            // Click on the previous button in detail view modal
            var $modal = $('.oh-modal--show');
            var $previousButton = $modal.length ? $modal.find('[data-action="previous"]') : $('[data-action="previous"]');
            if ($previousButton.length) {
                $previousButton[0].click();

            }
        }
    }
});
function handleDownloadAndRefresh(event, url) {
    // Use in import_popup.html file
    event.preventDefault();

    // Create a temporary hidden iframe to trigger the download
    const iframe = document.createElement('iframe');
    iframe.style.display = 'none';
    iframe.src = url;
    document.body.appendChild(iframe);

    // Refresh the page after a short delay
    setTimeout(function () {
        document.body.removeChild(iframe);  // Clean up the iframe
        window.location.reload();  // Refresh the page
    }, 500);  // Adjust the delay as needed
}
