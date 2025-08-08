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



function template_download(e) {
    e.preventDefault();
    Swal.fire({
        text: i18nMessages.downloadTemplate,
        icon: "question",
        showCancelButton: true,
        confirmButtonColor: "#008000",
        cancelButtonColor: "#d33",
        confirmButtonText: i18nMessages.confirm,
        cancelButtonText: i18nMessages.cancel,
    }).then(function (result) {
        if (result.isConfirmed) {
            $("#loading").show();

            var xhr = new XMLHttpRequest();
            xhr.open("GET", "/employee/work-info-import-file", true);
            xhr.responseType = "arraybuffer";

            xhr.upload.onprogress = function (e) {
                if (e.lengthComputable) {
                    var percent = (e.loaded / e.total) * 100;
                    $(".progress-bar")
                        .width(percent + "%")
                        .attr("aria-valuenow", percent);
                    $("#progress-text").text(
                        i18nMessages.uploading + percent.toFixed(2) + "%"
                    );
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
                    link.download = "work_info_template.xlsx";
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
}


$(document).ajaxStart(function () {
    $("#loading").show();
});

$(document).ajaxStop(function () {
    $("#loading").hide();
});

function simulateProgress() {
    let progressBar = document.querySelector(".progress-bar");
    let progressText = document.getElementById("progress-text");

    let width = 0;
    let interval = setInterval(function () {
        if (width >= 100) {
            clearInterval(interval);
            progressText.innerText = uploadMessage;
            setTimeout(function () {
                document.getElementById("loading").style.display = "none";
            }, 3000);
            Swal.fire({
                text: importMessage,
                icon: "success",
                showConfirmButton: false,
                timer: 2000,
                timerProgressBar: true,
            });
            setTimeout(function () {
                $("#workInfoImport").removeClass("oh-modal--show");
                location.reload(true);
            }, 2000);
        } else {
            width++;
            progressBar.style.width = width + "%";
            progressBar.setAttribute("aria-valuenow", width);
            progressText.innerText = i18nMessages.uploading + width + "%";
        }
    }, 20);
}
