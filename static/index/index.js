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
                cookieValue = decodeURIComponent(
                    cookie.substring(name.length + 1)
                );
                break;
            }
        }
    }
    return cookieValue;
}

function handleSidebarToggle() {
    // Delay the execution slightly to allow existing toggle logic to finish
    setTimeout(() => {
        const isOpen = !$('.oh-wrapper-main').hasClass('oh-wrapper-main--closed');
        localStorage.setItem('sidebarOpen', isOpen);
    }, 50);
}

function addToSelectedId(newIds, storeKey) {
    ids = JSON.parse($(`#${storeKey}`).attr("data-ids") || "[]");

    ids = [...ids, ...newIds.map(String)];
    ids = Array.from(new Set(ids));
    $(`#${storeKey}`).attr("data-ids", JSON.stringify(ids));
}

function togglePublicComments() {
    if ($('#id_disable_comments').is(':checked')) {
        $('#id_public_comments').prop('checked', false);
        $('#id_public_comments_parent_div').hide();
    } else {
        $('#id_public_comments_parent_div').show();
    }
}

function attendanceDateChange(selectElement) {
    var selectedDate = selectElement.val();
    let parentForm = selectElement.parents().closest("form");
    var shiftId = parentForm.find("[name=shift_id]").val();

    $.ajax({
        type: "post",
        url: "/attendance/update-date-details",
        data: {
            csrfmiddlewaretoken: getCookie("csrftoken"),
            attendance_date: selectedDate,
            shift_id: shiftId,
        },
        success: function (response) {
            parentForm.find("[name=minimum_hour]").val(response.minimum_hour);
        },
    });
}

function getAssignedLeave(employeeElement) {
    var employeeId = employeeElement.val();
    $.ajax({
        type: "get",
        url: "/payroll/get-assigned-leaves",
        data: { employeeId: employeeId },
        dataType: "json",
        success: function (response) {
            let rows = "";
            for (let index = 0; index < response.length; index++) {
                const element = response[index];
                rows =
                    rows +
                    `<tr class="toggle-highlight"><td>${element.leave_type_id__name}</td><td>${element.available_days}</td><td>${element.carryforward_days}</td></tr>`;
            }
            $("#availableTableBody").html($(rows));
            let newLeaves = "";
            for (let index = 0; index < response.length; index++) {
                const leave = response[index];
                newLeaves =
                    newLeaves +
                    `<option value="${leave.leave_type_id__id}">${leave.leave_type_id__name}</option>`;
            }
            $("#id_leave_type_id").html(newLeaves);
            removeHighlight();
        },
    });
}
function selectSelected(viewId, storeKey = "selectedInstances") {
    ids = JSON.parse($(`#${storeKey}`).attr("data-ids") || "[]");
    $.each(ids, function (indexInArray, valueOfElement) {
        $(
            `${viewId} .oh-sticky-table__tbody .list-table-row[value=${valueOfElement}]`
        )
            .prop("checked", true)
            .change();
        $(`${viewId} tbody .list-table-row[value=${valueOfElement}]`)
            .prop("checked", true)
            .change();
    });
    $(
        `${viewId} .oh-sticky-table__tbody .list-table-row,${viewId} tbody .list-table-row`
    ).change(function (e) {
        id = $(this).val();
        ids = JSON.parse($(`#${storeKey}`).attr("data-ids") || "[]");
        ids = Array.from(new Set(ids));
        let index = ids.indexOf(id);
        if (!ids.includes(id)) {
            ids.push(id);
        } else {
            if (!$(this).is(":checked")) {
                ids.splice(index, 1);
            }
        }
        $(`#${storeKey}`).attr("data-ids", JSON.stringify(ids));
    });
    if (viewId) {
        reloadSelectedCount($(`#count_${viewId}`), storeKey);
    }
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
    if (element.val() == "reimbursement") {
        $("#objectCreateModalTarget [name=attachment]").parent().show();
        $("#objectCreateModalTarget [name=attachment]").attr("required", true);
        $("#objectCreateModalTarget [name=leave_type_id]")
            .parent()
            .hide()
            .attr("required", false);
        $("#objectCreateModalTarget [name=cfd_to_encash]")
            .parent()
            .hide()
            .attr("required", false);
        $("#objectCreateModalTarget [name=ad_to_encash]")
            .parent()
            .hide()
            .attr("required", false);
        $("#objectCreateModalTarget [name=amount]")
            .parent()
            .show()
            .attr("required", true);
        $("#objectCreateModalTarget #availableTable")
            .hide()
            .attr("required", false);
        $("#objectCreateModalTarget [name=bonus_to_encash]")
            .parent()
            .hide()
            .attr("required", false);
    } else if (element.val() == "leave_encashment") {
        $("#objectCreateModalTarget [name=attachment]").parent().hide();
        $("#objectCreateModalTarget [name=attachment]").attr("required", false);
        $("#objectCreateModalTarget [name=leave_type_id]")
            .parent()
            .show()
            .attr("required", true);
        $("#objectCreateModalTarget [name=cfd_to_encash]")
            .parent()
            .show()
            .attr("required", true);
        $("#objectCreateModalTarget [name=ad_to_encash]")
            .parent()
            .show()
            .attr("required", true);
        $("#objectCreateModalTarget [name=amount]")
            .parent()
            .hide()
            .attr("required", false);
        $("#objectCreateModalTarget #availableTable")
            .show()
            .attr("required", true);
        $("#objectCreateModalTarget [name=bonus_to_encash]")
            .parent()
            .hide()
            .attr("required", false);
        // #819
        $("#objectCreateModalTarget [name=employee_id]").trigger("change");
    } else if (element.val() == "bonus_encashment") {
        $("#objectCreateModalTarget [name=attachment]").parent().hide();
        $("#objectCreateModalTarget [name=attachment]").attr("required", false);
        $("#objectCreateModalTarget [name=leave_type_id]")
            .parent()
            .hide()
            .attr("required", false);
        $("#objectCreateModalTarget [name=cfd_to_encash]")
            .parent()
            .hide()
            .attr("required", false);
        $("#objectCreateModalTarget [name=ad_to_encash]")
            .parent()
            .hide()
            .attr("required", false);
        $("#objectCreateModalTarget [name=amount]")
            .parent()
            .hide()
            .attr("required", false);
        $("#objectCreateModalTarget #availableTable")
            .hide()
            .attr("required", false);
        $("#objectCreateModalTarget [name=bonus_to_encash]")
            .parent()
            .show()
            .attr("required", true);
    }
}

