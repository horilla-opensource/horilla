import $ from 'jquery'
import 'jquery-ui/ui/core';
import 'jquery-ui/ui/widgets/tooltip';
import 'jquery-ui/themes/base/core.css';
import 'jquery-ui/themes/base/theme.css';
import 'jquery-ui/themes/base/tooltip.css';

class Tooltip {

  constructor() { 
    this.events();
  }

  // Events
  events() { 
    // Initialize tooltip.
    $( document ).tooltip();
  }
 
  // Methods
  

}

export default Tooltip;