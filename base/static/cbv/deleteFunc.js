function getCSRFToken() {
    return document.querySelector('meta[name="csrf-token"]').getAttribute('content');
}
// #846
function deleteItem(url, message) {
    Swal.fire({
        text: message,
        icon: "question",
        showCancelButton: true,
        confirmButtonColor: "#d33",
        cancelButtonColor: "#6c757d",
        confirmButtonText: typeof i18nMessages !== "undefined" ? i18nMessages.confirm : "Confirm"
    }).then((result) => {
        if (result.isConfirmed) {
            const form = document.createElement('form');
            form.setAttribute('action', url);
            form.setAttribute('method', 'post');
            const csrfTokenInput = document.createElement('input');
            csrfTokenInput.setAttribute('type', 'hidden');
            csrfTokenInput.setAttribute('name', 'csrfmiddlewaretoken');
            csrfTokenInput.value = getCSRFToken();
            form.appendChild(csrfTokenInput);
            document.body.appendChild(form);
            form.submit();
        }
    });
}
