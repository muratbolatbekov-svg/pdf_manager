(function () {
  const section = document.getElementById('documentLinksSection');
  if (!section) return;

  const listEl = document.getElementById('documentLinksList');
  const emptyEl = document.getElementById('documentLinksEmpty');
  const modalEl = document.getElementById('addLinkModal');
  const searchInput = document.getElementById('linkSearchInput');
  const resultsEl = document.getElementById('linkSearchResults');
  const addBtn = document.getElementById('addLinkSubmit');
  const form = document.getElementById('addLinkForm');
  const csrfToken = form?.querySelector('[name=csrfmiddlewaretoken]')?.value;

  const searchUrl = section.dataset.searchUrl;
  const createUrl = section.dataset.createUrl;
  const deleteUrlTemplate = section.dataset.deleteUrlTemplate;
  const detailPrefix = section.dataset.docDetailPrefix || '/documents/';
  const canManage = section.dataset.canManage === 'true';

  let debounceTimer = null;
  let selectedIds = new Set();

  const badgeClasses = {
    supplement: 'link-badge-supplement',
    act: 'link-badge-act',
    invoice: 'link-badge-invoice',
    other: 'link-badge-other',
  };

  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  function renderLinkRow(link) {
    const row = document.createElement('div');
    row.className = 'document-link-row';
    row.dataset.linkId = link.id;
    const badgeClass = badgeClasses[link.link_type] || badgeClasses.other;
    row.innerHTML =
      '<div class="d-flex align-items-center gap-2 flex-grow-1 min-w-0">' +
        '<i class="bi bi-file-pdf text-danger flex-shrink-0"></i>' +
        '<span class="text-truncate">' + escapeHtml(link.linked_title) + '</span>' +
        '<span class="badge ' + badgeClass + ' flex-shrink-0">' + escapeHtml(link.link_type_label) + '</span>' +
      '</div>' +
      '<div class="d-flex gap-1 flex-shrink-0">' +
        '<a href="' + detailPrefix + encodeURIComponent(link.linked_slug) + '/" class="btn btn-sm btn-outline-secondary" title="' + appI18n('open', 'Открыть') + '"><i class="bi bi-arrow-right"></i></a>' +
        (canManage
          ? '<button type="button" class="btn btn-sm btn-outline-danger link-delete-btn" data-link-id="' + link.id + '" title="' + appI18n('deleteLink', 'Удалить связь') + '"><i class="bi bi-trash"></i></button>'
          : '') +
      '</div>';
    bindDelete(row.querySelector('.link-delete-btn'), row);
    return row;
  }

  function hideEmpty() {
    if (emptyEl) emptyEl.remove();
  }

  async function deleteLink(linkId, rowEl) {
    const url = deleteUrlTemplate.replace('0', String(linkId));
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'X-CSRFToken': csrfToken, 'X-Requested-With': 'XMLHttpRequest' },
    });
    if (!response.ok) return;
    rowEl.remove();
    if (listEl && !listEl.querySelector('.document-link-row') && !listEl.querySelector('#documentLinksEmpty')) {
      const p = document.createElement('p');
      p.id = 'documentLinksEmpty';
      p.className = 'text-muted text-center py-3 mb-0';
      p.textContent = appI18n('noLinks', 'Связанных документов пока нет');
      listEl.appendChild(p);
    }
  }

  function bindDelete(button, rowEl) {
    if (!button) return;
    button.addEventListener('click', function () {
      deleteLink(button.dataset.linkId, rowEl);
    });
  }

  listEl?.querySelectorAll('.document-link-row').forEach(function (row) {
    bindDelete(row.querySelector('.link-delete-btn'), row);
  });

  async function runSearch() {
    if (!searchInput || !resultsEl) return;
    const q = searchInput.value.trim();
    const url = searchUrl + (q ? '?q=' + encodeURIComponent(q) : '');
    const response = await fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' } });
    if (!response.ok) return;
    const data = await response.json();
    resultsEl.innerHTML = '';
    selectedIds.clear();
    if (!data.results.length) {
      resultsEl.innerHTML = '<p class="text-muted small mb-0">' + appI18n('noDocsFound', 'Документы не найдены') + '</p>';
      return;
    }
    data.results.forEach(function (doc) {
      const label = document.createElement('label');
      label.className = 'd-flex align-items-center gap-2 py-1 link-search-item';
      label.innerHTML =
        '<input type="checkbox" class="form-check-input link-search-check" value="' + doc.id + '">' +
        '<span>' + escapeHtml(doc.title) + '</span>';
      const checkbox = label.querySelector('.link-search-check');
      checkbox.addEventListener('change', function () {
        if (checkbox.checked) selectedIds.add(String(doc.id));
        else selectedIds.delete(String(doc.id));
      });
      resultsEl.appendChild(label);
    });
  }

  function debouncedSearch() {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(runSearch, 300);
  }

  searchInput?.addEventListener('input', debouncedSearch);

  modalEl?.addEventListener('show.bs.modal', function () {
    if (searchInput) searchInput.value = '';
    selectedIds.clear();
    runSearch();
  });

  addBtn?.addEventListener('click', async function () {
    const linkType = form.querySelector('input[name="link_type"]:checked')?.value || 'other';
    if (!selectedIds.size) return;

    const body = new FormData();
    body.append('csrfmiddlewaretoken', csrfToken);
    body.append('link_type', linkType);
    selectedIds.forEach(function (id) { body.append('linked_ids', id); });

    addBtn.disabled = true;
    const response = await fetch(createUrl, {
      method: 'POST',
      headers: { 'X-Requested-With': 'XMLHttpRequest' },
      body: body,
    });
    addBtn.disabled = false;

    if (!response.ok) {
      const err = await response.json().catch(function () { return {}; });
      alert(err.error || appI18n('addLinkError', 'Не удалось добавить связь'));
      return;
    }

    const data = await response.json();
    hideEmpty();
    data.links.forEach(function (link) {
      listEl.appendChild(renderLinkRow(link));
    });

    bootstrap.Modal.getInstance(modalEl)?.hide();
  });
})();
