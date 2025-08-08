function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Get the form element
var form = document.getElementById("projectImportForm");

// Add an event listener to the form submission
form.addEventListener("submit", function (event) {
    // Prevent the default form submission
    event.preventDefault();

    // Create a new form data object
    var formData = new FormData();

    // Append the file to the form data object
    var fileInput = document.querySelector("#projectImportFile");
    formData.append("file", fileInput.files[0]);
    $.ajax({
        type: "POST",
        url: "/project/project-import",
        dataType: "binary",
        data: formData,
        processData: false,
        contentType: false,
        headers: {
            "X-CSRFToken": getCookie('csrftoken'), // Replace with your csrf token value
        },
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
            link.download = "ImportError.xlsx";
            document.body.appendChild(link);
            link.click();
        },
        error: function (xhr, textStatus, errorThrown) {
            console.error("Error downloading file:", errorThrown);
        },
    });
});


$("#importProject").click(function (e) {
    e.preventDefault();
    // Use SweetAlert for the confirmation dialog
    Swal.fire({

        text: i18nMessages.downloadTemplate,
        icon: 'question',
        showCancelButton: true,
        confirmButtonColor: '#008000',
        cancelButtonColor: '#d33',
        confirmButtonText: i18nMessages.confirm,
        cancelButtonText: i18nMessages.cancel,
    }).then(function (result) {
        if (result.isConfirmed) {
            $("#loading").show();
            var xhr = new XMLHttpRequest();
            xhr.open('GET', "/project/project-import", true);
            xhr.responseType = 'arraybuffer';

            xhr.upload.onprogress = function (e) {
                if (e.lengthComputable) {
                    var percent = (e.loaded / e.total) * 100;
                    $(".progress-bar").width(percent + "%").attr("aria-valuenow", percent);
                    $("#progress-text").text("Uploading... " + percent.toFixed(2) + "%");
                }
            };

            xhr.onload = function (e) {
                if (this.status == 200) {
                    const file = new Blob([this.response], {
                        type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    });
                    const url = URL.createObjectURL(file);
                    const link = document.createElement("a");
                    link.href = url;
                    link.download = "project_template.xlsx";
                    document.body.appendChild(link);
                    link.click();
                }
            };

            xhr.onerror = function (e) {
                console.error("Error downloading file:", e);
            };

            xhr.send();
        }
    });
});

$(document).on('click', '#importProject', function (e) {
    e.preventDefault();

    // Use SweetAlert for the confirmation dialog
    Swal.fire({
        text: i18nMessages.downloadTemplate,
        icon: 'question',
        showCancelButton: true,
        confirmButtonColor: '#008000',
        cancelButtonColor: '#d33',
        confirmButtonText: i18nMessages.confirm,
        cancelButtonText: i18nMessages.cancel,
    }).then(function (result) {
        if (result.isConfirmed) {
            $("#loading").show();
            var xhr = new XMLHttpRequest();
            xhr.open('GET', "/project/project-import", true);
            xhr.responseType = 'arraybuffer';

            xhr.upload.onprogress = function (e) {
                if (e.lengthComputable) {
                    var percent = (e.loaded / e.total) * 100;
                    $(".progress-bar").width(percent + "%").attr("aria-valuenow", percent);
                    $("#progress-text").text("Uploading... " + percent.toFixed(2) + "%");
                }
            };

            xhr.onload = function (e) {
                if (this.status == 200) {
                    const file = new Blob([this.response], {
                        type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    });
                    const url = URL.createObjectURL(file);
                    const link = document.createElement("a");
                    link.href = url;
                    link.download = "project_template.xlsx";
                    document.body.appendChild(link);
                    link.click();
                    // Clean up by removing the link element
                    document.body.removeChild(link);
                    URL.revokeObjectURL(url);
                }
            };

            xhr.onerror = function (e) {
                console.error("Error downloading file:", e);
            };

            xhr.send();
        }
    });
});


$(document).ajaxStart(function () {
    $("#loading").show();
});

$(document).ajaxStop(function () {
    $("#loading").hide();
});

function simulateProgress() {
    let progressBar = document.querySelector('.progress-bar');
    let progressText = document.getElementById('progress-text');

    let width = 0;
    let interval = setInterval(function () {
        if (width >= 100) {
            clearInterval(interval);
            progressText.innerText = gettext("Upload Completed!");
            setTimeout(function () {
                document.getElementById('loading').style.display = 'none';
            }, 3000);
            Swal.fire({
                text: gettext("Imported Successfully!"),
                icon: "success",
                showConfirmButton: false,
                timer: 2000,
                timerProgressBar: true,
            });
            setTimeout(function () {
                $('#projectImport').removeClass('oh-modal--show');
                location.reload(true);
            }, 2000);
        } else {
            width++;
            progressBar.style.width = width + '%';
            progressBar.setAttribute('aria-valuenow', width);
            progressText.innerText = i18nMessages.uploading + width + '%';
        }
    }, 20);
}

document.getElementById('projectImportForm').addEventListener('submit', function (event) {
    event.preventDefault();

    var fileInput = $('#projectImportFile').val();
    var allowedExtensions = /(\.xlsx)$/i;

    if (!allowedExtensions.exec(fileInput)) {

        var errorMessage = document.createElement('div');
        errorMessage.classList.add('error-message');

        errorMessage.textContent = gettext("Please upload a file with the .xlsx extension only.");

        document.getElementById('error-container').appendChild(errorMessage);

        fileInput.value = '';

        setTimeout(function () {
            errorMessage.remove();
        }, 2000);

        return false;
    }
    else {

        document.getElementById('loading').style.display = 'block';


        simulateProgress();
    }
})
