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

var candidateId = null;

$(".candidate").mousedown(function () {
  window["candidateId"] = $(this).attr("data-candidate-id");
});

var stageSequence = null;
var recruitmentId = null;
var oldSequences = [];
var stages = [];
var elements = [];

function stageSequenceGet(stage) {
  var sequence = {};
  var stageId = stage.attr("id");
  console.log(stageId);
  var stageContainers = stage.parent().parent().find("[data-container]");
  let totalStages = stageContainers.length;
  $.each(stageContainers, function (index, element) {
    sequence[$(element).attr("data-stage-id")] = index + 1;
  });
  $.ajax({
    type: "POST",
    url: "/recruitment/stage-sequence-update",
    data: {
      csrfmiddlewaretoken: getCookie("csrftoken"),
      sequence: JSON.stringify(sequence),
    },
    success: function (response) {
      console.log(response);
    },
  });

  console.log("---------");
  console.log(sequence);
}
$(".stage").mousedown(function () {
  window["stageSequence"] = $(this).attr("data-stage-sequence");
  window["recruitmentId"] = $(this).attr("data-recruitment-id");
  $(".stage").each(function (i, obj) {
    if (recruitmentId == $(obj).attr("data-recruitment-id")) {
      window["stages"].push($(obj).attr("data-stage-id"));
      window["oldSequences"].push($(obj).attr("data-stage-sequence"));
    }
  });
});

$(".stage").mouseup(function () {
  var newSequences = [];
  setTimeout(() => {
    stageSequenceGet($(this));
  }, 0);
  $(".stage").each(function (i, obj) {
    if (
      recruitmentId == $(obj).attr("data-recruitment-id") ||
      $(obj).attr("data-recruitment-id") == undefined
    ) {
      newSequences.push($(obj).attr("data-stage-sequence"));
      if ($(obj).attr("data-recruitment-id") != undefined) {
        window["elements"].push(obj);
      }
    }
  });

  if (newSequences.includes(undefined)) {
    var newSequences = newSequences.filter((e) => e !== stageSequence);
    var newSequences = newSequences.map((elem) =>
      elem === undefined ? stageSequence : elem
    );
  }

  oldSequences = JSON.stringify(oldSequences);
  stages = JSON.stringify(stages);

  elements.forEach(function (element) {
    for (let index = 0; index < newSequences.length; index++) {
      const sequence = newSequences[index];
      if (sequence == $(element).attr("data-stage-sequence")) {
        $(element).attr("data-stage-sequence", `${index + 1}`);
        return;
      }
    }
  });

  window["stageSequence"] = null;
  window["recruitmentId"] = null;
  window["oldSequences"] = [];
  window["elements"] = [];
  window["stages"] = [];
});

function countSequence(element) {
  // let childs = element.parent().find(".change-cand")
  let childs = $(".change-cand");
  let data = {};
  $.each(childs, function (index, elem) {
    $(elem).attr("data-sequence", index + 1);
    data[elem.getAttribute("data-candidate-id")] = index + 1;
  });
  $.ajax({
    type: "post",
    url: "/recruitment/candidate-sequence-update",
    data: {
      csrfmiddlewaretoken: getCookie("csrftoken"),
      sequenceData: JSON.stringify(data),
    },
    dataType: "dataType",
    success: function (response) {
      $("#ohMessages").append(`
            <div class="oh-alert-container">
                  <div class="oh-alert oh-alert--animated oh-alert--${response.type}">
                    ${response.message}
            </div>`);
    },
  });
}

$("[data-container='candidate']").on("DOMNodeInserted", function (e) {
  var candidate = $(e.target);
  setInterval(countSequence(candidate), 500);
  // countSequence(candidate)
  var stageId = $(this).attr("data-stage-id");
  candidateId = $(candidate).attr("data-candidate-id");
  if (candidateId != null) {
    $.ajax({
      type: "post",
      url: `/recruitment/candidate-stage-update/${candidateId}/`,
      data: {
        csrfmiddlewaretoken: getCookie("csrftoken"),
        stageId: stageId,
      },
      success: function (response) {
        var candidateId = $(this).attr("data-candidate-id");
        setInterval(countSequence(candidate), 500);

        //  console.log(response);
        $("#ohMessages").append(`
            <div class="oh-alert-container">
                  <div class="oh-alert oh-alert--animated oh-alert--${response.type}">
                    ${response.message}
            </div>`);
      },
    });
  }
});

$(".schedule").change(function (e) {
  date = this.value;
  candidateId = $(this).data("candidate-id");
  $.ajax({
    type: "post",
    url: `/recruitment/candidate-schedule-date-update`,
    data: {
      csrfmiddlewaretoken: getCookie("csrftoken"),
      candidateId: candidateId,
      date: date,
    },
    success: function (response) {
      // console.log(response);
    },
  });
});
