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
    domains.push(inputText);
  } else {
    setInvalidChipStyle(chip);
    invalidDomainMessage.style.display = 'block';
    chipInput.setAttribute("readonly", true);
    domainSaveButton.disabled = true;
    document.querySelectorAll('.chip-remove-button').forEach((button) => {
      const hasMatch = domains.some((item) => chip.textContent.includes(item));
      if (!hasMatch) {
        button.style.visibility = 'hidden';
      }
    });
  }
});

const setInvalidChipStyle = ((chip) => {
  chip.style.backgroundColor = 'red';
  chip.style.color = 'white';
  chip.style.fontWeight = '600';
});

const createChip = ((inputText, isValid) => {
  const chip = document.createElement('div');
  chip.className = 'chip';
  chip.innerHTML = `
        <span>${inputText}</span>
        <ion-button class="chip-remove-button">
          <ion-icon name="trash"></ion-icon>
        </ion-button>
    `;
  setChipInputState(inputText, chip, isValid);
  chipInputContainer.style.display = 'block';
  chipsContainer.appendChild(chip);

  chip.querySelector('.chip-remove-button').addEventListener('click', () => {
    chipsContainer.removeChild(chip);
    if (!isValid) {
      invalidDomainMessage.style.display = 'none';
      domainSaveButton.disabled = false;
      chipInput.removeAttribute("readonly");
      chipInput.style.visibility = 'visible';
      chipInput.value = '';
      document.querySelectorAll('.chip-remove-button').forEach((button) => {
        button.style.visibility = 'visible';
      });
    }
    domains = domains.filter(item => item === inputText ? false : true);
    if (domains.length === 0) {
      chipInputContainer.style.display = 'none';
    }
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

window.addEventListener('load', async function() {
  const fetchedDomains = await getExistingDomains();
  if (fetchedDomains) chipInputContainer.style.display = 'block';
});
