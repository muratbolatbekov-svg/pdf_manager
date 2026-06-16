(function () {
  const wrapper = document.querySelector('.tag-input-wrapper');
  if (!wrapper) return;

  const hiddenInput = wrapper.querySelector('input[name="tags_input"]');
  const chipsEl = document.getElementById('tagChips');
  const textInput = document.getElementById('tagTextInput');
  const suggestionsEl = document.getElementById('tagSuggestions');
  const autocompleteUrl = wrapper.dataset.autocompleteUrl;

  let tags = [];
  if (hiddenInput && hiddenInput.value) {
    tags = hiddenInput.value.split(',').map(function (t) { return t.trim(); }).filter(Boolean);
  }

  function syncHidden() {
    if (hiddenInput) hiddenInput.value = tags.join(', ');
  }

  function renderChips() {
    if (!chipsEl) return;
    chipsEl.innerHTML = '';
    tags.forEach(function (tag, index) {
      const chip = document.createElement('span');
      chip.className = 'tag-chip';
      chip.innerHTML = tag + '<button type="button" class="tag-chip-remove" aria-label="' + appI18n('removeTag', 'Удалить тег') + '">&times;</button>';
      chip.querySelector('.tag-chip-remove').addEventListener('click', function () {
        tags.splice(index, 1);
        renderChips();
        syncHidden();
      });
      chipsEl.appendChild(chip);
    });
    syncHidden();
  }

  async function fetchSuggestions(query) {
    if (!autocompleteUrl || !suggestionsEl) return;
    const url = autocompleteUrl + (query ? '?q=' + encodeURIComponent(query) : '');
    try {
      const response = await fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' } });
      if (!response.ok) return;
      const data = await response.json();
      suggestionsEl.innerHTML = '';
      (data.tags || []).forEach(function (name) {
        if (tags.indexOf(name) !== -1) return;
        const option = document.createElement('option');
        option.value = name;
        suggestionsEl.appendChild(option);
      });
    } catch (e) {
      /* ignore */
    }
  }

  function addTag(raw) {
    const value = (raw || '').trim().replace(/,+$/, '');
    if (!value) return;
    const exists = tags.some(function (t) { return t.toLowerCase() === value.toLowerCase(); });
    if (!exists) {
      tags.push(value);
      renderChips();
    }
    if (textInput) textInput.value = '';
  }

  if (textInput) {
    textInput.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' || e.key === ',') {
        e.preventDefault();
        addTag(textInput.value);
      } else if (e.key === 'Backspace' && !textInput.value && tags.length) {
        tags.pop();
        renderChips();
      }
    });

    textInput.addEventListener('input', function () {
      const parts = textInput.value.split(',');
      if (parts.length > 1) {
        parts.slice(0, -1).forEach(addTag);
        textInput.value = parts[parts.length - 1];
      }
      fetchSuggestions(textInput.value.trim());
    });

    textInput.addEventListener('blur', function () {
      if (textInput.value.trim()) addTag(textInput.value);
    });
  }

  renderChips();
  fetchSuggestions('');
})();