function reloadSelectedCount(targetElement, storeKey = "selectedInstances") {
    var count = JSON.parse($(`#${storeKey}`).attr("data-ids") || "[]").length;
    id = targetElement.attr("id");
    if (id) {
        id = id.split("count_")[1];
    }
    if (count) {
        targetElement.html(count);
        targetElement.parent().removeClass("d-none");
        $(`#unselect_${id}, #export_${id}, #bulk_udate_${id}`).removeClass(
            "d-none"
        );
    } else {
        targetElement.parent().addClass("d-none");
        $(`#unselect_${id}, #export_${id}, #bulk_udate_${id}`).addClass(
            "d-none"
        );
    }
}

function removeHighlight() {
    setTimeout(function () {
        $(".toggle-highlight").removeClass("toggle-highlight");
    }, 200);
}

function removeId(element, storeKey = "selectedInstances") {
    id = element.val();
    viewId = element.attr("data-view-id");
    ids = JSON.parse($(`#${storeKey}`).attr("data-ids") || "[]");
    let elementToRemove = 5;
    if (ids[ids.length - 1] === id) {
        ids.pop();
    }
    ids = JSON.stringify(ids);
    $(`#${storeKey}`).attr("data-ids", ids);
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
                    icon: "info",
                    confirmButtonText: "Ok",
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
                    icon: "info",
                    confirmButtonText: "Ok",
                });
            }
        },
    });
}

function checkSequence(element) {
    var preStageId = $(element).data("stage_id");
    var canIds = $(element).data("cand_id");
    var stageOrderJson = $(element).attr("data-stage_order");
    var stageId = $(element).val();

    var parsedStageOrder = JSON.parse(stageOrderJson);

    var stage = parsedStageOrder.find((stage) => stage.id == stageId);
    var preStage = parsedStageOrder.find((stage) => stage.id == preStageId);
    var stageOrder = parsedStageOrder.map((stage) => stage.id);

    if (
        stageOrder.indexOf(parseInt(stageId)) !=
        stageOrder.indexOf(parseInt(preStageId)) + 1 &&
        stage.type != "cancelled"
    ) {
        Swal.fire({
            title: "Confirm",
            text: `Are you sure to change the candidate from ${preStage.stage} stage to ${stage.stage} stage`,
            icon: "info",
            showCancelButton: true,
            confirmButtonColor: "#008000",
            cancelButtonColor: "#d33",
            confirmButtonText: "Confirm",
        }).then(function (result) {
            if (result.isConfirmed) {
                updateCandStage(canIds, stageId, preStageId);
            }
        });
    } else {
        updateCandStage(canIds, stageId, preStageId);
    }
}

