function closeTag(element) {
  var filterTagClass = $(element).attr("class");
  classArray = filterTagClass.split(" ");
  lastClass = classArray[classArray.length - 1];
  if (lastClass === "pipelineSearch") {
    $("#" + lastClass).val("");
    $("#" + lastClass).trigger("keyup");
  }
  var button = document.querySelector(
    ".oh-tabs__action-bar#filter_item button"
  );
  if (lastClass === "job_pos_id") {
    $("#" + lastClass).val("");
    $("#select2-" + lastClass + "-container").text("------------------");
    if (button) {
      button.click();
    }
  }
}

$(document).ready(function () {
  $("#pipelineSearch").keyup(function (e) {
    e.preventDefault();
    var search = $(this).val().toLowerCase();
    $(".candidate-container div.change-cand").each(function () {
      var candidate = $(this).attr("data-candidate");
      if (candidate.toLowerCase().includes(search)) {
        $(this).show();
      } else {
        $(this).hide();
      }
      let stageId = $(this).parent().attr("data-stage-id");
      var count = $(this).parent().find(".candidate:visible").length;
      badge = $(`#stageCount${stageId}`).html(count);
      $(`#stageCount${stageId}`).attr("title", `${count} candidates`);
    });
    $(".oh-filter-tag.filter-field.pipelineSearch").remove();
    if (search != "") {
      $(".oh-filter-tag-container.filter-value").append(
        '<span class="oh-filter-tag filter-field pipelineSearch" onclick="closeTag(this)">Search : ' +
          search +
          '<button class="oh-filter-tag__close" id="close"><ion-icon name="close-outline" role="img" class="md hydrated" aria-label="close outline"></ion-icon></button></span>'
      );
    }
  });
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

  function job_Position() {
    let search = $("#job_pos_id").val().toLowerCase();
    $(".oh-filter-tag.filter-field.job_pos_id").remove();
    if (search != "") {
      job = $("[data-job-position]:visible");
      job.each(function () {
        var candidate = $(this).attr("data-job-position");
        if (candidate.toLowerCase().includes(search)) {
          $(this).show();
        } else {
          $(this).hide();
        }
      });
      $(".oh-filter-tag-container.filter-value").append(
        '<span class="oh-filter-tag filter-field job_pos_id" onclick="closeTag(this)">Job position : ' +
          search +
          '<button class="oh-filter-tag__close" id="close"><ion-icon name="close-outline" role="img" class="md hydrated" aria-label="close outline"></ion-icon></button></span>'
      );
    }
  }

  $("#filter_item").on("click", function () {
    var candidate = $("[data-job-position]");
    candidate.each(function () {
      $(this).show();
    });
    $(".pipeline_items").each(function () {
      $(this).removeClass("d-none");
    });
    job_Position();
    count_element();
  });
  $(".oh-tabs__tab").on("click", function () {
    $(".pipeline_items").each(function () {
      $(this).removeClass("d-none");
    });
    job_Position();
    count_element();
  });
});
