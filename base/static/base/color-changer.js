// Utility Function: Convert HSL to Hex
function hslToHex(hsl) {
  const hslRegex = /hsl\((\d+),\s*([\d.]+)%,\s*([\d.]+)%\)/;
  const match = hsl.match(hslRegex);
  if (!match) return '#000000'; // Default fallback

  let h = parseInt(match[1]);
  let s = parseFloat(match[2]) / 100;
  let l = parseFloat(match[3]) / 100;

  let c = (1 - Math.abs(2 * l - 1)) * s;
  let x = c * (1 - Math.abs((h / 60) % 2 - 1));
  let m = l - c / 2;

  let r, g, b;
  if (h >= 0 && h < 60) [r, g, b] = [c, x, 0];
  else if (h < 120) [r, g, b] = [x, c, 0];
  else if (h < 180) [r, g, b] = [0, c, x];
  else if (h < 240) [r, g, b] = [0, x, c];
  else if (h < 300) [r, g, b] = [x, 0, c];
  else [r, g, b] = [c, 0, x];

  r = Math.round((r + m) * 255).toString(16).padStart(2, '0');
  g = Math.round((g + m) * 255).toString(16).padStart(2, '0');
  b = Math.round((b + m) * 255).toString(16).padStart(2, '0');

  return `#${r}${g}${b}`;
}

// Utility Function: Convert Hex to HSL
function hexToHsl(hex) {
  let r = parseInt(hex.slice(1, 3), 16) / 255;
  let g = parseInt(hex.slice(3, 5), 16) / 255;
  let b = parseInt(hex.slice(5, 7), 16) / 255;

  let max = Math.max(r, g, b),
      min = Math.min(r, g, b);
  let h, s, l = (max + min) / 2;

  if (max === min) h = s = 0;
  else {
      let d = max - min;
      s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
      h =
          max === r
              ? (g - b) / d + (g < b ? 6 : 0)
              : max === g
              ? (b - r) / d + 2
              : (r - g) / d + 4;
      h /= 6;
  }
  h = Math.round(h * 360);
  s = Math.round(s * 100);
  l = Math.round(l * 100);

  return `hsl(${h}, ${s}%, ${l}%)`;
}

// Controls and their default values
const controls = [
{ id: 'sbar', cssClass: '.oh-sidebar', property: 'background-color', default: 'hsl(0, 0%, 13%)' },
{ id: 'company-bg', cssClass: '.oh-sidebar__company', property: 'background-color', default: 'hsl(0, 0%, 13%)' },
{ id: 'menu-link', cssClass: '.oh-sidebar__menu-link', property: 'background-color', default: 'hsl(0, 0%, 20%)' },
{ id: 'active-menu-link', cssClass: '.oh-sidebar__menu-link--active', property: 'background-color', default: 'hsl(0, 0%, 20%)' },
{ id: 'submenu', cssClass: '.oh-sidebar__submenu', property: 'background-color', default: 'hsl(0, 0%, 13%)' },
{ id: 'submenu-link', cssClass: '.oh-sidebar__submenu-link', property: 'color', default: 'hsl(0, 0%, 100%)' },
{ id: 'submenu-link-active', cssClass: '.oh-sidebar__submenu-link.active', property: 'color', default: 'hsl(0, 0%, 70%)' },
{ id: 'secondary-btn', cssClass: '.oh-btn--secondary', property: 'background-color', default: 'hsl(8, 77%, 56%)' },
{ id: 'page-bg', cssClass: 'body', property: 'background-color', default: 'hsl(0, 0%, 97.5%)' }
];

// Fetch company colors from the backend using the company ID.
async function fetchCompanyColors(companyId) {
try {
  const response = await fetch(`/get-company-colors/?company_id=${companyId}`);
  if (response.ok) {
    const data = await response.json();
    console.log('Fetched Company Colors:', data);
    return data;
  } else {
    console.error('Error fetching company colors:', await response.text());
    return {};
  }
} catch (error) {
  console.error('Error during fetchCompanyColors:', error);
  return {};
}
}
//updates colors and send them to the back-end
async function updateColor(colorId, hexValue) {
  const hslValue = hexToHsl(hexValue);

  const control = controls.find(c => c.id === colorId);
  if (control) {
    document.querySelectorAll(control.cssClass).forEach(element => {
      element.style.setProperty(control.property, hexValue, 'important');
    });

    const display = document.getElementById(`${colorId}-val`);
    if (display) {
      display.textContent = hslValue;
    }

    try {
      const response = await fetch('/update-company-color/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ color_id: colorId, color_value: hexValue })
      });

      if (!response.ok) {
        console.error('Error saving colors:', await response.text());
      } else {
        console.log(`Cor ${colorId} Saved with success!`);
      }
      //Injects dynamically the colors
      injectDynamicStyles(window.currentColors);
    } catch (error) {
      console.error('Error sending to the back-end backend:', error);
    }
  }
}


