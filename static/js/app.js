/**
 * BeTrendy - Fashion Trend Analyzer Client Application
 * Handles asynchronous data fetching, dynamic Hang Tag generation,
 * Chart.js renders (Movers & 8-Week Forecast), table sorting/filtering,
 * and AJAX favourite toggling.
 */

// Global Application State
const AppState = {
  category: 'both',
  geo: 'IN',
  timeframe: 'today 12-m',
  forceSample: false,
  searchQuery: '',
  sortCol: 'growth',
  sortDir: 'desc',
  items: [],
  dates: [],
  selectedForecastItems: ['cargo pants', 'co ord set', 'baggy jeans'],
  charts: {
    movers: null,
    forecast: null
  }
};

// Streetwear Color Palette for Multi-Line Forecasts
const CHART_COLORS = [
  { solid: '#ff2e93', fill: 'rgba(255, 46, 147, 0.1)' }, // Hot Pink
  { solid: '#ff8a00', fill: 'rgba(255, 138, 0, 0.1)' },  // Neon Orange
  { solid: '#8b5cf6', fill: 'rgba(139, 92, 246, 0.1)' }, // Electric Purple
  { solid: '#0070f3', fill: 'rgba(0, 112, 243, 0.1)' },  // Electric Blue
  { solid: '#10b981', fill: 'rgba(16, 185, 129, 0.1)' }  // Acid Lime
];

/**
 * Get current CSRF token from page meta tag.
 */
function getCsrfToken() {
  const meta = document.querySelector('meta[name="csrf-token"]');
  return meta ? meta.getAttribute('content') : '';
}

/**
 * Format string slug for local images.
 */
function toSlug(name) {
  return name.toLowerCase().trim().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');
}

/**
 * Initialize application when DOM is ready.
 */
document.addEventListener('DOMContentLoaded', () => {
  // Only initialize on pages containing the dashboard elements
  if (!document.getElementById('hangTagsContainer')) return;

  initEventListeners();
  loadInitialStateFromUrl();
  fetchTrendData();
});

/**
 * Read query parameters from URL if present.
 */
function loadInitialStateFromUrl() {
  const urlParams = new URLSearchParams(window.location.search);
  if (urlParams.has('category')) AppState.category = urlParams.get('category');
  if (urlParams.has('geo')) AppState.geo = urlParams.get('geo');
  if (urlParams.has('timeframe')) AppState.timeframe = urlParams.get('timeframe');
  if (urlParams.get('sample') === '1') AppState.forceSample = true;

  // Sync inputs with state
  const sampleToggle = document.getElementById('sampleDataToggle');
  if (sampleToggle) sampleToggle.checked = AppState.forceSample;

  const geoSelect = document.getElementById('geoSelect');
  if (geoSelect) geoSelect.value = AppState.geo;

  const timeframeSelect = document.getElementById('timeframeSelect');
  if (timeframeSelect) timeframeSelect.value = AppState.timeframe;

  document.querySelectorAll('#categoryFilter .pill-opt').forEach(btn => {
    btn.classList.toggle('active', btn.getAttribute('data-cat') === AppState.category);
  });
}

/**
 * Attach UI event listeners.
 */
