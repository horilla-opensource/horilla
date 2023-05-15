
// this function is used to generate csrf token
function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== "") {
    const cookies = document.cookie.split(";");
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      // Does this cookie string begin with the name we want?
      if (cookie.substring(0, name.length + 1) === (name + "=")) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

$(document).ready(function () {
  
    // answer status checking 
    $('.feedback-status').each(function(){
      var statusEl = $(this)
      var feedbackId = statusEl.attr('x-data-feedback-id')
      var employeeId = statusEl.attr('x-data-employee-id')
      var csrf_token = getCookie("csrftoken")
      
      $.ajax({
            url: '/pms/feedback-status',
            type: "POST",
            dataType: "json",
            data: {'employee_id':employeeId,'feedback_id': feedbackId, 'csrfmiddlewaretoken':csrf_token},
            headers: {
              "X-Requested-With": "XMLHttpRequest",
              
            },
            success: (data) => {
              // based on response the span element text will be added
              statusEl.text(data.status) 
              if (data.status === 'Completed') {
                statusEl.prev().attr('class','oh-dot oh-dot--small oh-dot--success me-1')
              }else{
                statusEl.prev().attr('class','oh-dot oh-dot--small oh-dot--danger me-1')
              }
            },
            error: (error) => {
              console.log('Error',error);
            
            }
          });
      
      })
    
  });
  