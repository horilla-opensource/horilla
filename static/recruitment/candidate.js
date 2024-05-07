function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
  }
$(document).ready(function () {
    var stages = []
    $('#recruitment').change(function (e) {
        var recruitmentId = $(this).val()
        if (recruitmentId) {

            var a =  $.ajax({
                type: "post",
                url: `/recruitment/recruitment-stage-get/${recruitmentId}/`,
                data: {
                    'csrfmiddlewaretoken': getCookie('csrftoken'),
                },
                success: function (response) {
                    stages = JSON.parse(response['stages']);
                    let optionData = '';
                    for (let index = 0; index < stages.length; index++) {
                        const element = stages[index];
                        stage = element['fields']
                        if (element['pk']) {
                            optionData += `<option value="${element['pk']}">${stage['stage']}</option>`
                        }
                    }
                    $("#stage").html(optionData);
                }
            });
        }
        else{
            $("#stage").html('');

        }

        });
});