function reloadMessage(e) {
    $("#reloadMessagesButton").click();
}

function htmxLoadIndicator(e) {
    var target = $(e).attr("hx-target");
    var table = $(target).find("table");
    var card = $(target).find(".oh-card__body");
    var kanban = $(target).find(".oh-kanban-card");

    if (table.length) {
        table.addClass("is-loading");
        table.find("th, td").empty();
    }
    if (card.length) {
        card.addClass("is-loading");
    }
    if (kanban.length) {
        kanban.addClass("is-loading");
    }
    if (!table.length && !card.length && !kanban.length) {
        $(target).html(`<div class="animated-background"></div>`);
    }
}

function ajaxWithResponseHandler(event) {
    $(event.target).each(function () {
        $.each(this.attributes, function () {
            if (this.specified && this.name === "hx-on-htmx-after-request") {
                eval(this.value);
            }
        });
    });
}

function handleHtmxTarget(event, path, verb) {
    var targetElement;
    var hxTarget = $(event.target).attr("hx-target");
    if (hxTarget) {
        if (hxTarget === "this") {
            targetElement = $(event.target);
        } else if (hxTarget.startsWith("closest ")) {
            var selector = hxTarget.replace("closest ", "").trim();
            targetElement = $(event.target).closest(selector);
        } else if (hxTarget.startsWith("find ")) {
            var selector = hxTarget.replace("find ", "").trim();
            targetElement = $(event.target).find(selector).first();
        } else if (hxTarget === "next") {
            targetElement = $(event.target).next();
        } else if (hxTarget.startsWith("next ")) {
            var selector = hxTarget.replace("next ", "").trim();
            targetElement = $(event.target).nextAll(selector).first();
        } else if (hxTarget === "previous") {
            targetElement = $(event.target).prev();
        } else if (hxTarget.startsWith("previous ")) {
            var selector = hxTarget.replace("previous ", "").trim();
            targetElement = $(event.target).prevAll(selector).first();
        } else {
            targetElement = $(hxTarget);
        }
        hxTarget = targetElement.length ? targetElement[0] : null;
    } else if (path && verb) {
        hxTarget = event.target;
    }
    return hxTarget;
}

function hxConfirm(element, messageText) {
    Swal.fire({
        html: messageText,
        icon: "question",
        showCancelButton: true,
        confirmButtonColor: "#008000",
        cancelButtonColor: "#d33",
        confirmButtonText: "Confirm",
        cancelButtonText: "Cancel",
        reverseButtons: true,
    }).then((result) => {
        if (result.isConfirmed) {
            htmx.trigger(element, 'confirmed');
        }
        else {
            element.checked = false
            return false
        }

    });
}

function handleDownloadAndRefresh(event, url) {
    // Use in import_popup.html file
    event.preventDefault();

    // Create a temporary hidden iframe to trigger the download
    const iframe = document.createElement("iframe");
    iframe.style.display = "none";
    iframe.src = url;
    document.body.appendChild(iframe);

    // Refresh the page after a short delay
    setTimeout(function () {
        document.body.removeChild(iframe); // Clean up the iframe
        window.location.reload(); // Refresh the page
    }, 500); // Adjust the delay as needed
}

function toggleCommentButton(e) {
    const $button = $(e).closest("form").find("#commentButton");
    $button.toggle($(e).val().trim() !== "");
}

function updateUserPanelCount(e) {
    var count = $(e)
        .closest(".oh-sticky-table__tr")
        .find(".oh-user-panel").length;
    setTimeout(() => {
        var $permissionCountSpan = $(e)
            .closest(".oh-permission-table--toggle")
            .parent()
            .find(".oh-permission-count");
        var currentText = $permissionCountSpan.text();

        var firstSpaceIndex = currentText.indexOf(" ");
        var textAfterNumber = currentText.slice(firstSpaceIndex + 1);
        var newText = count + " " + textAfterNumber;

        $permissionCountSpan.text(newText);
    }, 100);
}

