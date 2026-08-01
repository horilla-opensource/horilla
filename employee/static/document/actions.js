function validateDocsIds(event) {
    // Bulk Reject reads its ids straight off #selectedInstances itself via
    // hx-vals="js:..." on the button (see DocumentRequestNav), evaluated
    // fresh by htmx at request time, so nothing more is needed for it here
    // beyond the empty-selection warning below.
    //
    // Bulk Approve has no hx-vals at all - it goes through window.confirm's
    // global SweetAlert override (see index.js), which reads a plain JSON
    // hx-vals attribute *after* the user confirms, so it still needs this
    // handler to set that attribute imperatively before the confirm
    // resolves. A `js:` expression won't work there since that override does
    // its own `JSON.parse` on the raw attribute rather than letting htmx
    // evaluate it.
    const ids = JSON.parse($("#selectedInstances").attr("data-ids") || "[]");
    const takeAction = $(event.currentTarget).data("action");

    if (ids.length === 0) {
        event.preventDefault();
        Swal.fire({
            text: i18nMessages.noRowsSelected,
            icon: "warning",
            confirmButtonText: i18nMessages.close,
        });
    } else if (takeAction === "approved") {
        $(event.currentTarget).attr("hx-vals", JSON.stringify({ ids }));
    }
}


function highlightRow(checkbox) {
    // This file is also loaded on the legacy document request pages
    // (employee/templates/documents/requests.html,
    // horilla_theme/templates/documents/requests.html), whose rows are
    // ".oh-user_permission-list_item" wrappers rather than plain <tr>s -
    // handle that shape first. On the standard list table used by the
    // Document Requests tab under /employee/requests/, fall back to the
    // same <tr>-based highlighting index.js's global highlightRow() does,
    // so this definition doesn't just silently no-op there and shadow the
    // one that actually matches the row markup.
    var $legacyRow = checkbox.closest(".oh-user_permission-list_item");
    if ($legacyRow.length) {
        $legacyRow.removeClass("highlight-selected");
        if (checkbox.is(":checked")) {
            $legacyRow.addClass("highlight-selected");
        }
        return;
    }

    checkbox.closest(".oh-sticky-table__tr").removeClass("highlight-selected");
    checkbox.closest("tr").removeClass("highlight-selected");
    if (checkbox.is(":checked")) {
        checkbox.closest(".oh-sticky-table__tr").addClass("highlight-selected");
        checkbox.closest("tr").addClass("highlight-selected");
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
