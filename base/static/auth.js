const chipInput = document.querySelector('.chip-input');
const chipsContainer = document.querySelector('.chips');
const chipInputContainer = document.querySelector('.chip-input-container');
const invalidDomainMessage = document.querySelector('.invalid-domain');
const domainSaveButton = document.querySelector('.domain-save-btn');
const form = document.getElementById('domain-form');
const domainRegex = /^[a-zA-Z0-9-]+\.[a-zA-Z]{2,}$/;
let domains = [];


const isDomainValid = ((inputText) => domainRegex.test(inputText));

const processInput = ((inputText) => {
  if (inputText) createChip(inputText, isDomainValid(inputText));
});

const setChipInputState = ((inputText, chip, isValid) => {
  if (isValid) {
    chip.style.backgroundColor = 'green';
    domains.push(inputText);
  } else {
    chip.style.backgroundColor = 'red';
    invalidDomainMessage.style.display = 'block';
    chipInput.setAttribute("readonly", true);
    domainSaveButton.disabled = true;
  }
});

const createChip = ((inputText, isValid) => {
  const chip = document.createElement('div');
  chip.className = 'chip';
  chip.innerHTML = `
        <span>${inputText}</span>
        <span class="chip-remove">&times;</span>
    `;

  setChipInputState(inputText, chip, isValid);

  chipsContainer.appendChild(chip);

  chip.querySelector('.chip-remove').addEventListener('click', () => {
    chipsContainer.removeChild(chip);
    if (!isValid) {
      invalidDomainMessage.style.display = 'none';
      domainSaveButton.disabled = false;
      chipInput.removeAttribute("readonly");
      chipInput.style.visibility = 'visible';
      chipInput.value = '';
    }
    domains = domains.filter(item => item === inputText ? false : true);
  });
  chipInput.value = '';
});

const getExistingDomains = (async () => {
  try {
    const response = await fetch('/api/domains');
    if (!response.ok) {
      throw new Error(`HTTP error with status: ${response.status}`);
    }
    const data = await response.json();
    if (data.domains) {
      data.domains.split(',').map(domain => createChip(domain, true));
    }
  } catch (error) {
      invalidDomainMessage.textContent = `${error.message}`;
      invalidDomainMessage.style.display = 'block';
  }
});

chipInput.addEventListener('keydown', (event) => {
  if (event.key === ' ' || event.key === 'Enter') {
    event.preventDefault();
    processInput(chipInput.value.trim());
  }
});

domainSaveButton.addEventListener('click', () => {
  processInput(chipInput.value.trim());
  chipInput.value = domains.join(',');
  chipInput.style.visibility = 'hidden';
});

chipInputContainer.addEventListener('click', () => chipInput.focus());

window.addEventListener('load', async function() {
  await getExistingDomains();
});
