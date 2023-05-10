$(document).ready(function(){
    $("#search").keyup(function(e){
        e.preventDefault();
        var search = $(this).val().toLowerCase();
        $('.candidate-container div.change-cand').each(function() {
            var candidate = $(this).attr('data-candidate');
            if (candidate.toLowerCase().includes(search)) {
                $(this).show();
              }else{
                $(this).hide();
              }
        })
    });
});