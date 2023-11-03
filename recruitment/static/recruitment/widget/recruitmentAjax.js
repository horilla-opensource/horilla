$(document).ready(function () {
  $(`[data-widget="ajax-widget"]select`).css({
    "width": "100% ",
    "height": "50px",
    "display": "flex",
    "border": "1px solid hsl(213deg,22%,84%)",
    "border-radius": "0rem",
    "padding": "0.8rem 1.25rem",
    "color": "hsl(0deg,0%,11%)",
  });

  function checkInitial() {
    const initialValue = $("#id_recruitment_id").val();
    if (initialValue == "") {
      $("#id_job_position_id").hide();
    } else {
      $("#id_job_position_id").show();
    }
  }
  checkInitial();
  $("#id_recruitment_id").change(function (e) {
    e.preventDefault();
    checkInitial();
    var recId = $(this).val();

    $.ajax({
      type: "get",
      url: "/recruitment/get-open-positions",
      data: { recId: recId },
      success: function (response) {
        var openPositions = JSON.parse(response.openPositions);
        recruitmentInfo = JSON.parse(response.recruitmentInfo);
        var selectElement = $("#id_job_position_id");

        // Clear existing options
        selectElement.empty();

        // Add new options
        openPositions.forEach(function (position) {
          var option = $("<option>")
            .val(position.pk)
            .text(position.fields.job_position);
          selectElement.append(option);
        });
        // add the recruitment description
        // Add the recruitment description with line breaks
        var description = recruitmentInfo[0].fields.description;
        var formattedDescription = description.replace(/\n/g, "<br>");
        $("#recruitmentInfoBody").html(formattedDescription);
      },
    });
    // $.ajax({
    //   type: "GET",
    //   url: "/recruitment/recruitment-application-survey",
    //   data: {recId:recId},
    //   success: function (response) {
    //     $("#recruitmentSurveyBody").html(response);
    //   }
    // });
  });
});
