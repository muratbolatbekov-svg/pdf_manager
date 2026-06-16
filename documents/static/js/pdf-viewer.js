(function () {
  const modalEl = document.getElementById('pdfViewerModal');
  if (!modalEl) return;

  const modal = new bootstrap.Modal(modalEl);
  const titleEl = document.getElementById('pdfViewerTitle');
  const canvas = document.getElementById('pdfViewerCanvas');
  const canvasWrap = document.getElementById('pdfViewerCanvasWrap');
  const pageInfoEl = document.getElementById('pdfViewerPageInfo');
  const prevBtn = document.getElementById('pdfViewerPrev');
  const nextBtn = document.getElementById('pdfViewerNext');
  const downloadBtn = document.getElementById('pdfViewerDownload');
  const printBtn = document.getElementById('pdfViewerPrint');
  const loadingEl = document.getElementById('pdfViewerLoading');

  let pdfDoc = null;
  let pageNum = 1;
  let currentUrl = '';
  let renderTask = null;

  pdfjsLib.GlobalWorkerOptions.workerSrc =
    'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';

  function setLoading(isLoading) {
    loadingEl.classList.toggle('d-none', !isLoading);
    canvas.classList.toggle('d-none', isLoading);
  }

  function updatePageInfo() {
    const total = pdfDoc ? pdfDoc.numPages : 0;
    if (total) {
      const pageLabel = appI18n('pageOf', 'Стр. %(page)s из %(total)s')
        .replace('%(page)s', pageNum)
        .replace('%(total)s', total);
      pageInfoEl.textContent = pageLabel;
    } else {
      pageInfoEl.textContent = '';
    }
    prevBtn.disabled = pageNum <= 1;
    nextBtn.disabled = !pdfDoc || pageNum >= total;
  }

  function renderPage(num) {
    if (!pdfDoc) return;
    setLoading(true);
    pdfDoc.getPage(num).then(function (page) {
      const containerWidth = canvasWrap.clientWidth - 32;
      const viewport = page.getViewport({ scale: 1 });
      const scale = Math.min(containerWidth / viewport.width, 1.5);
      const scaledViewport = page.getViewport({ scale: scale });

      canvas.height = scaledViewport.height;
      canvas.width = scaledViewport.width;

      if (renderTask) {
        renderTask.cancel();
      }

      renderTask = page.render({
        canvasContext: canvas.getContext('2d'),
        viewport: scaledViewport,
      });

      return renderTask.promise;
    }).then(function () {
      setLoading(false);
      updatePageInfo();
    }).catch(function (err) {
      if (err && err.name === 'RenderingCancelledException') return;
      setLoading(false);
      pageInfoEl.textContent = appI18n('renderError', 'Не удалось отобразить страницу');
    });
  }

  function openViewer(url, title) {
    currentUrl = url;
    pageNum = 1;
    pdfDoc = null;
    titleEl.textContent = title;
    downloadBtn.href = url;
    downloadBtn.download = title + '.pdf';
    setLoading(true);
    canvas.classList.add('d-none');
    modal.show();

    pdfjsLib.getDocument(url).promise.then(function (pdf) {
      pdfDoc = pdf;
      renderPage(pageNum);
    }).catch(function () {
      setLoading(false);
      pageInfoEl.textContent = appI18n('loadError', 'Не удалось загрузить PDF');
    });
  }

  document.querySelectorAll('.pdf-preview-trigger').forEach(function (trigger) {
    trigger.addEventListener('click', function (event) {
      event.preventDefault();
      const url = trigger.dataset.pdfUrl;
      const title = trigger.dataset.pdfTitle || appI18n('document', 'Документ');
      if (url) {
        openViewer(url, title);
      }
    });
  });

  prevBtn.addEventListener('click', function () {
    if (pageNum <= 1) return;
    pageNum -= 1;
    renderPage(pageNum);
  });

  nextBtn.addEventListener('click', function () {
    if (!pdfDoc || pageNum >= pdfDoc.numPages) return;
    pageNum += 1;
    renderPage(pageNum);
  });

  printBtn.addEventListener('click', function () {
    if (!currentUrl) return;
    const printWindow = window.open(currentUrl);
    if (printWindow) {
      printWindow.onload = function () {
        printWindow.print();
      };
    }
  });

  modalEl.addEventListener('hidden.bs.modal', function () {
    if (renderTask) {
      renderTask.cancel();
      renderTask = null;
    }
    pdfDoc = null;
    pageNum = 1;
    currentUrl = '';
    canvas.getContext('2d').clearRect(0, 0, canvas.width, canvas.height);
    pageInfoEl.textContent = '';
  });

  window.addEventListener('resize', function () {
    if (pdfDoc && modalEl.classList.contains('show')) {
      renderPage(pageNum);
    }
  });
})();