function enlargeImage(src, $element) {
    $(".enlargeImageContainer").empty();
    var enlargeImageContainer = $element
        .parents()
        .closest("li")
        .find(".enlargeImageContainer");
    enlargeImageContainer.empty();
    style =
        "width:100%; height:90%; box-shadow: 0 10px 10px 0 rgba(0, 0, 0, 0.2), 0 6px 20px 0 rgba(0, 0, 0, 0.2); background:white";
    var enlargedImage = $("<iframe>").attr({ src: src, style: style });
    var name = $("<span>").text(src.split("/").pop().replace(/_/g, " "));
    enlargeImageContainer.append(enlargedImage);
    enlargeImageContainer.append(name);
    setTimeout(function () {
        enlargeImageContainer.show();

        const iframe = document.querySelector("iframe").contentWindow;
        var iframe_document = iframe.document;
        iframe_image = iframe_document.getElementsByTagName("img")[0];
        $(iframe_image).attr("style", "width:100%; height:100%;");
    }, 100);
}

function hideEnlargeImage() {
    var enlargeImageContainer = $(".enlargeImageContainer");
    enlargeImageContainer.empty();
}

function submitForm(elem) {
    $(elem).siblings(".add_more_submit").click();
}

function show_answer(element) {
    const $parentItem = $(element).closest(".oh-faq__item");
    const isShown = $parentItem.hasClass("oh-faq__item--show");

    $(".oh-faq__item--show").removeClass("oh-faq__item--show");

    if (!isShown) {
        $parentItem.addClass("oh-faq__item--show");
    }
}

var originalConfirm = window.confirm;
// Override the default confirm function with SweetAlert
window.confirm = function (message) {
    var event = window.event || {};
    event.preventDefault();
    var languageCode = $("#main-section-data").attr("data-lang") || "en";
    var confirm = confirmModal[languageCode];
    var cancel = cancelModal[languageCode];

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
            var path = event.target["htmx-internal-data"]?.path;
            var verb = event.target["htmx-internal-data"]?.verb;
            var hxTarget = handleHtmxTarget(event, path, verb);
            var hxVals = $(event.target).attr("hx-vals")
                ? JSON.parse($(event.target).attr("hx-vals"))
                : {};
            var hxSwap = $(event.target).attr("hx-swap");
            $(event.target).each(function () {
                $.each(this.attributes, function () {
                    if (
                        this.specified &&
                        this.name === "hx-on-htmx-before-request"
                    ) {
                        eval(this.value);
                    }
                });
            });
            if (event.target.tagName.toLowerCase() === "form") {
                if (path && verb) {
                    // Collect all form values
                    const formData = new FormData(event.target);
                    const values = {};
                    formData.forEach((value, key) => {
                        values[key] = value;
                    });

                    // Merge with hx-vals, if any
                    Object.assign(values, hxVals);

                    htmx.ajax(verb.toUpperCase(), path, {
                        target: hxTarget,
                        swap: hxSwap,
                        values: values,
                    }).then((response) => {
                        ajaxWithResponseHandler(event);
                    });
                } else {
                    event.target.submit();  // fallback
                }
            }
            else if (event.target.tagName.toLowerCase() === "a") {
                if (event.target.href) {
                    window.location.href = event.target.href;
                } else {
                    if (verb === "post") {
                        htmx.ajax("POST", path, {
                            target: hxTarget,
                            swap: hxSwap,
                            values: hxVals,
                        }).then((response) => {
                            ajaxWithResponseHandler(event);
                        });
                    } else {
                        htmx.ajax("GET", path, {
                            target: hxTarget,
                            swap: hxSwap,
                            values: hxVals,
                        }).then((response) => {
                            ajaxWithResponseHandler(event);
                        });
                    }
                }
            } else {
                if (verb === "post") {
                    htmx.ajax("POST", path, {
                        target: hxTarget,
                        swap: hxSwap,
                        values: hxVals,
                    }).then((response) => {
                        ajaxWithResponseHandler(event);
                    });
                } else {
                    htmx.ajax("GET", path, {
                        target: hxTarget,
                        swap: hxSwap,
                        values: hxVals,
                    }).then((response) => {
                        ajaxWithResponseHandler(event);
                    });
                }
            }
        }
    });
};

var excludeIds = "#employeeSearch";
// To exclude more elements, add their IDs (prefixed with '#') or class names (prefixed with '.'), separated by commas to 'excludeIds'.
setTimeout(() => {
    $("[name='search']").not(excludeIds).focus();
}, 100);

$("#close").attr(
    "class",
    "oh-activity-sidebar__header-icon me-2 oh-activity-sidebar__close md hydrated"
);

