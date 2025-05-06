import $ from 'jquery';

class SelectDropDown {

  constructor() {
    this.events();
  }

  // Events
  events() {
    // Picker Event
    $(window).on('load', this.imageSelectInit.bind(this));
    $('.oh-image-selector__btn-select').on('click', this.imageSelectSelect.bind(this));
    // Toggle Class
    $('[data-action="toggle"]').on('click', this.genericToggleClass.bind(this));
  }



  // Methods

  /**
   *  Initialize Image Selector
   */
  imageSelectInit() {
    var itemArray = [];
    $('.oh-image-selector option').each(function () {
      var img = $(this).attr("data-thumbnail");
      var text = this.innerText;
      var value = $(this).val();
      var item = '<li class="oh-image-selector__item"><img src="' + img + '" alt="" value="' + value + '"/><span>' + text + '</span></li>';
      itemArray.push(item);
    })

    $('.oh-image-selector__list').html(itemArray);

    $('.oh-image-selector__btn-select').html(itemArray[0]);
    $('.oh-image-selector__btn-select').attr('value', 'en');

    $('.oh-image-selector__item').on('click', function () {
      var img = $(this).find('img').attr("src");
      var value = $(this).find('img').attr('value');
      var text = this.innerText;
      var item = '<li><img src="' + img + '" alt="" /><span>' + text + '</span></li>';
      $('.oh-image-selector__btn-select').html(item);
      $('.oh-image-selector__btn-select').attr('value', value);
      $(".oh-image-selector__list-container").toggle();
    });
  }

  /**
    *  Make Image Selector Selection
    */
  imageSelectSelect() {
    $(".oh-image-selector__list-container").toggle();
  }

  /**
   *  Toggle Class
  */
  genericToggleClass(e){
    e.preventDefault();
    let targetSelector = $(e.target).data('target');
    let classToToggle = $(e.target).data('class');
    if(targetSelector && classToToggle){
      $(targetSelector).toggleClass(classToToggle);
    }
  }
}


export default SelectDropDown;