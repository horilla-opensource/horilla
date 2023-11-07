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
  let stage = $(".recruitment_items");
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
      // count_element();
    },
  });
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

function countSequence(letmessage=true) {
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
    success: function (response) {
      if (response.type != "noChange" && letmessage) {

      $("#ohMessages").append(`
        <div class="oh-alert-container">
              <div class="oh-alert oh-alert--animated oh-alert--${response.type}">
                ${response.message}
        </div>`);
    }},
    error: (response) => {
      $("#ohMessages").append(`
            <div class="oh-alert-container">
                  <div class="oh-alert oh-alert--animated oh-alert--danger">
                    Something went wrong
            </div>`);
    },
  });
}

$('[data-container-list = "candidate"]').on("DOMNodeInserted", function (e) {
  var candidate = $(e.target);
  if (e.target.nodeType === Node.ELEMENT_NODE) {
    const insertedElement = $(e.target);

    // Check if the inserted element has the class you want to remove
    if (!insertedElement.hasClass("ui-sortable-placeholder")) {
      
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
              candidate.find("select").val(stageId)
              if (response.type != "noChange") {
                countSequence(false)
                setTimeout(() => {
                  $("#ohMessages").append(`
                    <div class="oh-alert-container">
                    <div class="oh-alert oh-alert--animated oh-alert--${response.type}">
                    ${response.message}
                    </div>
                    </div>`);
                }, 1000);
              }
          },
        });
      }else{
        countSequence()
      }
    }
  }
  
});

$(`.change-cand`).not('[data-container-list = "candidate"]').mouseup(function (e) {
  e.preventDefault()
  setTimeout(() => {
    var stageId = $(this).parent().attr("data-stage-id");
    var candidate = $(e.target).parents(".change-cand").last();
    var candidateId = candidate.attr("data-candidate-id");
    if (candidateId != null) {
      $.ajax({
        type: "post",
        url: `/recruitment/candidate-stage-update/${candidateId}/`,
        data: {
          csrfmiddlewaretoken: getCookie("csrftoken"),
          stageId: stageId,
        },
        success: function (response) {
          var selectElement = $("#stageChange" + candidateId);
          selectElement.val(stageId);
          var duration = 0;
          if (response.type != "noChange") {
              $("#ohMessages").append(`
              <div class="oh-alert-container">
              <div class="oh-alert oh-alert--animated oh-alert--${response.type}">
              ${response.message}
              </div>
              </div>`);
              duration = 1500;
          }
          countSequence(false);
        },
        error: (response) => {
          $("#ohMessages").append(`
            <div class="oh-alert-container">
              <div class="oh-alert oh-alert--animated oh-alert--danger">
                Something went wrong.
              </div>
            </div>`);
        },
      });
    }
  }, 200);
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
    success: function (response) {},
  });
});
