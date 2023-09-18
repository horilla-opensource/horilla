var filterCount = 0;
function closeTag(element) {
  var filterTagClass = $(element).attr("class");
  $(element).remove();
  var classArray = filterTagClass.split(" ");
  var lastClass = classArray[classArray.length - 1];
  $("#" + lastClass).val("");
  if (lastClass === "job_position_id") {
    $("#select2-" + lastClass + "-container").text("------------------");
  }
  var button = document.querySelector(
    ".oh-tabs__action-bar#filter_item button"
  );
  if (button) {
    button.click();
  }
}
$(document).ready(function () {
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

  $("#search").keyup(function (e) {
    e.preventDefault();
    let search = $(this).val().toLowerCase();
    $(".onboarding_items").each(function () {
      $(this).removeClass("d-none");
    });
    cands = $("[data-candidate]");
    cands.each(function () {
      var candidate = $(this).attr("data-candidate");
      if (candidate.toLowerCase().includes(search)) {
        $(this).show();
      } else {
        $(this).hide();
      }
    });
    $(".oh-filter-tag.filter-field.search").remove();
    if (search != "") {
      $(".oh-filter-tag-container.filter-value").append(
        '<span class="oh-filter-tag filter-field search" onclick="closeTag(this)">Search : ' +
          search +
          '<button class="oh-filter-tag__close" id="close"><ion-icon name="close-outline" role="img" class="md hydrated" aria-label="close outline"></ion-icon></button></span>'
      );
    }
    count_element();
  });

  function job_Position() {
    let search = $("#job_position_id").val().toLowerCase();
    if (search != "") {
      filterCount++;
      job = $("[data-job-position]:visible");
      job.each(function () {
        var candidate = $(this).attr("data-job-position");
        if (candidate.toLowerCase().includes(search)) {
          $(this).show();
        } else {
          $(this).hide();
        }
      });
      $(".oh-filter-tag.filter-field.job_position_id").remove();
      $(".oh-filter-tag-container.filter-value").append(
        '<span class="oh-filter-tag filter-field job_position_id" onclick="closeTag(this)">Job position : ' +
          search +
          '<button class="oh-filter-tag__close" id="close"><ion-icon name="close-outline" role="img" class="md hydrated" aria-label="close outline"></ion-icon></button></span>'
      );
      count_element();
    }
  }

  function join_date() {
    let date = $("#join_date").val();
    if (date != "") {
      filterCount++;
      var dateObject = new Date(date);

      var monthNames = [
        "Jan.",
        "Feb.",
        "March",
        "April",
        "May",
        "June",
        "July",
        "Aug.",
        "Sept.",
        "Oct.",
        "Nov.",
        "Dec.",
      ];

      var month = monthNames[dateObject.getMonth()];
      var day = dateObject.getDate();
      var year = dateObject.getFullYear();

      var search = month + " " + day + ", " + year;
      let dates = $("[data-join-date]:visible");
      dates.each(function () {
        var candidate = $(this).attr("data-join-date");

        if (candidate.includes(search)) {
          $(this).show();
        } else {
          $(this).hide();
        }
      });
      $(".oh-filter-tag.filter-field.join_date").remove();
      $(".oh-filter-tag-container.filter-value").append(
        '<span class="oh-filter-tag filter-field join_date" onclick="closeTag(this)">Join date : ' +
          search +
          '<button class="oh-filter-tag__close" id="close"><ion-icon name="close-outline" role="img" class="md hydrated" aria-label="close outline"></ion-icon></button></span>'
      );
      count_element();
    }
  }

  function portal() {
    let search = $("#portal_stage").val();

    if (search != "") {
      filterCount++;
      let portal_items = $("[data-portal-count]:visible");
      portal_items.each(function () {
        var candidate = $(this).attr("data-portal-count");
        if (candidate.includes(search)) {
          $(this).show();
        } else {
          $(this).hide();
        }
      });
      $(".oh-filter-tag.filter-field.portal_stage").remove();
      $(".oh-filter-tag-container.filter-value").append(
        '<span class="oh-filter-tag filter-field portal_stage" onclick="closeTag(this)">Portal stage : ' +
          search +
          '<button class="oh-filter-tag__close" id="close"><ion-icon name="close-outline" role="img" class="md hydrated" aria-label="close outline"></ion-icon></button></span>'
      );
      count_element();
    }
  }
  function join_date_range() {
    let start_date = $("#join_date_start").val();
    let end_date = $("#join_date_end").val();

    if (start_date || end_date) {
      filterCount++;
      let visibleDates = $("[data-join-date]:visible");

      visibleDates.each(function () {
        let candidateDateString = $(this).data("join-date");
        let candidateDate = new Date(candidateDateString);
        if (!isNaN(candidateDate)) {
          let showElement = true;

          if (start_date && !end_date) {
            showElement = candidateDate >= new Date(start_date);
          } else if (!start_date && end_date) {
            showElement = candidateDate <= new Date(end_date);
          } else if (start_date && end_date) {
            showElement =
              candidateDate >= new Date(start_date) &&
              candidateDate <= new Date(end_date);
          }

          if (showElement) {
            $(this).show();
          } else {
            $(this).hide();
          }
        } else {
          $(this).hide();
        }
      });

      count_element();
    } else {
    }
    $(".oh-filter-tag.filter-field.join_date_end").remove();
    $(".oh-filter-tag.filter-field.join_date_start").remove();
    if (start_date.length) {
      $(".oh-filter-tag-container.filter-value").append(
        '<span class="oh-filter-tag filter-field join_date_start" onclick="closeTag(this)">Join date from : ' +
          start_date +
          '<button class="oh-filter-tag__close" id="close"><ion-icon name="close-outline" role="img" class="md hydrated" aria-label="close outline"></ion-icon></button></span>'
      );
    }
    if (end_date.length) {
      $(".oh-filter-tag-container.filter-value").append(
        '<span class="oh-filter-tag filter-field join_date_end" onclick="closeTag(this)">Join date to : ' +
          end_date +
          '<button class="oh-filter-tag__close" id="close"><ion-icon name="close-outline" role="img" class="md hydrated" aria-label="close outline"></ion-icon></button></span>'
      );
    }
  }

  $("#filter_item").on("click", function () {
    filterCount = 0;
    var candidate = $("[data-job-position]");
    candidate.each(function () {
      $(this).show();
    });
    $(".onboarding_items").each(function () {
      $(this).removeClass("d-none");
    });
    job_Position();
    join_date();
    portal();
    join_date_range();
    $("#filterCount").empty();
    if (filterCount > 0) {
      $("#filterCount").text("(" + filterCount + ")");
    }
  });

  $(".oh-tabs__tab").on("click", function () {
    $(".onboarding_items").each(function () {
      $(this).removeClass("d-none");
    });
    job_Position();
    join_date();
    portal();
    join_date_range();
  });

  $("#job_position_id").select2();
  $("#portal_stage").select2();
});
