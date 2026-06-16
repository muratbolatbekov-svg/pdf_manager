(function () {
  const form = document.getElementById('documentForm');
  const pdfInput = document.getElementById('id_pdf_file');
  const modalEl = document.getElementById('replacePdfModal');
  if (!form || !pdfInput || !modalEl || form.dataset.hasPdf !== 'true') return;

  const modal = new bootstrap.Modal(modalEl);
  const confirmBtn = document.getElementById('replacePdfConfirm');
  let pendingSubmit = false;

  pdfInput.addEventListener('change', function () {
    if (pdfInput.files && pdfInput.files.length > 0) {
      pendingSubmit = false;
    }
  });

  form.addEventListener('submit', function (e) {
    if (pendingSubmit) return;
    if (pdfInput.files && pdfInput.files.length > 0) {
      e.preventDefault();
      modal.show();
    }
  });

  document.getElementById('replacePdfCancel')?.addEventListener('click', function () {
    pdfInput.value = '';
    modal.hide();
  });

  confirmBtn?.addEventListener('click', function () {
    pendingSubmit = true;
    modal.hide();
    form.submit();
  });
})();
