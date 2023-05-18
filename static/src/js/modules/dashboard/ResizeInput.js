import $ from 'jquery';

class SelectDropDown {

  constructor() {
    this.events();
  }

  // Events
  events() {
    // $(document).on('load', this.defineEditableInputSize.bind(this));;
    $(".oh-editable-input--w-auto").on('input', this.autoResizeInput.bind(this));;
  }



  // Methods

  /**
   *  Define Editable input size on load.
   */
  // defineEditableInputSize(e) {
    
  //   $(".oh-editable-input--w-auto") = e.target.value.length + "ch";
  // }
  /**
   *  Auto resize input base on the input value.
   */
  autoResizeInput(e) {
    e.target.style.width = e.target.value.length + "ch";
  }

}


export default SelectDropDown;