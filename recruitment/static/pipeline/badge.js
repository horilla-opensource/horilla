$(document).ready(function () {
  $(".stage-change").on("change", function (e) {
    e.preventDefault();

    // Your code here
    var candidateId = $(this).attr("data-candidate-id");
    var stageId = $(this).val();
    const elementToMove = $(`[data-change-cand-id=${candidateId}]`);
    $(`#candidateContainer${stageId}`).append(elementToMove);
    setTimeout(() => {
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
          selectElement.attr("data-stage-id", stageId);
          var duration = 0;
          if (response.type != "noChange") {
            $("#ohMessages").append(`
              <div class="oh-alert-container">
              <div class="oh-alert oh-alert--animated oh-alert--${response.type}">
              ${response.message}
              </div>
              </div>`);
            duration = 1500;
          } else {
            countSequence(false);
          }
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
    }, 100);
  });

  // Bind the DOMNodeInserted event listener
  $(".candidate-container").on("DOMNodeInserted", function (event) {
    var addedNode = event.target;
    // Check if the added node is a div with the class name "change-cand"
    if (addedNode.nodeType === 1 && $(addedNode).hasClass("change-cand")) {
      let count = $(this).children().filter(".change-cand").length;
      var stageId = $(this).attr("data-stage-id");
      var stageBadge = $(`#stageCount${stageId}`);
      stageBadge.html(count);
      stageBadge.attr("title", `${count} candidates`);
      $(this).find(".stage-change").attr("data-stage-id",stageId)
    }
  });

  $(".candidate-container").on("DOMNodeRemoved", function (event) {
    var removedNode = event.target;
    // Check if the removed node is a div with the class name "change-cand"
    if (removedNode.nodeType === 1 && $(removedNode).hasClass("change-cand")) {
      let count = $(this).children().filter(".change-cand").length;
      var stageId = $(this).attr("data-stage-id");
      var stageBadge = $(`#stageCount${stageId}`);
      count_element();
      stageBadge.html(count - 1);
      stageBadge.attr("title", `${count - 1} candidates`);
    }
  });
});