function initEventListeners() {
  // Category Pill Buttons (Both / Men / Women)
  document.querySelectorAll('#categoryFilter .pill-opt').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('#categoryFilter .pill-opt').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      AppState.category = btn.getAttribute('data-cat');
      fetchTrendData();
    });
  });

  // Region Selector Dropdown
  const geoSelect = document.getElementById('geoSelect');
  if (geoSelect) {
    geoSelect.addEventListener('change', (e) => {
      AppState.geo = e.target.value;
      fetchTrendData();
    });
  }

  // Timeframe Selector Dropdown
  const timeframeSelect = document.getElementById('timeframeSelect');
  if (timeframeSelect) {
    timeframeSelect.addEventListener('change', (e) => {
      AppState.timeframe = e.target.value;
      fetchTrendData();
    });
  }

  // Sample Data Toggle Switch
  const sampleToggle = document.getElementById('sampleDataToggle');
  if (sampleToggle) {
    sampleToggle.addEventListener('change', (e) => {
      AppState.forceSample = e.target.checked;
      fetchTrendData();
    });
  }

  // Realtime Search Input
  const searchInput = document.getElementById('searchInput');
  if (searchInput) {
    searchInput.addEventListener('input', (e) => {
      AppState.searchQuery = e.target.value.toLowerCase().trim();
      renderItemsTable();
    });
  }

  // Custom Item Submission Form
  const customForm = document.getElementById('customItemForm');
  if (customForm) {
    customForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const input = document.getElementById('customItemInput');
      const keyword = input.value.trim();
      if (!keyword) return;

      try {
        const res = await fetch('/api/custom-item', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
          },
          body: JSON.stringify({ keyword })
        });
        const data = await res.json();
        if (res.ok) {
          input.value = '';
          // Ensure new item is included in forecast
          if (!AppState.selectedForecastItems.includes(keyword)) {
            if (AppState.selectedForecastItems.length >= 5) {
              AppState.selectedForecastItems.shift();
            }
            AppState.selectedForecastItems.push(keyword);
          }
          fetchTrendData();
        } else {
          alert(data.error || 'Failed to add item.');
        }
      } catch (err) {
        console.error('Custom item error:', err);
      }
    });
  }

  // Download CSV Button
  const csvBtn = document.getElementById('downloadCsvBtn');
  if (csvBtn) {
    csvBtn.addEventListener('click', () => {
      const url = `/api/export-csv?category=${AppState.category}&geo=${AppState.geo}&timeframe=${AppState.timeframe}&sample=${AppState.forceSample ? 1 : 0}`;
      window.location.href = url;
    });
  }

  // Table Sorting Headers
  document.querySelectorAll('#itemsTable th[data-sort]').forEach(th => {
    th.addEventListener('click', () => {
      const sortField = th.getAttribute('data-sort');
      if (AppState.sortCol === sortField) {
        AppState.sortDir = AppState.sortDir === 'asc' ? 'desc' : 'asc';
      } else {
        AppState.sortCol = sortField;
        AppState.sortDir = 'desc';
      }
      renderItemsTable();
    });
  });
}

/**
 * Fetch analyzed trend data from Flask JSON route /api/trends.
 */
async function fetchTrendData() {
  const sampleParam = AppState.forceSample ? '1' : '0';
  const url = `/api/trends?category=${AppState.category}&geo=${AppState.geo}&timeframe=${AppState.timeframe}&sample=${sampleParam}`;

  let data;
  try {
    const res = await fetch(url);
    if (!res.ok) throw new Error(`HTTP error ${res.status}`);
    data = await res.json();
  } catch (apiErr) {
    console.warn('API unreachable, checking static fallback data/trends.json:', apiErr);
    try {
      const fallbackRes = await fetch('data/trends.json');
      if (!fallbackRes.ok) throw new Error(`Fallback HTTP error ${fallbackRes.status}`);
      data = await fallbackRes.json();
    } catch (fallbackErr) {
      console.error('Failed to load trends:', fallbackErr);
      const container = document.getElementById('hangTagsContainer');
      if (container) {
        container.innerHTML = `<div class="hang-tag-card" style="grid-column: 1/-1; text-align: center; padding: 2rem;">
          <h3>Could not load trends data</h3>
          <p style="color: var(--text-muted); margin-top: 0.5rem;">Please check your connection or switch on Sample Data.</p>
        </div>`;
      }
      return;
    }
  }

  try {
    AppState.items = data.items || [];
    AppState.dates = data.dates || [];

    // Filter items according to current category selection if on static mode
    let filteredItems = AppState.items;
    if (AppState.category && AppState.category !== 'both') {
      filteredItems = AppState.items.filter(i => i.category === AppState.category);
    }
    const risingSorted = [...filteredItems].filter(i => i.status === 'Rising').sort((a, b) => b.growth_rate - a.growth_rate);
    const topRising = risingSorted.slice(0, 3);

    // Handle Sample Notice Banner
    const noticeBanner = document.getElementById('sampleNoticeBanner');
    const noticeText = document.getElementById('sampleNoticeText');
    if (data.is_sample) {
      noticeBanner.style.display = 'flex';
      noticeText.textContent = data.sample_notice || 'Showing curated sample data.';
    } else {
      noticeBanner.style.display = 'none';
    }

    // Update Hero Headline
    const heroTitle = document.getElementById('heroHeadline');
    if (heroTitle && data.hero_headline) {
      const words = data.hero_headline.split(' ');
      const highlightWord = words.slice(-2).join(' ');
      const prefix = words.slice(0, -2).join(' ');
      heroTitle.innerHTML = `${prefix} <span class="highlight">${highlightWord}</span>`;
    }

    // Render Components
    renderHangTags(topRising.length > 0 ? topRising : (data.top_rising || []));
    renderMoversChart();
    renderForecastChips();
    fetchAndRenderForecast();
    renderItemsTable();
  } catch (renderErr) {
    console.error('Render error:', renderErr);
  }
}

