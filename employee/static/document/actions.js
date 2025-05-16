var confirmMessages = {
    approved: {
        ar: "هل ترغب حقًا في الموافقة على جميع الطلبات المحددة؟",
        de: "Möchten Sie wirklich alle ausgewählten Anfragen genehmigen?",
        es: "¿Realmente quieres aprobar todas las solicitudes seleccionadas?",
        en: "Do you really want to approve all the selected requests?",
        fr: "Voulez-vous vraiment approuver toutes les demandes sélectionnées?",
    },
    rejected: {
        ar: "هل تريد حقًا رفض جميع الطلبات المحددة؟",
        de: "Möchten Sie wirklich alle ausgewählten Anfragen ablehnen?",
        es: "¿Realmente deseas rechazar todas las solicitudes seleccionadas?",
        en: "Do you really want to reject all the selected requests?",
        fr: "Voulez-vous vraiment rejeter toutes les demandes sélectionnées?",
    },
};

var alreadyActionMessages = {
    approved: {
        ar: "بعض الطلبات المحددة تم الموافقة عليها مسبقًا.",
        de: "Einige ausgewählte Anfragen wurden bereits genehmigt.",
        es: "Algunas solicitudes seleccionadas ya han sido aprobadas.",
        en: "Some selected requests have already been approved.",
        fr: "Certaines demandes sélectionnées ont déjà été approuvées.",
    },
    rejected: {
        ar: "بعض الطلبات المحددة تم رفضها مسبقًا.",
        de: "Einige ausgewählte Anfragen wurden bereits abgelehnt.",
        es: "Algunas solicitudes seleccionadas ya han sido rechazadas.",
        en: "Some selected requests have already been rejected.",
        fr: "Certaines demandes sélectionnées ont déjà été rejetées.",
    },
};

function validateDocsIds(event) {
    getCurrentLanguageCode(function (lang) {
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
            var norowMessages = {
                ar: "لم يتم تحديد أي صفوف.",
                de: "Es wurden keine Zeilen ausgewählt.",
                es: "No se han seleccionado filas.",
                en: "No rows have been selected.",
                fr: "Aucune ligne n'a été sélectionnée.",
            };
            event.preventDefault();
            Swal.fire({
                text: norowMessages[lang] || norowMessages.en,
                icon: "warning",
                confirmButtonText: "Close",
            });
        } else if (alreadyTakeAction) {
            event.preventDefault();
            Swal.fire({
                text:
                    alreadyActionMessages[takeAction][lang] ||
                    alreadyActionMessages[takeAction].en,
                icon: "warning",
                confirmButtonText: "Close",
            });
        } else {
            // Directly trigger action without confirmation
            const triggerId =
                takeAction === "approved"
                    ? "#bulkApproveDocument"
                    : "#bulkRejectDocument";
            $(triggerId).attr("hx-vals", JSON.stringify({ ids })).click();
        }
    });
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
