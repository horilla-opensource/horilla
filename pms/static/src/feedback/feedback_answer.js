
$(document).ready(function () {
    // answer color for likert
    var booleanText = $('.boolean-colour').text().trim()
    var booleanEl = $('.boolean-colour')
    var red = "oh-input-picker--1"
    var orange = "oh-input-picker--2"
    var yellow = "oh-input-picker--3"
    var light_green = "oh-input-picker--4"
    var green = "oh-input-picker--5"
  
    $('.likert-colour').each(function() {
      var likertText = $(this).text().trim()
  
      if (likertText === 'Strongly Agree'){
        $(this).addClass(green)
      }
      else if (likertText === 'Agree'){
        $(this).addClass(light_green)
      }
      else if (likertText === 'Neutral'){
        $(this).addClass(yellow)
      }
      else if (likertText === 'Disagree'){
        $(this).addClass(orange)
      }
      else if (likertText === 'Strongly Disagree'){
        $(this).addClass(red)
      }
    });
  
    // boolean text colour adding
    $('.boolean-colour').each(function() {
      var booleanText = $(this).text().trim()
  
      if (booleanText === 'yes'){
        $(this).addClass(green)
      }
      else if (booleanText === 'no'){
        $(this).addClass(red)
      }
  })
    
    
  });