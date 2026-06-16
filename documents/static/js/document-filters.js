(function () {
  const searchInput = document.getElementById('docSearchInput');
  const searchClear = document.getElementById('docSearchClear');
  const noMatchRow = document.getElementById('docSearchNoMatch');
  const filtersResetBtn = document.getElementById('filtersResetBtn');
  const resetAllFiltersBtn = document.getElementById('resetAllFiltersBtn');
  const filterTagRemoveButtons = document.querySelectorAll('.filter-tag-remove');
  const rows = document.querySelectorAll('.doc-row');

  let debounceTimer = null;

  function normalize(value) {
    return (value || '').toLowerCase().trim();
  }

  function updateSearchClear() {
    if (!searchClear || !searchInput) return;
    searchClear.classList.toggle('d-none', !searchInput.value.trim());
  }

  function filterRows() {
    if (!searchInput || !rows.length) return;
    const query = normalize(searchInput.value);
    let visibleCount = 0;

    rows.forEach(function (row) {
      const haystack = normalize(row.dataset.search);
      const visible = !query || haystack.includes(query);
      row.classList.toggle('d-none', !visible);
      if (visible) visibleCount += 1;
    });

    if (noMatchRow) {
      noMatchRow.classList.toggle('d-none', visibleCount > 0 || !query);
    }

    updateSearchClear();
  }

  function debouncedFilter() {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(filterRows, 300);
  }

  if (searchInput) {
    searchInput.addEventListener('input', debouncedFilter);
  }

  if (searchClear && searchInput) {
    searchClear.addEventListener('click', function () {
      searchInput.value = '';
      filterRows();
      searchInput.focus();
    });
  }

  if (filtersResetBtn) {
    filtersResetBtn.addEventListener('click', function () {
      window.location.href = window.location.pathname;
    });
  }

  if (resetAllFiltersBtn && searchInput) {
    resetAllFiltersBtn.addEventListener('click', function () {
      searchInput.value = '';
      filterRows();
      window.location.href = window.location.pathname;
    });
  }

  filterTagRemoveButtons.forEach(function (button) {
    button.addEventListener('click', function () {
      const param = button.dataset.filterParam;
      const params = new URLSearchParams(window.location.search);
      params.delete(param);
      params.delete('page');
      const query = params.toString();
      window.location.href = query ? '?' + query : window.location.pathname;
    });
  });

  updateSearchClear();
})();