/**
 * Render Signature Top 3 Hang Tag Cards.
 */
function renderHangTags(topRising) {
  const container = document.getElementById('hangTagsContainer');
  if (!container) return;

  if (!topRising || topRising.length === 0) {
    container.innerHTML = '<p style="grid-column: 1/-1; text-align: center; color: var(--text-muted);">No rising items in this selection.</p>';
    return;
  }

  container.innerHTML = topRising.slice(0, 3).map((item, idx) => {
    const slug = toSlug(item.name);
    const growthSign = item.growth_rate > 0 ? '+' : '';
    const heartActive = item.is_favourite ? 'active' : '';
    const initial = item.name.charAt(0).toUpperCase();

    return `
      <article class="hang-tag-card" data-item="${item.name}">
        <!-- Punched Hole at Top Center -->
        <div class="hang-tag-hole"></div>

        <!-- Rank Badge -->
        <span class="hang-tag-rank">#${idx + 1} RISING</span>

        <!-- Heart Save Button -->
        <button 
          type="button" 
          class="btn-icon btn-heart hang-tag-heart ${heartActive}" 
          title="Save to Favourites" 
          aria-label="Save ${item.name} to favourites"
          onclick="toggleFavourite('${item.name}', '${item.category}', this)"
        >
          ♥
        </button>

        <!-- Apparel Image with Fallback -->
        <div class="hang-tag-image-wrap">
          <img 
            src="/static/images/${slug}.jpg" 
            alt="${item.name}" 
            class="hang-tag-img"
            onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';"
          >
          <div class="img-fallback-tile ${idx === 1 ? 'alt-grad-1' : (idx === 2 ? 'alt-grad-2' : '')}" style="display: none;">
            <span class="fallback-initial">${initial}</span>
            <span class="fallback-name">${item.name}</span>
          </div>
        </div>

        <!-- Info & Velocity Stats -->
        <div class="hang-tag-info">
          <h3 class="hang-tag-name">${item.name}</h3>
          <span class="hang-tag-category">${item.category} silhouette</span>

          <div class="hang-tag-stats">
            <div>
              <span style="font-size: 0.72rem; color: var(--text-muted); display: block; font-weight: 700;">GROWTH</span>
              <div class="growth-badge-large">${growthSign}${item.growth_rate}%</div>
            </div>
            <div style="text-align: right;">
              <span style="font-size: 0.72rem; color: var(--text-muted); display: block; font-weight: 700;">SCORE</span>
              <span class="interest-score">${item.current_score}/100</span>
            </div>
          </div>

          <!-- Mini Sparkline Canvas -->
          <canvas class="sparkline-canvas" data-sparkline='${JSON.stringify(item.sparkline)}'></canvas>
        </div>
      </article>
    `;
  }).join('');

  // Render Mini Sparkline Canvases
  container.querySelectorAll('.sparkline-canvas').forEach(canvas => {
    try {
      const data = JSON.parse(canvas.getAttribute('data-sparkline'));
      drawSparkline(canvas, data, '#ff2e93');
    } catch (e) {
      console.warn('Sparkline error', e);
    }
  });
}

/**
 * Draw a clean 2D Canvas Sparkline.
 */
