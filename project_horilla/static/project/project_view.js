$(document).ready(function(){
    $("#filter-project").keyup(function (e) {
        $(".project-view-type").attr("hx-vals", `{"search":"${$(this).val()}"}`);
    });
    $(".project-view-type").click(function (e) {
        let view = $(this).data("view");
        var currentURL = window.location.href;
        if (view != undefined){
          // Check if the query string already exists in the URL
          if (/\?view=[^&]+/.test(currentURL)) {
            // If the query parameter ?view exists, replace it with the new value
            newURL = currentURL.replace(/\?view=[^&]+/, "?view="+view);
          }
          else {
            // If the query parameter ?view does not exist, add it to the URL
            var separator = currentURL.includes('?') ? '&' : '?';
            newURL = currentURL + separator + "view="+view;
          }

          history.pushState({}, "", newURL);
        $("#filter-project").attr("hx-vals", `{"view":"${view}"}`);
        $('#timesheetForm').attr("hx-vals", `{"view":"${view}"}`);
      }
    });
});
