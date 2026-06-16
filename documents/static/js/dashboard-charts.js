(function () {
  const configEl = document.getElementById('dashboardAnalyticsConfig');
  const rootEl = document.getElementById('dashboardAnalyticsRoot');
  if (!configEl || !rootEl) return;

  const analyticsUrl = rootEl.dataset.analyticsUrl;
  let initialData = {};
  try {
    initialData = JSON.parse(configEl.textContent);
  } catch (e) {
    initialData = {};
  }

  const statEls = {
    total_docs: document.getElementById('statTotalDocs'),
    active_docs: document.getElementById('statActiveDocs'),
    draft_docs: document.getElementById('statDraftDocs'),
    archived_docs: document.getElementById('statArchivedDocs'),
  };

  const periodLabelEl = document.getElementById('dashboardPeriodLabel');
  const periodMenu = document.getElementById('dashboardPeriodMenu');
  const rangeButtons = document.querySelectorAll('[data-months]');

  let trendChart = null;
  let categoryChart = null;
  let currentPeriod = initialData.period || 'current_month';
  let currentMonths = initialData.months || 12;

  const chartColors = [
    '#0071e3', '#34c759', '#ff9500', '#ff3b30', '#5856d6',
    '#af52de', '#5ac8fa', '#ff2d55', '#8e8e93', '#30b0c7',
  ];

  function formatAmount(value) {
    return new Intl.NumberFormat('ru-RU').format(Math.round(value));
  }

  function updateStats(stats) {
    Object.keys(statEls).forEach((key) => {
      if (statEls[key]) statEls[key].textContent = stats[key] ?? 0;
    });
  }

  function renderTrendChart(points) {
    const canvas = document.getElementById('amountTrendChart');
    if (!canvas || typeof Chart === 'undefined') return;
    const labels = points.map((p) => p.label);
    const values = points.map((p) => p.amount);
    if (trendChart) trendChart.destroy();
    trendChart = new Chart(canvas, {
      type: 'line',
      data: {
        labels,
        datasets: [{
          label: appI18n('chartAmountLabel', 'Сумма договоров, ₸'),
          data: values,
          borderColor: '#0071e3',
          backgroundColor: 'rgba(0,113,227,0.08)',
          fill: true,
          tension: 0.35,
          pointRadius: 4,
          pointHoverRadius: 6,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label(ctx) {
                return `${formatAmount(ctx.parsed.y)} ₸`;
              },
            },
          },
        },
        scales: {
          y: {
            ticks: {
              callback(value) {
                return `${formatAmount(value)} ₸`;
              },
            },
          },
        },
      },
    });
  }

  function renderCategoryChart(items) {
    const canvas = document.getElementById('categoryChart');
    if (!canvas || typeof Chart === 'undefined') return;
    if (!items.length) {
      if (categoryChart) categoryChart.destroy();
      categoryChart = null;
      canvas.parentElement.querySelector('.chart-empty')?.classList.remove('d-none');
      return;
    }
    canvas.parentElement.querySelector('.chart-empty')?.classList.add('d-none');
    const labels = items.map((item) => item.label);
    const values = items.map((item) => item.amount);
    if (categoryChart) categoryChart.destroy();
    categoryChart = new Chart(canvas, {
      type: 'bar',
      data: {
        labels,
        datasets: [{
          data: values,
          backgroundColor: chartColors.slice(0, values.length),
          borderRadius: 6,
          barThickness: 18,
        }],
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label(ctx) {
                const item = items[ctx.dataIndex];
                return `${formatAmount(item.amount)} ₸ (${item.percent}%)`;
              },
            },
          },
        },
        scales: {
          x: {
            ticks: {
              callback(value) {
                return `${formatAmount(value)} ₸`;
              },
            },
          },
        },
      },
    });
  }

  function applyData(data) {
    updateStats(data.stats || {});
    if (periodLabelEl && data.period_label) periodLabelEl.textContent = data.period_label;
    renderTrendChart(data.trend || []);
    renderCategoryChart(data.categories || []);
  }

  function setActivePeriod(period) {
    currentPeriod = period;
    periodMenu?.querySelectorAll('[data-period]').forEach((btn) => {
      const active = btn.dataset.period === period;
      btn.classList.toggle('active', active);
      const icon = btn.querySelector('.period-dot');
      if (icon) icon.textContent = active ? '●' : '○';
    });
  }

  function setActiveMonths(months) {
    currentMonths = months;
    rangeButtons.forEach((btn) => {
      btn.classList.toggle('active', Number(btn.dataset.months) === months);
    });
  }

  async function loadAnalytics(period, months) {
    const params = new URLSearchParams({ period, months: String(months) });
    const response = await fetch(`${analyticsUrl}?${params.toString()}`, {
      headers: { 'X-Requested-With': 'XMLHttpRequest' },
    });
    if (!response.ok) return;
    const data = await response.json();
    applyData(data);
  }

  periodMenu?.querySelectorAll('[data-period]').forEach((btn) => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      const period = btn.dataset.period;
      setActivePeriod(period);
      loadAnalytics(period, currentMonths);
    });
  });

  rangeButtons.forEach((btn) => {
    btn.addEventListener('click', () => {
      const months = Number(btn.dataset.months);
      setActiveMonths(months);
      loadAnalytics(currentPeriod, months);
    });
  });

  setActivePeriod(currentPeriod);
  setActiveMonths(currentMonths);
  applyData(initialData);
})();