function drawSparkline(canvas, data, color) {
  if (!data || data.length < 2) return;
  const ctx = canvas.getContext('2d');
  const w = canvas.width = canvas.parentElement.clientWidth || 180;
  const h = canvas.height = 38;

  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;

  ctx.clearRect(0, 0, w, h);
  ctx.beginPath();
  ctx.strokeStyle = color;
  ctx.lineWidth = 2.5;
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';

  data.forEach((val, i) => {
    const x = (i / (data.length - 1)) * (w - 12) + 6;
    const y = h - ((val - min) / range) * (h - 12) - 6;
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();

  // Subtle gradient fill under curve
  const grad = ctx.createLinearGradient(0, 0, 0, h);
  grad.addColorStop(0, 'rgba(255, 46, 147, 0.25)');
  grad.addColorStop(1, 'rgba(255, 46, 147, 0.0)');
  ctx.lineTo(w - 6, h);
  ctx.lineTo(6, h);
  ctx.closePath();
  ctx.fillStyle = grad;
  ctx.fill();
}

/**
 * Render Horizontal Bar Chart of Biggest Movers with Chart.js.
 */
function renderMoversChart() {
  const canvas = document.getElementById('moversChart');
  if (!canvas) return;

  // Take top 8 highest movers and bottom 4 decliners
  const sorted = [...AppState.items].sort((a, b) => b.growth_rate - a.growth_rate);
  const displayItems = sorted.slice(0, 10);

  const labels = displayItems.map(i => i.name.toUpperCase());
  const data = displayItems.map(i => i.growth_rate);
  const colors = displayItems.map(i => {
    if (i.status === 'Rising') return '#10b981'; // Green
    if (i.status === 'Declining') return '#ef4444'; // Red
    return '#f59e0b'; // Amber
  });

  if (AppState.charts.movers) {
    AppState.charts.movers.destroy();
  }

  const ctx = canvas.getContext('2d');
  AppState.charts.movers = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [{
        label: 'Growth Rate (%)',
        data: data,
        backgroundColor: colors,
        borderRadius: 6,
        borderSkipped: false
      }]
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (ctx) => {
              const item = displayItems[ctx.dataIndex];
              return ` Growth: ${item.growth_rate}% | Score: ${item.current_score} | Status: ${item.status}`;
            }
          }
        }
      },
      scales: {
        x: {
          grid: { color: '#e2e8f0' },
          ticks: {
            callback: (v) => `${v}%`,
            font: { family: 'Inter', weight: '600' }
          }
        },
        y: {
          grid: { display: false },
          ticks: { font: { family: 'Syne', weight: '700', size: 11 } }
        }
      }
    }
  });
}

/**
 * Render item selection chips for forecast comparison.
 */
function renderForecastChips() {
  const container = document.getElementById('forecastChipsContainer');
  if (!container) return;

  // Default selection if empty: top 3 items
  if (AppState.selectedForecastItems.length === 0 && AppState.items.length > 0) {
    AppState.selectedForecastItems = AppState.items.slice(0, 3).map(i => i.name);
  }

  // Available top 10 items to select from
  const candidateItems = AppState.items.slice(0, 12);

  container.innerHTML = candidateItems.map((item, idx) => {
    const isSelected = AppState.selectedForecastItems.includes(item.name);
    const colorIdx = AppState.selectedForecastItems.indexOf(item.name);
    const colorPill = isSelected && colorIdx >= 0 && colorIdx < CHART_COLORS.length
      ? `<span class="forecast-legend-pill" style="background:${CHART_COLORS[colorIdx].solid};"></span>`
      : '';

    return `
      <button 
        type="button" 
        class="forecast-chip ${isSelected ? 'selected' : ''}" 
        data-item="${item.name}"
        onclick="toggleForecastItem('${item.name}')"
      >
        ${colorPill}
        <span>${item.name}</span>
      </button>
    `;
  }).join('');
}

/**
 * Toggle forecast item selection (max 5 items).
 */
