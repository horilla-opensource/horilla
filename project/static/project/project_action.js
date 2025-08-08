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

function validateProjectIds(event) {
    var takeAction = $(event.currentTarget).data("action");

    var idsRaw = $("#selectedInstances").attr("data-ids");
    if (!idsRaw) {
        Swal.fire({
            text: i18nMessages.noRowsSelected,
            icon: "warning",
            confirmButtonText: i18nMessages.close,
        });
        return;
    }

    var ids = JSON.parse(idsRaw);
    if (ids.length === 0) {
        Swal.fire({
            text: i18nMessages.noRowsSelected,
            icon: "warning",
            confirmButtonText: i18nMessages.close,
        });
        return;
    }

    let triggerId;
    if (takeAction === "archive") {
        triggerId = "#bulkArchiveProject";
    } else if (takeAction === "unarchive") {
        triggerId = "#bulkUnArchiveProject";
    } else if (takeAction === "delete") {
        triggerId = "#bulkDeleteProject";
    } else {
        console.warn("Unsupported action:", takeAction);
        return;
    }

    const $triggerElement = $(triggerId);
    if ($triggerElement.length) {
        $triggerElement.attr("hx-vals", JSON.stringify({ ids })).click();
    } else {
        console.warn("Trigger element not found for:", triggerId);
    }
}

$(".all-projects").change(function (e) {
    var is_checked = $(this).is(":checked");
    if (is_checked) {
        $(".all-project-row").prop("checked", true);
    } else {
        $(".all-project-row").prop("checked", false);
    }
});

$("#exportProject").click(function (e) {
    e.preventDefault();

    var checkedRows = $(".all-project-row").filter(":checked");
    if (checkedRows.length === 0) {
        Swal.fire({
            text: i18nMessages.noRowsSelected,
            icon: "warning",
            confirmButtonText: i18nMessages.close,
        });
    } else {
        Swal.fire({
            text: i18nMessages.downloadExcel,
            icon: "info",
            showCancelButton: true,
            confirmButtonColor: "#008000",
            cancelButtonColor: "#d33",
            confirmButtonText: i18nMessages.confirm,
            cancelButtonText: i18nMessages.cancel,
        }).then(function (result) {
            if (result.isConfirmed) {
                var checkedRows = $(".all-project-row").filter(":checked");
                ids = [];
                checkedRows.each(function () {
                    ids.push($(this).attr("id"));
                });

                $.ajax({
                    type: "POST",
                    url: "/project/project-bulk-export",
                    dataType: "binary",
                    xhrFields: {
                        responseType: "blob",
                    },
                    data: {
                        csrfmiddlewaretoken: getCookie("csrftoken"),
                        ids: JSON.stringify(ids),
                    },
                    success: function (response, textStatus, jqXHR) {
                        const file = new Blob([response], {
                            type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        });
                        const url = URL.createObjectURL(file);
                        const link = document.createElement("a");
                        link.href = url;
                        link.download = "project details.xlsx";
                        document.body.appendChild(link);
                        link.click();
                    },
                });
            }
        });
    }
});

$(document).on('click', '#exportProject', function (e) {
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
            text: i18nMessages.downloadExcel,
            icon: "info",
            showCancelButton: true,
            confirmButtonColor: "#008000",
            cancelButtonColor: "#d33",
            confirmButtonText: i18nMessages.confirm,
            cancelButtonText: i18nMessages.cancel,
        }).then(function (result) {
            if (result.isConfirmed) {
                // var checkedRows = $(".all-project-row").filter(":checked");
                // ids = [];
                // checkedRows.each(function () {
                //   ids.push($(this).attr("id"));
                // });

                $.ajax({
                    type: "POST",
                    url: "/project/project-bulk-export",
                    dataType: "binary",
                    xhrFields: {
                        responseType: "blob",
                    },
                    data: {
                        csrfmiddlewaretoken: getCookie("csrftoken"),
                        ids: JSON.stringify(ids),
                    },
                    success: function (response, textStatus, jqXHR) {
                        const file = new Blob([response], {
                            type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        });
                        const url = URL.createObjectURL(file);
                        const link = document.createElement("a");
                        link.href = url;
                        link.download = "project details.xlsx";
                        document.body.appendChild(link);
                        link.click();
                    },
                });
            }
        });
    }
});




// // Get the form element
// var form = document.getElementById("projectImportForm");

// // Add an event listener to the form submission
// form.addEventListener("submit", function (event) {
//   // Prevent the default form submission
//   event.preventDefault();

//   // Create a new form data object
//   var formData = new FormData();

//   // Append the file to the form data object
//   var fileInput = document.querySelector("#projectImportFile");
//   formData.append("file", fileInput.files[0]);
//   $.ajax({
//     type: "POST",
//     url: "/project/project-import",
//     dataType: "binary",
//     data: formData,
//     processData: false,
//     contentType: false,
//     headers: {
//       "X-CSRFToken": getCookie('csrftoken'), // Replace with your csrf token value
//     },
//     xhrFields: {
//       responseType: "blob",
//     },
//     success: function (response) {
//       const file = new Blob([response], {
//         type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
//       });
//       const url = URL.createObjectURL(file);
//       const link = document.createElement("a");
//       link.href = url;
//       link.download = "ImportError.xlsx";
//       document.body.appendChild(link);
//       link.click();
//     },
//     error: function (xhr, textStatus, errorThrown) {
//       console.error("Error downloading file:", errorThrown);
//     },
//   });
// });

// $("#importProject").click(function (e) {
//   e.preventDefault();
//   var languageCode = null;
//   getCurrentLanguageCode(function (code) {
//     languageCode = code;
//     var confirmMessage = downloadMessages[languageCode];
//     // Use SweetAlert for the confirmation dialog
//     Swal.fire({
//       text: confirmMessage,
//       icon: 'question',
//       showCancelButton: true,
//       confirmButtonColor: '#008000',
//       cancelButtonColor: '#d33',
//       confirmButtonText: 'Confirm'
//     }).then(function(result) {
//       if (result.isConfirmed) {
//         $.ajax({
//           type: "GET",
//           url: "/project/project-import",
//           dataType: "binary",
//           xhrFields: {
//             responseType: "blob",
//           },
//           success: function (response) {
//             const file = new Blob([response], {
//               type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
//             });
//             const url = URL.createObjectURL(file);
//             const link = document.createElement("a");
//             link.href = url;
//             link.download = "project_template.xlsx";
//             document.body.appendChild(link);
//             link.click();
//           },
//           error: function (xhr, textStatus, errorThrown) {
//             console.error("Error downloading file:", errorThrown);
//           },
//         });
//       }
//     });
//   });
// });

// $('#importProject').click(function (e) {
//   $.ajax({
//     type: 'POST',
//     url: '/project/project-import',
//     dataType: 'binary',
//     xhrFields: {
//       responseType: 'blob'
//     },
//     success: function(response) {
//       const file = new Blob([response], {type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'});
//       const url = URL.createObjectURL(file);
//       const link = document.createElement('a');
//       link.href = url;
//       link.download = 'project.xlsx';
//       document.body.appendChild(link);
//       link.click();
//     },
//     error: function(xhr, textStatus, errorThrown) {
//       console.error('Error downloading file:', errorThrown);
//     }
//   });
// });
