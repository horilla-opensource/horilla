tickShiftCheckboxes();
function makeShiftListUnique(list) {
    return Array.from(new Set(list));
}

tickWorktypeCheckboxes();
function makeWorktypeListUnique(list) {
    return Array.from(new Set(list));
}

tickRShiftCheckboxes();
function makeRShiftListUnique(list) {
    return Array.from(new Set(list));
}

tickRWorktypeCheckboxes();
function makeRWorktypeListUnique(list) {
    return Array.from(new Set(list));
}

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

$(".all-rshift").change(function (e) {
    var is_checked = $(this).is(":checked");
    var closest = $(this)
        .closest(".oh-sticky-table__thead")
        .siblings(".oh-sticky-table__tbody");
    if (is_checked) {
        $(closest)
            .children()
            .find(".all-rshift-row")
            .prop("checked", true)
            .closest(".oh-sticky-table__tr")
            .addClass("highlight-selected");
    } else {
        $(closest)
            .children()
            .find(".all-rshift-row")
            .prop("checked", false)
            .closest(".oh-sticky-table__tr")
            .removeClass("highlight-selected");
    }
});

function tickRShiftCheckboxes() {
    var ids = JSON.parse($("#selectedRShifts").attr("data-ids") || "[]");
    uniqueIds = makeRShiftListUnique(ids);
    toggleHighlight(uniqueIds);
    click = $("#selectedRShifts").attr("data-clicked");
    if (click === "1") {
        $(".all-rshift").prop("checked", true);
    }
    uniqueIds.forEach(function (id) {
        $("#" + id).prop("checked", true);
    });
    var selectedCount = uniqueIds.length;
    if (selectedCount > 0) {
        $("#exportRShifts").css("display", "inline-flex");
        $("#unselectAllRShifts").css("display", "inline-flex");
        $("#selectedShowRShifts").css("display", "inline-flex");
        $("#selectedShowRShifts").text(selectedCount + " -" + i18nMessages.selected);
    } else {
        $("#selectedShowRShifts").css("display", "none");
        $("#exportRShifts").css("display", "none");
        $("#unselectAllRShifts").css("display", "none");
    }
}

$("#exportRShifts").click(function (e) {
    var currentDate = new Date().toISOString().slice(0, 10);
    ids = [];
    ids = JSON.parse($("#selectedRShifts").attr("data-ids"));
    Swal.fire({
        text: i18nMessages.downloadExcel,
        icon: "question",
        showCancelButton: true,
        confirmButtonColor: "#008000",
        cancelButtonColor: "#d33",
        confirmButtonText: i18nMessages.confirm,
        cancelButtonText: i18nMessages.cancel,
    }).then(function (result) {
        if (result.isConfirmed) {
            $.ajax({
                type: "GET",
                url: "/rotating-shift-assign-info-export",
                data: {
                    ids: JSON.stringify(ids),
                },
                dataType: "binary",
                xhrFields: {
                    responseType: "blob",
                },
                success: function (response) {
                    const file = new Blob([response], {
                        type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    });
                    const url = URL.createObjectURL(file);
                    const link = document.createElement("a");
                    link.href = url;
                    link.download =
                        "Rotating_shift_assign_export" + currentDate + ".xlsx";
                    document.body.appendChild(link);
                    link.click();
                },
                error: function (xhr, textStatus, errorThrown) {
                    console.error("Error downloading file:", errorThrown);
                },
            });
        }
    });
});

