(function () {
  const root = document.getElementById('commentsSection');
  if (!root) return;

  const listEl = document.getElementById('commentsList');
  const countEl = document.getElementById('commentsCount');
  const form = document.getElementById('commentForm');
  const input = document.getElementById('commentInput');
  const createUrl = root.dataset.createUrl;
  const deleteUrlTemplate = root.dataset.deleteUrlTemplate;
  const csrfToken = form?.querySelector('[name=csrfmiddlewaretoken]')?.value;

  function updateCount(count) {
    if (countEl) countEl.textContent = count;
  }

  function hideEmptyState() {
    const empty = document.getElementById('commentsEmpty');
    if (empty) empty.remove();
  }

  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  function renderComment(comment) {
    const item = document.createElement('div');
    item.className = 'comment-item';
    item.dataset.commentId = comment.id;
    item.innerHTML =
      '<div class="comment-avatar" style="background:' + comment.avatar_color + '">' + comment.initials + '</div>' +
      '<div class="comment-body flex-grow-1">' +
        '<div class="comment-meta">' +
          '<span class="comment-author">' + escapeHtml(comment.author_name) + '</span>' +
          '<span class="comment-date"> · ' + comment.created_at + '</span>' +
        '</div>' +
        '<div class="comment-text">' + escapeHtml(comment.text) + '</div>' +
      '</div>' +
      (comment.can_delete
        ? '<button type="button" class="btn btn-sm btn-link text-danger comment-delete" data-comment-id="' + comment.id + '" title="' + appI18n('delete', 'Удалить') + '"><i class="bi bi-trash"></i></button>'
        : '');

    bindDelete(item.querySelector('.comment-delete'), item);
    return item;
  }

  async function deleteComment(commentId, itemEl) {
    const deleteUrl = deleteUrlTemplate.replace('0', String(commentId));
    const response = await fetch(deleteUrl, {
      method: 'POST',
      headers: {
        'X-CSRFToken': csrfToken,
        'X-Requested-With': 'XMLHttpRequest',
      },
    });
    if (!response.ok) return;
    const data = await response.json();
    itemEl.remove();
    updateCount(data.count);
  }

  function bindDelete(button, itemEl) {
    if (!button) return;
    button.addEventListener('click', function () {
      deleteComment(button.dataset.commentId, itemEl);
    });
  }

  listEl?.querySelectorAll('.comment-item').forEach(function (item) {
    bindDelete(item.querySelector('.comment-delete'), item);
  });

  if (form && input) {
    form.addEventListener('submit', async function (e) {
      e.preventDefault();
      const text = input.value.trim();
      if (!text) return;

      const body = new FormData();
      body.append('text', text);
      body.append('csrfmiddlewaretoken', csrfToken);

      const response = await fetch(createUrl, {
        method: 'POST',
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
        body: body,
      });
      if (!response.ok) return;

      const data = await response.json();
      if (listEl && data.comment) {
        hideEmptyState();
        listEl.appendChild(renderComment(data.comment));
      }
      input.value = '';
      updateCount(data.count);
    });

    input.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        form.requestSubmit();
      }
    });
  }
})();