$("body").on("click", ".select2-search__field", function (e) {
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

$(function () {
    const $wrapper = $('.oh-wrapper-main');
    const sidebarOpen = localStorage.getItem('sidebarOpen');

    if (sidebarOpen === 'false') {
        $wrapper.addClass('oh-wrapper-main--closed');
    } else {
        $wrapper.removeClass('oh-wrapper-main--closed');
    }

    $('#sidebar').on('mouseleave', () => {
        if (localStorage.getItem('sidebarOpen') === 'false') {
            $wrapper.addClass('oh-wrapper-main--closed');
        }
    });
});

$(document).on('click', '.oh-kanban__card-body-collapse', function (e) {
    e.preventDefault();

    var $cardBody = $(this).closest('.oh-kanban__card-body');

    $cardBody.find('.oh-kanban__card-content').toggleClass('oh-kanban__card-content--hide');

    $(this).toggleClass('oh-kanban__card-collapse--down');
});


$(document).on("htmx:beforeRequest", function (event, data) {
    if (
        !Array.from(event.target.getAttributeNames()).some((attr) =>
            attr.startsWith("hx-on")
        )
    ) {
        var response = event.detail.xhr.response;
        var target = $(event.detail.elt.getAttribute("hx-target"));
        var avoid_target_ids = [
            "BiometricDeviceTestFormTarget",
            "reloadMessages",
            "infinite",
            "OtpContainer"
        ];
        var avoid_target_class = ["oh-badge--small"];
        if (
            !target.closest("form").length &&
            !avoid_target_ids.includes(target.attr("id")) &&
            !avoid_target_class.some((cls) => target.hasClass(cls))
        ) {
            target.html(`<div class="animated-background"></div>`);
        }
    }
});

$(document).on("click", ".select2-selection__choice__remove", function (event) {
    if ($('[role="tooltip"]:visible').length) {
        $('[role="tooltip"]').hide();
    }
});

$(document).on("keydown", function (event) {
    // Check if the cursor is not focused on an input field
    var isInputFocused = $(document.activeElement).is(
        "input, textarea, select"
    );

    if (event.keyCode === 27) {
        // Key code 27 for Esc in keypad
        $(".oh-modal--show").removeClass("oh-modal--show");
        $(".oh-activity-sidebar--show").removeClass(
            "oh-activity-sidebar--show"
        );
    }

    if (event.keyCode === 46) {
        // Key code 46 for delete in keypad
        // If there have any objectDetailsModal with oh-modal--show
        // take delete button inside that else take the delete button from navbar Actions
        if (!isInputFocused) {
            var $modal = $(".oh-modal--show");
            var $deleteButton = $modal.length
                ? $modal.find('[data-action="delete"]')
                : $(".oh-dropdown").find('[data-action="delete"]');
            if ($deleteButton.length) {
                $deleteButton.click();
                $deleteButton[0].click();
            }
        }
    } else if (event.keyCode === 107) {
        // Key code for the + key on the numeric keypad
        if (!isInputFocused) {
            // Click the create option from navbar of current page
            $('[data-action="create"]').click();
        }
    } else if (event.keyCode === 39) {
        // Key code for the right arrow key
        if (!isInputFocused) {
            var $modal = $(".oh-modal--show");
            var $nextButton = $modal.length
                ? $modal.find('[data-action="next"]')
                : $('[data-action="next"]'); // Click on the next button in detail view modal
            if ($nextButton.length) {
                $nextButton[0].click();
            }
        }
    } else if (event.keyCode === 37) {
        // Key code for the left arrow key
        if (!isInputFocused) {
            // Click on the previous button in detail view modal
            var $modal = $(".oh-modal--show");
            var $previousButton = $modal.length
                ? $modal.find('[data-action="previous"]')
                : $('[data-action="previous"]');
            if ($previousButton.length) {
                $previousButton[0].click();
            }
        }
    }
});

$(document).on("click", function (event) {
    if (!$(event.target).closest("#enlargeImageContainer").length) {
        hideEnlargeImage();
    }
});

$(document).on("htmx:afterSwap", function () {
    if ($("[data-summernote]").length > 0) {
        $("[data-summernote]").summernote({
            height: 300,
            codeviewFilter: false,
            codeviewIframeFilter: false,
            callbacks: {
                onChange: function (contents) {
                    $('[name="body"]').val(contents);
                },
            },
        });
    }
});