function toggleForecastItem(itemName) {
  const idx = AppState.selectedForecastItems.indexOf(itemName);
  if (idx > -1) {
    if (AppState.selectedForecastItems.length > 1) {
      AppState.selectedForecastItems.splice(idx, 1);
    } else {
      alert("Please keep at least one item selected for forecasting.");
      return;
    }
  } else {
    if (AppState.selectedForecastItems.length >= 5) {
      alert("You can compare up to 5 items simultaneously on the forecast chart.");
      return;
    }
    AppState.selectedForecastItems.push(itemName);
  }

  renderForecastChips();
  fetchAndRenderForecast();
}

/**
 * Fetch forecast series from /api/forecast and render Chart.js multi-line graph.
 */
async function fetchAndRenderForecast() {
  const canvas = document.getElementById('forecastChart');
  if (!canvas) return;

  const itemsParam = encodeURIComponent(AppState.selectedForecastItems.join(','));
  const sampleParam = AppState.forceSample ? '1' : '0';
  const url = `/api/forecast?items=${itemsParam}&geo=${AppState.geo}&timeframe=${AppState.timeframe}&sample=${sampleParam}`;

  let data;
  try {
    const res = await fetch(url);
    if (!res.ok) throw new Error(`HTTP error ${res.status}`);
    data = await res.json();
  } catch (apiErr) {
    console.warn('Forecast API unreachable, checking fallback data/forecast.json:', apiErr);
    try {
      const fallbackRes = await fetch('data/forecast.json');
      if (fallbackRes.ok) {
        data = await fallbackRes.json();
      } else {
        return;
      }
    } catch (e) {
      return;
    }
  }

    const historicalDates = data.historical_dates || [];
    const futureDates = data.future_dates || [];
    const allDates = data.all_dates || [...historicalDates, ...futureDates];
    const forecasts = data.forecasts || {};

    const datasets = [];
    const trajectoryPills = [];

    let colorCounter = 0;
    for (const [itemName, forecastObj] of Object.entries(forecasts)) {
      const palette = CHART_COLORS[colorCounter % CHART_COLORS.length];
      colorCounter++;

      // Find historical series directly from API response or AppState
      const match = AppState.items.find(i => i.name.toLowerCase() === itemName.toLowerCase());
      const historicalValues = (data.historical_series && (data.historical_series[itemName] || data.historical_series[itemName.toLowerCase()]))
        || (match ? match.full_series : []);
      const forecastValues = forecastObj.forecast_values || [];

      // Historical Solid Line
      const solidData = [...historicalValues];
      // Future points filled with null for the historical line
      for (let i = 0; i < futureDates.length; i++) {
        solidData.push(null);
      }

      datasets.push({
        label: `${itemName} (Historical)`,
        data: solidData,
        borderColor: palette.solid,
        backgroundColor: 'transparent',
        borderWidth: 2.5,
        tension: 0.3,
        pointRadius: 0,
        pointHoverRadius: 5
      });

      // Forecast Dashed Line (Begins at the last historical point)
      const dashedData = [];
      const lastHistVal = historicalValues.length > 0 ? historicalValues[historicalValues.length - 1] : null;

      for (let i = 0; i < historicalValues.length - 1; i++) {
        dashedData.push(null);
      }
      dashedData.push(lastHistVal); // Connect point
      for (const val of forecastValues) {
        dashedData.push(val);
      }

      datasets.push({
        label: `${itemName} (8-Week Forecast)`,
        data: dashedData,
        borderColor: palette.solid,
        backgroundColor: palette.fill,
        borderWidth: 2.5,
        borderDash: [6, 6], // Dashed line continuation!
        tension: 0.2,
        pointRadius: 3,
        pointHoverRadius: 6,
        fill: false
      });

      // Trajectory label pill
      const trajClass = forecastObj.label === 'Expected to rise' ? 'rise' :
                        forecastObj.label === 'Expected to fall' ? 'fall' : 'hold';
      const arrowIcon = forecastObj.label === 'Expected to rise' ? '↗' :
                        forecastObj.label === 'Expected to fall' ? '↘' : '→';

      trajectoryPills.push(`
        <div class="traj-pill ${trajClass}">
          <span style="background:${palette.solid}; width:8px; height:8px; border-radius:50%; display:inline-block;"></span>
          <strong>${itemName.toUpperCase()}:</strong> ${arrowIcon} ${forecastObj.label} (Slope: ${forecastObj.slope > 0 ? '+' : ''}${forecastObj.slope})
        </div>
      `);
    }

    // Render Trajectory Badges
    const trajContainer = document.getElementById('forecastTrajectoriesList');
    if (trajContainer) {
      trajContainer.innerHTML = trajectoryPills.join('');
    }

    // Destroy prior chart instance if exists
    if (AppState.charts.forecast) {
      AppState.charts.forecast.destroy();
    }

    const ctx = canvas.getContext('2d');
    AppState.charts.forecast = new Chart(ctx, {
      type: 'line',
      data: {
        labels: allDates,
        datasets: datasets
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: 'index',
          intersect: false
        },
        plugins: {
          legend: {
            display: true,
            position: 'top',
            labels: {
              boxWidth: 14,
              font: { family: 'Inter', size: 11, weight: '600' }
            }
          },
          tooltip: {
            callbacks: {
              label: (ctx) => {
                if (ctx.raw === null || ctx.raw === undefined) return null;
                return ` ${ctx.dataset.label}: ${ctx.raw}/100`;
              }
            }
          }
        },
        scales: {
          x: {
            grid: { display: false },
            ticks: {
              maxTicksLimit: 10,
              font: { family: 'Inter', size: 10 }
            }
          },
          y: {
            min: 0,
            max: 100,
            grid: { color: '#f1f5f9' },
            ticks: {
              callback: (v) => `${v}`,
              font: { family: 'Inter', weight: '600' }
            }
          }
        }
      }
    });

  } catch (err) {
    console.error('Forecast chart error:', err);
  }
}