// Apply colors within modals using the "controls" mapping
function applyColorsToModal(modal, colors) {
controls.forEach(({ id, cssClass, property, default: defaultColor }) => {
  // Get the color using the control id; fallback to default if not available.
  const color = colors[id] || defaultColor;
  // Apply styles (using the control's defined property) to matching elements within the modal.
  modal.querySelectorAll(cssClass).forEach(element => {
    element.style.setProperty(property, color, 'important');
    console.log(`Applying color ${color} to ${cssClass} (property ${property}) in modal ${modal.id}`);
  });
});
}

// Apply colors to global page elements and color pickers.
function applyColors(colors) {
controls.forEach(({ id, cssClass, property, default: defaultColor }) => {
  const color = colors[id] || defaultColor;
  const hexValue = color.startsWith('hsl') ? hslToHex(color) : color;
  const picker = document.getElementById(id);
  const display = document.getElementById(`${id}-val`);

  // Set the picker's value.
  if (picker) {
    picker.value = hexValue;
    picker.addEventListener('input', (e) => {
      const newHexValue = e.target.value;
      updateColor(id, newHexValue);
    });
  }

  // Update the displayed color (in HSL format).
  if (display) {
    display.textContent = color;
  }

  // Apply the color to the corresponding global page elements.
  document.querySelectorAll(cssClass).forEach(element => {
    element.style.setProperty(property, hexValue, 'important');
  });
});
}

// Reset all colors to their default values and update the backend.
async function resetColorsToDefault() {

try {
  const response = await fetch('/reset-company-colors/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' }
  });
  if (!response.ok) {
    console.error('Reset failed:', await response.text());
    return;
  }
  const data = await response.json();

  const defaultColors = data.colors;


  controls.forEach(({ id, cssClass, property, default: controlDefault }) => {

    const defaultHex = controlDefault.startsWith('hsl') ? hslToHex(controlDefault) : controlDefault;

    const picker = document.getElementById(id);
    if (picker) {
      picker.value = defaultHex;
    }

    const display = document.getElementById(`${id}-val`);
    if (display) {
      display.textContent = controlDefault;
    }

    document.querySelectorAll(cssClass).forEach(element => {
      element.style.setProperty(property, defaultHex, 'important');
    });
  });

  window.currentColors = defaultColors;

  document.querySelectorAll('[id*="Modal"]').forEach(modal => {
    applyColorsToModal(modal, window.currentColors);
  });

  console.log("All colors were reset.");

} catch (error) {
  console.error('Error during reset:', error);
}
}

document.addEventListener('DOMContentLoaded', async () => {
  const urlParams = new URLSearchParams(window.location.search);
  const companyId = urlParams.get('company_id') || 'all';
  window.currentColors = await fetchCompanyColors(companyId);

  applyColors(window.currentColors);
  injectDynamicStyles(window.currentColors);
});

function injectDynamicStyles(colors) {
  let styleElement = document.getElementById('dynamic-styles');
  
  // Se o elemento de estilo ainda não existir, cria um
  if (!styleElement) {
    styleElement = document.createElement('style');
    styleElement.id = 'dynamic-styles';
    document.head.appendChild(styleElement);
  }

  let cssRules = '';

  controls.forEach(({ id, cssClass, property, default: defaultColor }) => {
    const color = colors[id] || defaultColor;
    const hexValue = color.startsWith('hsl') ? hslToHex(color) : color;

    // ADD's CSS rules to ensure priority.
    cssRules += `${cssClass} { ${property}: ${hexValue} !important; }\n`;
  });

  styleElement.innerHTML = cssRules;
}

document.addEventListener('DOMContentLoaded', async () => {
  const urlParams = new URLSearchParams(window.location.search);
  const companyId = urlParams.get('company_id') || 'all';

  window.currentColors = await fetchCompanyColors(companyId);

  applyColors(window.currentColors);

  document.querySelectorAll('[id*="Modal"]').forEach(modal => {
    const observer = new MutationObserver(() => {
      applyColorsToModal(modal, window.currentColors);
    });
    observer.observe(modal, { childList: true, subtree: true });
    applyColorsToModal(modal, window.currentColors);
  });

  const resetBtn = document.getElementById('reset-btn');
  if (resetBtn) {
    resetBtn.addEventListener('click', resetColorsToDefault);
  }
});

