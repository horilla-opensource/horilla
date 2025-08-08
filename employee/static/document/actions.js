var alreadyActionMessages = {
    approved: gettext("Some selected requests have already been approved."),
    rejected: gettext("Some selected requests have already been rejected."),
};

function validateDocsIds(event) {
    const ids = [];
    const checkedRows = $("[type=checkbox]:checked");
    const takeAction = $(event.currentTarget).data("action");
    let alreadyTakeAction = false;

    checkedRows.each(function () {
        const id = $(this).attr("id");
        const status = $(this).data("status");

        if (id) {
            if (status === takeAction) alreadyTakeAction = true;
            ids.push(id);
        }
    });

    if (ids.length === 0) {
        event.preventDefault();
        Swal.fire({
            text: i18nMessages.noRowsSelected,
            icon: "warning",
            confirmButtonText: i18nMessages.close,
        });
    } else if (alreadyTakeAction) {
        event.preventDefault();
        Swal.fire({
            text: alreadyActionMessages[takeAction],
            icon: "warning",
            confirmButtonText: i18nMessages.close,
        });
    } else {
        // Directly trigger action without confirmation
        const triggerId =
            takeAction === "approved"
                ? "#bulkApproveDocument"
                : "#bulkRejectDocument";
        $(triggerId).attr("hx-vals", JSON.stringify({ ids })).click();
    }
}


function highlightRow(checkbox) {
    checkbox.closest(".oh-user_permission-list_item").removeClass("highlight-selected");
    if (checkbox.is(":checked")) {
        checkbox.closest(".oh-user_permission-list_item").addClass("highlight-selected");
    }
}

function selectAllDocuments(event) {
    event.stopPropagation();
    const checkbox = event.currentTarget;
    const isChecked = checkbox.checked;

    const accordionBody = checkbox
        .closest(".oh-accordion-meta__header")
        .nextElementSibling;

    if (accordionBody) {
        const checkboxes = accordionBody.querySelectorAll('[type="checkbox"]');
        checkboxes.forEach(cb => cb.checked = isChecked);
    }
}
