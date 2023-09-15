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


function count_element() {
  let stage = $(".onboarding_items");
  let count = $(".stage_count");
  let nos = [];
  for (i = 0; i < stage.length; i++) {
    nos.push($(stage[i]).find("[data-candidate]:visible").length);
  }

  $.each(nos, function (index, value1) {
    var value2 = count[index];
    $(value2).text(value1);
    $(value2).attr("title", `${value1} candidates`);
  });
}

function countSequence(element) {
  // let childs = element.parent().find(".change-cand")
  setTimeout(() => {
    let childs = $(".oh-kanban__card.candidate");
    let data = {};
    $.each(childs, function (index, elem) {
      $(elem).attr("data-sequence", index + 1);
      data[elem.getAttribute("id")] = index + 1;
    });
    $.ajax({
      type: "post",
      url: "/onboarding/candidate-sequence-update",
      data: {
        csrfmiddlewaretoken: getCookie("csrftoken"),
        sequenceData: JSON.stringify(data),
      },
      success: function (response) {
        var alertContainer = $('<div class="oh-alert-container">');
        if (response.type == "info") {
          var alertDiv = $(
            `<div class="oh-alert oh-alert--animated oh-alert--${response.type}">`
          ).text(response.message);

          alertContainer.append(alertDiv);
          $(".messages").html(alertContainer);
        }
      },
    });
  }, 0);
}

function updateStageSequence(parentElement) {
  let childs = parentElement.find(".oh-kanban__section.stage");
  let data = {};
  $.each(childs, function (index, elem) {
    $(elem).attr("data-sequence", index + 1);
    data[elem.getAttribute("data-stage-id")] = index + 1;
  });
  $.ajax({
    type: "post",
    url: "/onboarding/stage-sequence-update",
    data: {
      csrfmiddlewaretoken: getCookie("csrftoken"),
      sequenceData: JSON.stringify(data),
    },
    success: function (response) {
      var alertContainer = $('<div class="oh-alert-container">');
      if (response.type == "success") {
        var alertDiv = $(
          `<div class="oh-alert oh-alert--animated oh-alert--${response.type}">`
        ).text(response.message);

        alertContainer.append(alertDiv);
        $(".messages").html(alertContainer);
      }
    },
  });
}
$(".oh-kanban__section.stage").mouseup(function () {
  let recruitmentId = $(this).attr("data-recruitment-id");
  let parentTab = $(`#tab_${recruitmentId}`);
  setTimeout(() => {
    updateStageSequence(parentTab);
  }, 0);
});

$(document).ready(function () {
  $(".candidate[data-candidate-id]").mouseup(function () {
    setTimeout(() => {
      let stageId = $(this).parent().attr("data-stage-id");
      let candidateId = $(this).attr("data-candidate-id");
      let recruitmentId = $(this).attr("data-recruitment-id");
      // ajax request here.. to update the stage of the candidates
      let candidateNow = $(this).attr("data-candidate-now");
      countSequence($(this));
      if (candidateNow != stageId) {
        $.ajax({
          type: "post",
          url: `candidate-stage-update/${candidateId}/${recruitmentId}/?is_ajax=true`,
          data: {
            csrfmiddlewaretoken: getCookie("csrftoken"),
            is_ajax: true,
            stage: stageId,
          },
          success: function (response) {
            var alertContainer = $('<div class="oh-alert-container">');
            var alertDiv = $(
              `<div class="oh-alert oh-alert--animated oh-alert--${response.type}">`
            ).text(response.message);

            alertContainer.append(alertDiv);
            setTimeout(() => {
              $(".messages").html(alertContainer);
            }, 1000);
            count_element();
          },
        });
        $(this).attr("data-candidate-now", stageId);
      }
    }, 0);
  });
});