/**
 * Render All Items Table with sorting, filtering, and mini sparklines.
 */
function renderItemsTable() {
  const tbody = document.getElementById('itemsTableBody');
  const countSpan = document.getElementById('tableSummaryCount');
  if (!tbody) return;

  // Filter items by search query
  let filtered = AppState.items.filter(item => {
    if (!AppState.searchQuery) return true;
    return item.name.toLowerCase().includes(AppState.searchQuery) ||
           item.category.toLowerCase().includes(AppState.searchQuery);
  });

  // Sort items
  filtered.sort((a, b) => {
    let valA = a[AppState.sortCol];
    let valB = b[AppState.sortCol];

    if (AppState.sortCol === 'name') {
      return AppState.sortDir === 'asc' ? valA.localeCompare(valB) : valB.localeCompare(valA);
    }
    if (AppState.sortCol === 'category') {
      return AppState.sortDir === 'asc' ? valA.localeCompare(valB) : valB.localeCompare(valA);
    }
    if (AppState.sortCol === 'score') {
      valA = a.current_score;
      valB = b.current_score;
    } else if (AppState.sortCol === 'growth') {
      valA = a.growth_rate;
      valB = b.growth_rate;
    } else if (AppState.sortCol === 'status') {
      valA = a.status;
      valB = b.status;
      return AppState.sortDir === 'asc' ? valA.localeCompare(valB) : valB.localeCompare(valA);
    }

    return AppState.sortDir === 'asc' ? valA - valB : valB - valA;
  });

  if (countSpan) {
    countSpan.textContent = `Showing ${filtered.length} of ${AppState.items.length} fashion items`;
  }

  if (filtered.length === 0) {
    tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; padding: 2.5rem; color: var(--text-muted);">No clothing items matched "${AppState.searchQuery}".</td></tr>`;
    return;
  }

  tbody.innerHTML = filtered.map(item => {
    const slug = toSlug(item.name);
    const growthSign = item.growth_rate > 0 ? '+' : '';
    const statusClass = item.status === 'Rising' ? 'status-rising' :
                        item.status === 'Declining' ? 'status-declining' : 'status-stable';
    const statusIcon = item.status === 'Rising' ? '▲' :
                       item.status === 'Declining' ? '▼' : '●';
    const heartActive = item.is_favourite ? 'active' : '';
    const initial = item.name.charAt(0).toUpperCase();

    return `
      <tr>
        <!-- Item Cell with Image and Fallback -->
        <td>
          <div class="item-cell">
            <div class="item-thumb">
              <img 
                src="/static/images/${slug}.jpg" 
                alt="${item.name}" 
                class="item-thumb-img"
                onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';"
              >
              <div class="thumb-fallback" style="display: none;">${initial}</div>
            </div>
            <div class="item-info-text">
              <span class="item-title-bold">${item.name}</span>
            </div>
          </div>
        </td>

        <!-- Category -->
        <td>
          <span class="item-category-tag">${item.category}</span>
        </td>

        <!-- Current Score Bar -->
        <td>
          <div class="score-bar-wrap">
            <span style="font-weight: 700; width: 28px;">${item.current_score}</span>
            <div class="score-bar-bg">
              <div class="score-bar-fill" style="width: ${item.current_score}%;"></div>
            </div>
          </div>
        </td>

        <!-- Growth Rate -->
        <td>
          <span style="font-weight: 800; font-family: 'Syne', sans-serif; color: ${item.growth_rate >= 15 ? '#059669' : (item.growth_rate <= -15 ? '#dc2626' : '#d97706')};">
            ${growthSign}${item.growth_rate}%
          </span>
        </td>

        <!-- Status Pill -->
        <td>
          <span class="status-pill ${statusClass}">
            ${statusIcon} ${item.status}
          </span>
        </td>

        <!-- Mini Sparkline -->
        <td>
          <canvas class="table-sparkline" data-sparkline='${JSON.stringify(item.sparkline)}'></canvas>
        </td>

        <!-- Save Button -->
        <td>
          <button 
            type="button" 
            class="btn-icon btn-heart ${heartActive}" 
            title="Save ${item.name}" 
            onclick="toggleFavourite('${item.name}', '${item.category}', this)"
          >
            ♥
          </button>
        </td>
      </tr>
    `;
  }).join('');

  // Render Table Mini Sparklines
  tbody.querySelectorAll('.table-sparkline').forEach(canvas => {
    try {
      const data = JSON.parse(canvas.getAttribute('data-sparkline'));
      drawSparkline(canvas, data, '#8b5cf6');
    } catch (e) {
      console.warn('Table sparkline error', e);
    }
  });
}