$("#archiveRotatingShiftAssign").click(function (e) {
    e.preventDefault();
    ids = [];
    ids.push($("#selectedRShifts").attr("data-ids"));
    ids = JSON.parse($("#selectedRShifts").attr("data-ids"));
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
                ids = [];
                ids.push($("#selectedRShifts").attr("data-ids"));
                ids = JSON.parse($("#selectedRShifts").attr("data-ids"));
                $.ajax({
                    type: "POST",
                    url: "/rotating-shift-assign-bulk-archive?is_active=False",
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

$("#unArchiveRotatingShiftAssign").click(function (e) {
    e.preventDefault();
    ids = [];
    ids.push($("#selectedRShifts").attr("data-ids"));
    ids = JSON.parse($("#selectedRShifts").attr("data-ids"));
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
                ids = [];
                ids.push($("#selectedRShifts").attr("data-ids"));
                ids = JSON.parse($("#selectedRShifts").attr("data-ids"));
                $.ajax({
                    type: "POST",
                    url: "/rotating-shift-assign-bulk-archive?is_active=True",
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

$("#deleteRotatingShiftAssign").click(function (e) {
    e.preventDefault();
    ids = [];
    ids.push($("#selectedRShifts").attr("data-ids"));
    ids = JSON.parse($("#selectedRShifts").attr("data-ids"));
    if (ids.length === 0) {
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
                ids = [];
                ids.push($("#selectedRShifts").attr("data-ids"));
                ids = JSON.parse($("#selectedRShifts").attr("data-ids"));
                $.ajax({
                    type: "POST",
                    url: "/rotating-shift-assign-bulk-delete",
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

$(".all-rwork-type").change(function (e) {
    var is_checked = $(this).is(":checked");
    var closest = $(this)
        .closest(".oh-sticky-table__thead")
        .siblings(".oh-sticky-table__tbody");
    if (is_checked) {
        $(closest)
            .children()
            .find(".all-rwork-type-row")
            .prop("checked", true)
            .closest(".oh-sticky-table__tr")
            .addClass("highlight-selected");
    } else {
        $(closest)
            .children()
            .find(".all-rwork-type-row")
            .prop("checked", false)
            .closest(".oh-sticky-table__tr")
            .removeClass("highlight-selected");
    }
});

function tickRWorktypeCheckboxes() {
    var ids = JSON.parse($("#selectedRWorktypes").attr("data-ids") || "[]");
    uniqueIds = makeWorktypeListUnique(ids);
    toggleHighlight(uniqueIds);
    click = $("#selectedRWorktypes").attr("data-clicked");
    if (click === "1") {
        $(".all-rwork-type").prop("checked", true);
    }
    uniqueIds.forEach(function (id) {
        $("#" + id).prop("checked", true);
    });
    var selectedCount = uniqueIds.length;
    if (selectedCount > 0) {
        $("#exportRWorktypes").css("display", "inline-flex");
        $("#unselectAllRWorktypes").css("display", "inline-flex");
        $("#selectedShowRWorktypes").css("display", "inline-flex");
        $("#selectedShowRWorktypes").text(selectedCount + " -" + i18nMessages.selected);
    } else {
        $("#selectedShowRWorktypes").css("display", "none");
        $("#exportRWorktypes").css("display", "none");
        $("#unselectAllRWorktypes").css("display", "none");
    }
}

$("#exportRWorktypes").click(function (e) {
    var currentDate = new Date().toISOString().slice(0, 10);
    ids = [];
    ids = JSON.parse($("#selectedRWorktypes").attr("data-ids"));
    Swal.fire({
        text: i18nMessages.downloadExcel,
        icon: "question",
        showCancelButton: true,
        confirmButtonColor: "#008000",
        cancelButtonColor: "#d33",
        confirmButtonText: i18nMessages.confirm,
        cancelButtonText: i18nMessages.cancel,

    }).then(function (result) {
        if (result.isConfirmed) {
            $.ajax({
                type: "GET",
                url: "/rotating-work-type-assign-export",
                data: {
                    ids: JSON.stringify(ids),
                },
                dataType: "binary",
                xhrFields: {
                    responseType: "blob",
                },
                success: function (response) {
                    const file = new Blob([response], {
                        type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    });
                    const url = URL.createObjectURL(file);
                    const link = document.createElement("a");
                    link.href = url;
                    link.download = "Rotating_work_type_assign" + currentDate + ".xlsx";
                    document.body.appendChild(link);
                    link.click();
                },
                error: function (xhr, textStatus, errorThrown) {
                    console.error("Error downloading file:", errorThrown);
                },
            });
        }
    });
});

$("#archiveRotatingWorkTypeAssign").click(function (e) {
    var ids = JSON.parse($("#selectedRWorktypes").attr("data-ids"));
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
                var idsString = JSON.stringify(ids);
                var hxSpan = $("#archiveRotatingWorkTypeAssignSpan");
                hxSpan.attr("hx-vals", JSON.stringify({ ids: idsString, is_active: false }));
                hxSpan.click();
            }
        });
    }
});

$("#unArchiveRotatingWorkTypeAssign").click(function (e) {
    e.preventDefault();
    var ids = JSON.parse($("#selectedRWorktypes").attr("data-ids"));
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
                var idsString = JSON.stringify(ids);
                var hxSpan = $("#archiveRotatingWorkTypeAssignSpan");
                hxSpan.attr("hx-vals", JSON.stringify({ ids: idsString, is_active: true }));
                hxSpan.click();
            }
        });
    }
});


$("#deleteRotatingWorkTypeAssign").click(function (e) {
    e.preventDefault();

    ids = [];
    ids.push($("#selectedRWorktypes").attr("data-ids"));
    ids = JSON.parse($("#selectedRWorktypes").attr("data-ids"));
    if (ids.length === 0) {
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
                ids = [];
                ids.push($("#selectedRWorktypes").attr("data-ids"));
                ids = JSON.parse($("#selectedRWorktypes").attr("data-ids"));
                $.ajax({
                    type: "POST",
                    url: "/rotating-work-type-assign-bulk-delete",
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

$(".all-shift-requests").change(function (e) {
    var is_checked = $(this).is(":checked");
    var closest = $(this)
        .closest(".oh-sticky-table__thead")
        .siblings(".oh-sticky-table__tbody");
    if (is_checked) {
        $(closest)
            .children()
            .find(".all-shift-requests-row")
            .prop("checked", true)
            .closest(".oh-sticky-table__tr")
            .addClass("highlight-selected");
    } else {
        $(closest)
            .children()
            .find(".all-shift-requests-row")
            .prop("checked", false)
            .closest(".oh-sticky-table__tr")
            .removeClass("highlight-selected");
    }
});

function tickShiftCheckboxes() {
    var ids = JSON.parse($("#selectedShifts").attr("data-ids") || "[]");
    uniqueIds = makeShiftListUnique(ids);
    toggleHighlight(uniqueIds);
    click = $("#selectedShifts").attr("data-clicked");
    if (click === "1") {
        $(".all-shift-requests").prop("checked", true);
    }
    uniqueIds.forEach(function (id) {
        $("#" + id).prop("checked", true);
    });
    var selectedCount = uniqueIds.length;
    if (selectedCount > 0) {
        $("#exportShifts").css("display", "inline-flex");
        $("#unselectAllShifts").css("display", "inline-flex");
        $("#selectedShowShifts").css("display", "inline-flex");
        $("#selectedShowShifts").text(selectedCount + " -" + i18nMessages.selected);
    } else {
        $("#selectedShowShifts").css("display", "none");
        $("#exportShifts").css("display", "none");
        $("#unselectAllShifts").css("display", "none");
    }
}

function exportShiftRequests() {
    var currentDate = new Date().toISOString().slice(0, 10);
    ids = [];
    ids = JSON.parse($("#selectedShifts").attr("data-ids"));
    Swal.fire({
        text: i18nMessages.downloadExcel,
        icon: "question",
        showCancelButton: true,
        confirmButtonColor: "#008000",
        cancelButtonColor: "#d33",
        confirmButtonText: i18nMessages.confirm,
        cancelButtonText: i18nMessages.cancel,
    }).then(function (result) {
        if (result.isConfirmed) {
            $.ajax({
                type: "GET",
                url: "/shift-request-info-export",
                data: {
                    ids: JSON.stringify(ids),
                },
                dataType: "binary",
                xhrFields: {
                    responseType: "blob",
                },
                success: function (response) {
                    const file = new Blob([response], {
                        type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    });
                    const url = URL.createObjectURL(file);
                    const link = document.createElement("a");
                    link.href = url;
                    link.download = "Shift_requests" + currentDate + ".xlsx";
                    document.body.appendChild(link);
                    link.click();
                },
                error: function (xhr, textStatus, errorThrown) {
                    console.error("Error downloading file:", errorThrown);
                },
            });
        }
    });
}

$("#approveShiftRequest").click(function (e) {
    e.preventDefault();
    ids = [];
    ids.push($("#selectedShifts").attr("data-ids"));
    ids = JSON.parse($("#selectedShifts").attr("data-ids"));
    if (ids.length === 0) {
        Swal.fire({
            text: i18nMessages.noRowsSelected,
            icon: "warning",
            confirmButtonText: i18nMessages.close,
        });
    } else {
        // Use SweetAlert for the confirmation dialog
        Swal.fire({
            text: i18nMessages.confirmBulkApprove,
            icon: "success",
            showCancelButton: true,
            confirmButtonColor: "#008000",
            cancelButtonColor: "#d33",
            confirmButtonText: i18nMessages.confirm,
            cancelButtonText: i18nMessages.cancel,
        }).then(function (result) {
            if (result.isConfirmed) {
                ids = [];
                ids.push($("#selectedShifts").attr("data-ids"));
                ids = JSON.parse($("#selectedShifts").attr("data-ids"));
                $.ajax({
                    type: "POST",
                    url: "/shift-request-bulk-approve",
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

$("#cancelShiftRequest").click(function (e) {
    e.preventDefault();
    ids = [];
    ids.push($("#selectedShifts").attr("data-ids"));
    ids = JSON.parse($("#selectedShifts").attr("data-ids"));
    if (ids.length === 0) {
        Swal.fire({
            text: i18nMessages.noRowsSelected,
            icon: "warning",
            confirmButtonText: i18nMessages.close,
        });
    } else {
        Swal.fire({
            text: i18nMessages.confirmBulkReject,
            icon: "info",
            showCancelButton: true,
            confirmButtonColor: "#008000",
            cancelButtonColor: "#d33",
            confirmButtonText: i18nMessages.confirm,
            cancelButtonText: i18nMessages.cancel,
        }).then(function (result) {
            if (result.isConfirmed) {
                ids = [];
                ids.push($("#selectedShifts").attr("data-ids"));
                ids = JSON.parse($("#selectedShifts").attr("data-ids"));
                $.ajax({
                    type: "POST",
                    url: "/shift-request-bulk-cancel",
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

$("#deleteShiftRequest").click(function (e) {
    e.preventDefault();
    ids = [];
    ids.push($("#selectedShifts").attr("data-ids"));
    ids = JSON.parse($("#selectedShifts").attr("data-ids"));
    if (ids.length === 0) {
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
                ids = [];
                ids.push($("#selectedShifts").attr("data-ids"));
                ids = JSON.parse($("#selectedShifts").attr("data-ids"));
                $.ajax({
                    type: "POST",
                    url: "/shift-request-bulk-delete",
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

$(".all-work-type-requests").change(function (e) {
    var is_checked = $(this).is(":checked");
    var closest = $(this)
        .closest(".oh-sticky-table__thead")
        .siblings(".oh-sticky-table__tbody");
    if (is_checked) {
        $(closest)
            .children()
            .find(".all-work-type-requests-row")
            .prop("checked", true)
            .closest(".oh-sticky-table__tr")
            .addClass("highlight-selected");
    } else {
        $(closest)
            .children()
            .find(".all-work-type-requests-row")
            .prop("checked", false)
            .closest(".oh-sticky-table__tr")
            .removeClass("highlight-selected");
    }
});

function tickWorktypeCheckboxes() {
    var ids = JSON.parse($("#selectedWorktypes").attr("data-ids") || "[]");
    uniqueIds = makeWorktypeListUnique(ids);
    toggleHighlight(uniqueIds);
    click = $("#selectedWorktypes").attr("data-clicked");
    if (click === "1") {
        $(".all-work-type-requests").prop("checked", true);
    }
    uniqueIds.forEach(function (id) {
        $("#" + id).prop("checked", true);
    });
    var selectedCount = uniqueIds.length;
    if (selectedCount > 0) {
        $("#exportWorktypes").css("display", "inline-flex");
        $("#unselectAllWorktypes").css("display", "inline-flex");
        $("#selectedShowWorktypes").css("display", "inline-flex");
        $("#selectedShowWorktypes").text(selectedCount + " -" + i18nMessages.selected);
    } else {
        $("#selectedShowWorktypes").css("display", "none");
        $("#exportWorktypes").css("display", "none");
        $("#unselectAllWorktypes").css("display", "none");
    }
}

function exportWorkTypeRequets() {
    var currentDate = new Date().toISOString().slice(0, 10);
    ids = [];
    ids = JSON.parse($("#selectedWorktypes").attr("data-ids"));
    Swal.fire({
        text: i18nMessages.downloadExcel,
        icon: "question",
        showCancelButton: true,
        confirmButtonColor: "#008000",
        cancelButtonColor: "#d33",
        confirmButtonText: i18nMessages.confirm,
        cancelButtonText: i18nMessages.cancel,
    }).then(function (result) {
        if (result.isConfirmed) {
            $.ajax({
                type: "GET",
                url: "/work-type-request-info-export",
                data: {
                    ids: JSON.stringify(ids),
                },
                dataType: "binary",
                xhrFields: {
                    responseType: "blob",
                },
                success: function (response) {
                    const file = new Blob([response], {
                        type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    });
                    const url = URL.createObjectURL(file);
                    const link = document.createElement("a");
                    link.href = url;
                    link.download = "Work_type_requests" + currentDate + ".xlsx";
                    document.body.appendChild(link);
                    link.click();
                },
                error: function (xhr, textStatus, errorThrown) {
                    console.error("Error downloading file:", errorThrown);
                },
            });
        }
    });
}

$("#approveWorkTypeRequest").click(function (e) {
    e.preventDefault();
    ids = [];
    ids.push($("#selectedWorktypes").attr("data-ids"));
    ids = JSON.parse($("#selectedWorktypes").attr("data-ids"));
    if (ids.length === 0) {
        Swal.fire({
            text: i18nMessages.noRowsSelected,
            icon: "warning",
            confirmButtonText: i18nMessages.close,
        });
    } else {
        Swal.fire({
            text: i18nMessages.confirmBulkApprove,
            icon: "success",
            showCancelButton: true,
            confirmButtonColor: "#008000",
            cancelButtonColor: "#d33",
            confirmButtonText: i18nMessages.confirm,
            cancelButtonText: i18nMessages.cancel,
        }).then(function (result) {
            if (result.isConfirmed) {
                e.preventDefault();
                ids = [];
                ids.push($("#selectedWorktypes").attr("data-ids"));
                ids = JSON.parse($("#selectedWorktypes").attr("data-ids"));
                $.ajax({
                    type: "POST",
                    url: "/work-type-request-bulk-approve",
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

$("#cancelWorkTypeRequest").click(function (e) {
    e.preventDefault();
    ids = [];
    ids.push($("#selectedWorktypes").attr("data-ids"));
    ids = JSON.parse($("#selectedWorktypes").attr("data-ids"));
    if (ids.length === 0) {
        Swal.fire({
            text: i18nMessages.noRowsSelected,
            icon: "warning",
            confirmButtonText: i18nMessages.close,
        });
    } else {
        Swal.fire({
            text: i18nMessages.confirmBulkReject,
            icon: "warning",
            showCancelButton: true,
            confirmButtonColor: "#008000",
            cancelButtonColor: "#d33",
            confirmButtonText: i18nMessages.confirm,
            cancelButtonText: i18nMessages.cancel,
        }).then(function (result) {
            if (result.isConfirmed) {
                ids = [];
                ids.push($("#selectedWorktypes").attr("data-ids"));
                ids = JSON.parse($("#selectedWorktypes").attr("data-ids"));
                $.ajax({
                    type: "POST",
                    url: "/work-type-request-bulk-cancel",
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

$("#deleteWorkTypeRequest").click(function (e) {
    e.preventDefault();
    ids = [];
    ids.push($("#selectedWorktypes").attr("data-ids"));
    ids = JSON.parse($("#selectedWorktypes").attr("data-ids"));
    if (ids.length === 0) {
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
                ids.push($("#selectedWorktypes").attr("data-ids"));
                ids = JSON.parse($("#selectedWorktypes").attr("data-ids"));
                $.ajax({
                    type: "POST",
                    url: "/work-type-request-bulk-delete",
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
