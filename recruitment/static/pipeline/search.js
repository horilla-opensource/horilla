$(document).ready(function () {
    $('#pipelineSearch').keyup(function (e) { 
      e.preventDefault();
      var search = $(this).val().toLowerCase();
      $('.candidate-container div.change-cand').each(function() {
        var candidate = $(this).attr('data-candidate');
        if (candidate.toLowerCase().includes(search)) {
          $(this).show();
        }else{
          $(this).hide();
        }
        let stageId = $(this).parent().attr('data-stage-id');
        var count = $(this).parent().find('.candidate:visible').length
        badge = $(`#stageCount${stageId}`).html(count);
        recruitmentId = $(this).parent().attr('data-recruitment-id')
        let recruitmentStageBadges = $(`[data-rec-stage-badge='${recruitmentId}']`)
        recruitmentStageBadges.each(function(){
          var count = $(`#tab_rec_${recruitmentId}`).find('.candidate.change-cand:visible').length
          $(`#recruitmentCandidateCount${recruitmentId}`).html(count);

        })
        
      });
    });
  });