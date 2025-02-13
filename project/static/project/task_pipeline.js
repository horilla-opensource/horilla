$(document).ready(function(){
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

    // for the search function
    $("#filter-task").keyup(function (e) {
      var search = $(this).val().toLowerCase();
      var view = $(this).data('view')
      if (view == 'list') {
        $('.task_row').each(function () {
          var task = $(this).data('task')
          if (task.includes(search)) {
           $(this).show();  
          } else {
           $(this).hide();
          } 
         })
        
      } else {
        $('.task').each(function () {
          var task = $(this).data('task')
          if (task.includes(search)) {
           $(this).show();  
          } else {
           $(this).hide();
          } 
         })
      }
    });
    

    $('.task').mousedown(function(){
        window ['previous_task_id'] = $(this).attr('data-task-id')
        window ['previous_stage_id'] = $(this).parent().attr('data-stage-id')   
    });

    $(".tasks-container").on("DOMNodeInserted", function (e) {
        var updated_task_id = $(e.target).attr('data-task-id');
        var updated_stage_id = $(this).attr("data-stage-id");
        if (updated_task_id != null) {
          var new_seq = {}
          var task_container = $(this).children(".task")
          task_container.each(function(i, obj) {
            new_seq[$(obj).data('task-id')] = i
          });
          $.ajax({
              type: "post",
              url: '/project/drag-and-drop-task',
              data: {
              csrfmiddlewaretoken: getCookie("csrftoken"),
              updated_task_id: updated_task_id,
              updated_stage_id : updated_stage_id,
              previous_task_id : previous_task_id,
              previous_stage_id : previous_stage_id,
              sequence:JSON.stringify(new_seq),
              },
              success: function(response){
                if (response.change) {  // Check if the 'change' attribute in the response is True
                  $("#ohMessages").append(`
                      <div class="oh-alert-container">
                          <div class="oh-alert oh-alert--animated oh-alert--${response.type}">
                              ${response.message}
                          </div>
                      </div>`);
              }
              },
          });
        };
    });

    

    $('.stage').mouseup(function(){
      window['previous_stage_id'] = $(this).attr('data-stage-id')
      window['previous_sequence'] = $(this).attr('data-sequence')
      setTimeout(function() {
        var new_seq = {}
        $('.stage').each(function(i, obj) {
          new_seq[$(obj).attr('data-stage-id')] = i
        });
        $.ajax({
          type: 'post',
          url: '/project/drag-and-drop-stage',
          data:{
            csrfmiddlewaretoken: getCookie("csrftoken"),
            sequence:JSON.stringify(new_seq),
          },
          success: function(response) {
            if (response.change) {  // Check if the 'change' attribute in the response is True
                $("#ohMessages").append(`
                    <div class="oh-alert-container">
                        <div class="oh-alert oh-alert--animated oh-alert--${response.type}">
                            ${response.message}
                        </div>
                    </div>`);
            }
        },
        })
      }, 100);
    })  

    $("#filter-task").keyup(function (e) {
      $(".task-view-type").attr("hx-vals", `{"search":"${$(this).val()}"}`);
    });
    $(".task-view-type").click(function (e) {
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
          newURL = currentURL + separator + "view=card";
        }

        history.pushState({}, "", newURL);
      $("#filter-task").attr("hx-vals", `{"view":"${view}"}`);
      $('#timesheetForm').attr("hx-vals", `{"view":"${view}"}`);
    }
    });
});