/**
 * Toggle Item Save / Favourite via POST /api/favourites/toggle.
 * Prompts anonymous users to log in.
 */
async function toggleFavourite(itemName, category, buttonEl) {
  const token = getCsrfToken();

  try {
    const res = await fetch('/api/favourites/toggle', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': token
      },
      body: JSON.stringify({ item_name: itemName, category })
    });

    const data = await res.json();

    if (res.status === 401) {
      // Prompt user to log in if unauthorized
      if (confirm("Log in to save this item to your personal favourites. Would you like to log in now?")) {
        window.location.href = data.login_url || '/login';
      }
      return;
    }

    if (res.ok) {
      const isSaved = data.saved;
      // Toggle button visual state
      if (buttonEl) {
        buttonEl.classList.toggle('active', isSaved);
      }
      // Sync across all buttons with same item name
      document.querySelectorAll(`button[onclick*="'${itemName}'"]`).forEach(btn => {
        btn.classList.toggle('active', isSaved);
      });

      // Update in-memory state
      const item = AppState.items.find(i => i.name.toLowerCase() === itemName.toLowerCase());
      if (item) item.is_favourite = isSaved;
    } else {
      alert(data.error || 'Failed to update favourite.');
    }
  } catch (err) {
    console.warn('Backend unavailable, using localStorage for favourites:', err);
    let favs = JSON.parse(localStorage.getItem('betrendy_favourites') || '[]');
    const isSaved = favs.includes(itemName);
    if (isSaved) {
      favs = favs.filter(x => x !== itemName);
    } else {
      favs.push(itemName);
    }
    localStorage.setItem('betrendy_favourites', JSON.stringify(favs));
    document.querySelectorAll(`button[onclick*="'${itemName}'"]`).forEach(btn => {
      btn.classList.toggle('active', !isSaved);
    });
    const item = AppState.items.find(i => i.name.toLowerCase() === itemName.toLowerCase());
    if (item) item.is_favourite = !isSaved;
  }
}
