tickCandidateCheckboxes();

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

$(".all-candidate").change(function (e) {
    var is_checked = $(this).is(":checked");
    if (is_checked) {
        $(".all-candidate-row")
            .prop("checked", true)
            .closest(".oh-sticky-table__tr")
            .addClass("highlight-selected");
    } else {
        $(".all-candidate-row")
            .prop("checked", false)
            .closest(".oh-sticky-table__tr")
            .removeClass("highlight-selected");
    }
    addingCandidateIds();
});

$(".all-candidate-row").change(function () {
    addingCandidateIds();
});

function addingCandidateIds() {
    var ids = JSON.parse($("#selectedInstances").attr("data-ids") || "[]");
    var selectedCount = 0;

    $(".all-candidate-row").each(function () {
        if ($(this).is(":checked")) {
            ids.push(this.id);
        } else {
            var index = ids.indexOf(this.id);
            if (index > -1) {
                ids.splice(index, 1);
            }
        }
    });
    var ids = makeListUnique1(ids);
    var selectedCount = ids.length;

    $("#selectedInstances").attr("data-ids", JSON.stringify(ids));
    if (selectedCount > 0) {
        $("#exportCandidates").css("display", "inline-flex");
        $("#unselectAllInstances").css("display", "inline-flex");
        $("#selectedCandidate").text(selectedCount + " -" + i18nMessages.selected);
        $("#selectedCandidate").css("display", "inline-flex");
    } else {
        $("#exportCandidates").css("display", "none");
        $("#unselectAllInstances").css("display", "none");
        $("#selectedCandidate").css("display", "none");
    }

}

function tickCandidateCheckboxes() {
    var ids = JSON.parse($("#selectedInstances").attr("data-ids") || "[]");
    var uniqueIds = makeListUnique1(ids);
    toggleHighlight(uniqueIds);
    var selectedCount = uniqueIds.length;
    click = $("#selectedInstances").attr("data-clicked");
    if (click === "1") {
        $(".all-candidate").prop("checked", true);
        $("#allCandidate").prop("checked", true);
    }
    uniqueIds.forEach(function (id) {
        $("#" + id).prop("checked", true);
    });

    if (selectedCount > 0) {
        $("#exportCandidates").css("display", "inline-flex");
        $("#unselectAllInstances").css("display", "inline-flex");
        $("#selectedCandidate").text(selectedCount + " -" + i18nMessages.selected);
        $("#selectedCandidate").css("display", "inline-flex");
    } else {
        $("#exportCandidates").css("display", "none");
        $("#unselectAllInstances").css("display", "none");
        $("#selectedCandidate").css("display", "none");
    }
}

function makeListUnique1(list) {
    return Array.from(new Set(list));
}

$("#archiveCandidates").click(function (e) {
    e.preventDefault();

    ids = [];
    ids.push($("#selectedInstances").attr("data-ids"));
    ids = JSON.parse($("#selectedInstances").attr("data-ids"));
    if (ids.length === 0) {
        Swal.fire({
            text: i18nMessages.noRowsSelected,
            icon: "warning",
            confirmButtonText: i18nMessages.close,
        });
    } else {
        Swal.fire({
            text: i18nMessages.confirmBulkArchive,
            icon: "info",
            showCancelButton: true,
            confirmButtonColor: "#008000",
            cancelButtonColor: "#d33",
            confirmButtonText: i18nMessages.confirm,
            cancelButtonText: i18nMessages.cancel,
        }).then(function (result) {
            if (result.isConfirmed) {
                e.preventDefault();
                $.ajax({
                    type: "POST",
                    url: "/recruitment/candidate-bulk-archive?is_active=False",
                    data: {
                        csrfmiddlewaretoken: getCookie("csrftoken"),
                        ids: JSON.stringify(ids),
                    },
                    success: function (response, textStatus, jqXHR) {
                        if (jqXHR.status === 200) {
                            location.reload(); // Reload the current page
                        } else {
                            // console.log("Unexpected HTTP status:", jqXHR.status);
                        }
                    },
                });
            }
        });
    }
});

$("#unArchiveCandidates").click(function (e) {
    e.preventDefault();
    ids = [];
    ids.push($("#selectedInstances").attr("data-ids"));
    ids = JSON.parse($("#selectedInstances").attr("data-ids"));
    if (ids.length === 0) {
        Swal.fire({
            text: i18nMessages.noRowsSelected,
            icon: "warning",
            confirmButtonText: i18nMessages.close,
        });
    } else {
        Swal.fire({
            text: i18nMessages.confirmBulkUnArchive,
            icon: "info",
            showCancelButton: true,
            confirmButtonColor: "#008000",
            cancelButtonColor: "#d33",
            confirmButtonText: i18nMessages.confirm,
            cancelButtonText: i18nMessages.cancel,
        }).then(function (result) {
            if (result.isConfirmed) {
                e.preventDefault();
                $.ajax({
                    type: "POST",
                    url: "/recruitment/candidate-bulk-archive?is_active=True",
                    data: {
                        csrfmiddlewaretoken: getCookie("csrftoken"),
                        ids: JSON.stringify(ids),
                    },
                    success: function (response, textStatus, jqXHR) {
                        if (jqXHR.status === 200) {
                            location.reload(); // Reload the current page
                        } else {
                            // console.log("Unexpected HTTP status:", jqXHR.status);
                        }
                    },
                });
            }
        });
    }
});

$("#deleteCandidates").click(function (e) {
    e.preventDefault();

    var checkedRows = $(".all-candidate-row").filter(":checked");
    if (checkedRows.length === 0) {
        Swal.fire({
            text: i18nMessages.noRowsSelected,
            icon: "warning",
            confirmButtonText: i18nMessages.close,
        });
    } else {
        Swal.fire({
            text: i18nMessages.confirmBulkDelete,
            icon: "error",
            showCancelButton: true,
            confirmButtonColor: "#008000",
            cancelButtonColor: "#d33",
            confirmButtonText: i18nMessages.confirm,
            cancelButtonText: i18nMessages.cancel,
        }).then(function (result) {
            if (result.isConfirmed) {
                e.preventDefault();
                ids = [];

                ids.push($("#selectedInstances").attr("data-ids"));
                ids = JSON.parse($("#selectedInstances").attr("data-ids"));

                $.ajax({
                    type: "POST",
                    url: "/recruitment/candidate-bulk-delete",
                    data: {
                        csrfmiddlewaretoken: getCookie("csrftoken"),
                        ids: JSON.stringify(ids),
                    },
                    success: function (response, textStatus, jqXHR) {
                        if (jqXHR.status === 200) {
                            location.reload(); // Reload the current page
                        } else {
                            // console.log("Unexpected HTTP status:", jqXHR.status);
                        }
                    },
                });
            }
        });
    }
});
