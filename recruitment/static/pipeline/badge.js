
$(document).ready(function () {
    $('.stage-change').on('change', function() {
      // Your code here
      var candidateId = $(this).attr('data-candidate-id');
      const elementToMove = $(`[data-change-cand-id=${candidateId}]`)
      const stageContainerId = $(this).val();
      $(`#candidateContainer${stageContainerId}`).append(elementToMove);     
    
    });
  
    
  
    // Bind the DOMNodeInserted event listener
    $('.candidate-container').on('DOMNodeInserted', function(event) {
      var addedNode = event.target;
      // Check if the added node is a div with the class name "change-cand"
      if (addedNode.nodeType === 1 && $(addedNode).hasClass('change-cand')) {
        let count = $(this).children().filter('.change-cand').length;
        var stageId = $(this).attr('data-stage-id');
        var stageBadge = $(`#stageCount${stageId}`)
        stageBadge.html(count)
        stageBadge.attr("title", `${count} candidates`);

      }
    });
  
    $('.candidate-container').on('DOMNodeRemoved', function(event) {
    var removedNode = event.target;
    // Check if the removed node is a div with the class name "change-cand"
    if (removedNode.nodeType === 1 && $(removedNode).hasClass('change-cand')) {
      let count = $(this).children().filter('.change-cand').length;
      var stageId = $(this).attr('data-stage-id');
      var stageBadge = $(`#stageCount${stageId}`)
      count_element()
      stageBadge.html(count-1)
      stageBadge.attr("title", `${count-1} candidates`);
    }
    });
  });