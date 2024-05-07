$(`.change-ticket`).mouseup(function (e) {
    if (!$(e.target).hasClass('action-button')){
      e.preventDefault()
      setTimeout(() => {
        var status = $(this).parent().attr("data-ticket-id");
        var ticket = $(e.target).parents(".change-ticket").last();
        var ticketID = ticket.attr("data-ticket-id");
        if (ticketID != null) {
          $.ajax({
            type: "post",
            url: `/helpdesk/change-ticket-status/${ticketID}/`,
            data: {
              csrfmiddlewaretoken: getCookie("csrftoken"),
              "status": status,
            },
            success: function (response) {
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
              // countSequence(false);
            },
            error: () => {
              console.log("error")
            },
          });
        }
      }, 200);
    }

  });
