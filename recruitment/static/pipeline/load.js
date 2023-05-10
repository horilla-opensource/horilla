$(document).on("htmx:load", "#activitySidebar", function (event) {
  $('[data-target="#updateNoteModal"]').click(function (e) {
    $("#updateNoteModal").addClass("oh-modal--show");
  });
});
$(document).on("htmx:load", "#modalContent", function () {
  $(".oh-modal__close").click(function (e) {
    $("#updateNoteModal").removeClass("oh-modal--show");
  });
});
$(document).on("htmx:load", "#activitySidebar", function (event) {
  $('[data-target="#updateNoteModal"]').click(function (e) {
    $("#updateNoteModal").addClass("oh-modal--show");
  });
});
$(document).on("htmx:load", "#modalContent", function () {
  $(".oh-modal__close").click(function (e) {
    $("#updateNoteModal").removeClass("oh-modal--show");
  });
});

