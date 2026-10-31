// ── State ──────────────────────────────────────────────────────────────────

const DEFAULT_STYLE = 'bordered';
const DEFAULT_TAG_COLOR = '#00000000';
const DEFAULT_BORDER_COLOR = '#FFFFFFFF';

let translations = I18N.en;
let manifest = null;
let fragments = {};
let selectedBadges = new Set();
let groupOrder = [];
let badgeOrder = {};
let currentStyle = DEFAULT_STYLE;
let fillColor = '#000000';
let fillOpacity = 100;
let borderColor = '#ffffff';
let borderOpacity = 100;
let iconColor = '#ffffff';

// Color presets — per-badge border colors
const PRESETS = {
  default: {
    name: 'None',
    bordered: { borderColor: '#ffffff', borderOpacity: 100, iconColor: '#ffffff' },
    filled: { borderColor: '#ffffff', borderOpacity: 100, fillColor: '#000000', fillOpacity: 100, iconColor: '#ffffff' },
    badgeColors: {}
  },
  colorful: {
    name: 'Colorful',
    bordered: { borderColor: '#ffffff', borderOpacity: 100, iconColor: '#ffffff' },
    filled: { borderColor: '#000000', borderOpacity: 0, fillColor: '#000000', fillOpacity: 80, iconColor: '#ffffff' },
    badgeColors: {
      'p-remux': '#ff6600', 'p-bluray': '#dd8800', 'p-webdl': '#ccaa00', 'p-webrip': '#ccaa00',
      'p-hdtv': '#888888', 'p-dvdscr': '#666666', 'p-dvdrip': '#666666', 'p-cam': '#555555', 'p-r5': '#555555',
      'p-8k': '#00ee55', 'p-4k': '#33cc44', 'p-1440p': '#55aa44', 'p-1080p': '#778844', 'p-720p': '#888855', 'p-480p': '#777766',
      'p-imax-e': '#ff3333', 'p-imax': '#ff3333', 'p-seadex': '#44ddaa',
      'p-dv': '#55aaff', 'p-hdr10p': '#55aaff', 'p-hdr10': '#55aaff', 'p-hlg': '#55aaff', 'p-hdr': '#55aaff',
      'p-atmos': '#999999', 'p-truehd': '#999999', 'p-ddp': '#888888', 'p-dd': '#888888',
      'p-dtsx': '#999999', 'p-dtshdma': '#999999', 'p-dtshd': '#888888', 'p-dts': '#888888',
      'p-flac': '#888888', 'p-opus': '#888888', 'p-aac': '#777777', 'p-ac4': '#777777',
      'p-71': '#888888', 'p-51': '#888888', 'p-20': '#777777', 'p-10': '#777777',
    }
  },
  neon: {
    name: 'Neon',
    bordered: { borderColor: '#00ffcc', borderOpacity: 80, iconColor: '#00ffcc' },
    filled: { borderColor: '#00ffcc', borderOpacity: 0, fillColor: '#003333', fillOpacity: 80, iconColor: '#00ffcc' },
    badgeColors: {}
  },
  stealth: {
    name: 'Stealth',
    bordered: { borderColor: '#ffffff', borderOpacity: 20, iconColor: '#aaaaaa' },
    filled: { borderColor: '#ffffff', borderOpacity: 10, fillColor: '#ffffff', fillOpacity: 10, iconColor: '#aaaaaa' },
    badgeColors: {}
  },
  gold: {
    name: 'Gold',
    bordered: { borderColor: '#d4a843', borderOpacity: 100, iconColor: '#d4a843' },
    filled: { borderColor: '#d4a843', borderOpacity: 100, fillColor: '#d4a843', fillOpacity: 40, iconColor: '#d4a843' },
    badgeColors: {}
  },
};
let activePreset = null;
let badgeColors = {}; // badgeId → border hex color (per-badge override from preset)

function getContext() {
  return document.querySelector('#context-cards .context-card.active')?.dataset.value || 'player';
}

// Convert hex color (#rrggbb) + opacity (0-100) to #AARRGGBB format
function toArgb(hex, opacity) {
  const alpha = Math.round(opacity * 2.55).toString(16).padStart(2, '0').toUpperCase();
  return '#' + alpha + hex.replace('#', '').toUpperCase();
}

function applyPreset(key) {
  const p = PRESETS[key];
  if (!p) return;
  activePreset = key;
  const variant = p[currentStyle] || p.bordered;
  borderColor = variant.borderColor; borderOpacity = variant.borderOpacity;
  fillColor = variant.fillColor || '#000000'; fillOpacity = variant.fillOpacity || 100;
  iconColor = variant.iconColor;
  badgeColors = { ...(p.badgeColors || {}) };

  // Update UI controls (don't change style pill)
  document.getElementById('border-color-picker').value = borderColor;
  document.getElementById('border-color-hex').value = borderColor;
  document.getElementById('border-opacity').value = borderOpacity;
  document.getElementById('border-opacity-value').textContent = borderOpacity + '%';
  document.getElementById('fill-color-picker').value = fillColor;
  document.getElementById('fill-color-hex').value = fillColor;
  document.getElementById('fill-opacity').value = fillOpacity;
  document.getElementById('fill-opacity-value').textContent = fillOpacity + '%';
  document.getElementById('icon-color-picker').value = iconColor;
  document.getElementById('icon-color-hex').value = iconColor;

  // Highlight active preset
  document.querySelectorAll('.preset-pill').forEach(pill =>
    pill.classList.toggle('active', pill.dataset.key === key)
  );

  // Disable manual color controls when preset defines per-badge colors
  const hasCustomColors = Object.keys(p.badgeColors || {}).length > 0;
  document.getElementById('color-controls').classList.toggle('color-controls-disabled', hasCustomColors);

  updatePreview();
}

// Recolor SVG data URI: replace white fills/strokes with target color
function recolorDataUri(dataUri, color) {
  if (color === '#ffffff' || color === '#FFFFFF') return dataUri;
  const svg = atob(dataUri.split(',')[1]);
  const hex = color.toLowerCase();
  const recolored = svg
    .replace(/fill="white"/g, `fill="${hex}"`)
    .replace(/fill="#ffffff"/gi, `fill="${hex}"`)
    .replace(/fill:#ffffff/gi, `fill:${hex}`)
    .replace(/stroke="white"/g, `stroke="${hex}"`)
    .replace(/stroke:#ffffff/gi, `stroke:${hex}`)
    // Also handle fill-opacity on recolored elements
    .replace(/fill="white"/g, `fill="${hex}"`);
  return 'data:image/svg+xml;base64,' + btoa(recolored);
}

// ── Persistence ────────────────────────────────────────────────────────────

const STORAGE_KEY = 'nuvio-badge-editor';

function saveState() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({
      locale: document.getElementById('locale-select')?.value,
      context: getContext(),
      style: currentStyle,
      fillColor,
      fillOpacity,
      borderColor,
      borderOpacity,
      iconColor,
      selectedBadges: [...selectedBadges],
      groupOrder,
    }));
  } catch {}
}

function loadState() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch { return null; }
}

// ── i18n ───────────────────────────────────────────────────────────────────

function detectBrowserLocale() {
  const lang = (navigator.language || 'en').substring(0, 2);
  return I18N[lang] ? lang : 'en';
}

function applyTranslations(lang) {
  translations = I18N[lang] || I18N.en;
  document.getElementById('t-title').textContent = translations.title;
  document.getElementById('t-sub').textContent = translations.sub;
  document.getElementById('t-settings').textContent = translations.settings;
  document.getElementById('t-context').textContent = translations.context;
  document.getElementById('t-locale').textContent = translations.locale;
  document.getElementById('t-style').textContent = translations.style;
  document.getElementById('pill-bordered').textContent = translations.bordered;
  document.getElementById('pill-filled').textContent = translations.filled;
  document.getElementById('t-preview').textContent = translations.preview;
  document.getElementById('t-preview-desktop').textContent = translations.preview;
  document.getElementById('t-url').textContent = translations.url;
  document.getElementById('btn-copy-url').textContent = translations.copyUrl;
  document.getElementById('btn-copy-json').textContent = translations.copyJson;
  document.getElementById('btn-toggle-json').textContent = translations.showHide;
  document.title = translations.title;
  document.documentElement.lang = lang;
}

// ── Init ───────────────────────────────────────────────────────────────────

async function init() {
  const uiLang = detectBrowserLocale();
  applyTranslations(uiLang);

  manifest = await fetch('/output/manifest.json').then(r => r.json());

  // Populate locale selector
  const localeSelect = document.getElementById('locale-select');
  manifest.availableLocales.forEach(locale => {
    const option = document.createElement('option');
    option.value = locale;
    option.textContent = locale === 'iso' ? 'ISO (ENG, POL...)' : locale.toUpperCase();
    localeSelect.appendChild(option);
  });

  // Set default locale based on browser
  const saved = loadState();
  const defaultLocale = saved?.locale
    || (manifest.availableLocales.includes(uiLang) ? uiLang : 'en');
  localeSelect.value = defaultLocale;
  localeSelect.addEventListener('change', () => loadBadges());

  // Context cards
  document.querySelectorAll('#context-cards .context-card').forEach(card => {
    card.addEventListener('click', () => {
      document.querySelectorAll('#context-cards .context-card').forEach(c =>
        c.classList.toggle('active', c === card)
      );
      loadBadges();
    });
  });
  if (saved?.context) {
    document.querySelectorAll('#context-cards .context-card').forEach(c =>
      c.classList.toggle('active', c.dataset.value === saved.context)
    );
  }

  // Restore style
  if (saved?.style) {
    currentStyle = saved.style;
    document.querySelectorAll('#style-pills .pill').forEach(p =>
      p.classList.toggle('active', p.dataset.value === currentStyle)
    );
  }
  document.getElementById('fill-row').classList.toggle('visible', currentStyle === 'filled');
  if (saved?.fillColor) {
    fillColor = saved.fillColor;
    document.getElementById('fill-color-picker').value = fillColor;
    document.getElementById('fill-color-hex').value = fillColor;
  }
  if (saved?.fillOpacity != null) {
    fillOpacity = saved.fillOpacity;
    document.getElementById('fill-opacity').value = fillOpacity;
    document.getElementById('fill-opacity-value').textContent = fillOpacity + '%';
  }
  if (saved?.borderColor) {
    borderColor = saved.borderColor;
    document.getElementById('border-color-picker').value = borderColor;
    document.getElementById('border-color-hex').value = borderColor;
  }
  if (saved?.borderOpacity != null) {
    borderOpacity = saved.borderOpacity;
    document.getElementById('border-opacity').value = borderOpacity;
    document.getElementById('border-opacity-value').textContent = borderOpacity + '%';
  }
  if (saved?.iconColor) {
    iconColor = saved.iconColor;
    document.getElementById('icon-color-picker').value = iconColor;
    document.getElementById('icon-color-hex').value = iconColor;
  }

  // Style pills
  document.querySelectorAll('#style-pills .pill').forEach(pill => {
    pill.addEventListener('click', () => {
      currentStyle = pill.dataset.value;
      document.querySelectorAll('#style-pills .pill').forEach(p =>
        p.classList.toggle('active', p === pill)
      );
      document.getElementById('fill-row').classList.toggle('visible', currentStyle === 'filled');
      if (activePreset) applyPreset(activePreset);
      else updatePreview();
    });
  });

  // Presets
  const presetRow = document.getElementById('preset-row');
  for (const [key, preset] of Object.entries(PRESETS)) {
    const pill = document.createElement('span');
    pill.className = 'preset-pill' + (key === 'default' ? ' active' : '');
    pill.textContent = preset.name;
    pill.dataset.key = key;
    pill.addEventListener('click', () => applyPreset(key));
    presetRow.appendChild(pill);
  }

  // Icon (badge content) color
  function clearPreset() {
    activePreset = 'default';
    badgeColors = {};
    document.querySelectorAll('.preset-pill').forEach(p =>
      p.classList.toggle('active', p.dataset.key === 'default')
    );
    document.getElementById('color-controls').classList.remove('color-controls-disabled');
  }

  document.getElementById('icon-color-picker').addEventListener('input', e => {
    clearPreset();
    iconColor = e.target.value;
    document.getElementById('icon-color-hex').value = iconColor;
    updatePreview();
  });
  document.getElementById('icon-color-hex').addEventListener('input', e => {
    const v = e.target.value;
    if (/^#[0-9a-fA-F]{6}$/.test(v)) {
      iconColor = v;
      document.getElementById('icon-color-picker').value = v;
      updatePreview();
    }
  });

  // Border color + opacity
  document.getElementById('border-color-picker').addEventListener('input', e => {
    clearPreset();
    borderColor = e.target.value;
    document.getElementById('border-color-hex').value = borderColor;
    updatePreview();
  });
  document.getElementById('border-color-hex').addEventListener('input', e => {
    const v = e.target.value;
    if (/^#[0-9a-fA-F]{6}$/.test(v)) {
      clearPreset();
      borderColor = v;
      document.getElementById('border-color-picker').value = v;
      updatePreview();
    }
  });
  document.getElementById('border-opacity').addEventListener('input', e => {
    clearPreset();
    borderOpacity = parseInt(e.target.value);
    document.getElementById('border-opacity-value').textContent = borderOpacity + '%';
    updatePreview();
  });

  // Fill color + opacity
  document.getElementById('fill-color-picker').addEventListener('input', e => {
    clearPreset();
    fillColor = e.target.value;
    document.getElementById('fill-color-hex').value = fillColor;
    updatePreview();
  });
  document.getElementById('fill-color-hex').addEventListener('input', e => {
    const v = e.target.value;
    if (/^#[0-9a-fA-F]{6}$/.test(v)) {
      clearPreset();
      fillColor = v;
      document.getElementById('fill-color-picker').value = v;
      updatePreview();
    }
  });
  document.getElementById('fill-opacity').addEventListener('input', e => {
    clearPreset();
    fillOpacity = parseInt(e.target.value);
    document.getElementById('fill-opacity-value').textContent = fillOpacity + '%';
    updatePreview();
  });

  // Reset everything
  document.getElementById('reset-style').addEventListener('click', () => {
    // Clear saved state
    localStorage.removeItem(STORAGE_KEY);
    // Reset style
    currentStyle = DEFAULT_STYLE;
    borderColor = '#ffffff'; borderOpacity = 100;
    fillColor = '#000000'; fillOpacity = 100;
    iconColor = '#ffffff';
    badgeColors = {};
    activePreset = 'default';
    document.querySelectorAll('.preset-pill').forEach(p =>
      p.classList.toggle('active', p.dataset.key === 'default')
    );
    document.getElementById('color-controls').classList.remove('color-controls-disabled');
    document.querySelectorAll('#style-pills .pill').forEach(p =>
      p.classList.toggle('active', p.dataset.value === currentStyle)
    );
    document.getElementById('fill-row').classList.remove('visible');
    document.getElementById('border-color-picker').value = '#ffffff';
    document.getElementById('border-color-hex').value = '#ffffff';
    document.getElementById('border-opacity').value = 100;
    document.getElementById('border-opacity-value').textContent = '100%';
    document.getElementById('fill-color-picker').value = '#000000';
    document.getElementById('fill-color-hex').value = '#000000';
    document.getElementById('fill-opacity').value = 100;
    document.getElementById('fill-opacity-value').textContent = '100%';
    document.getElementById('icon-color-picker').value = '#ffffff';
    document.getElementById('icon-color-hex').value = '#ffffff';
    // Reset context to player
    document.querySelectorAll('#context-cards .context-card').forEach(c =>
      c.classList.toggle('active', c.dataset.value === 'player')
    );
    // Reload all badges (resets selection, group order)
    loadBadges(true);
  });

  // Copy buttons
  document.getElementById('btn-copy-url').addEventListener('click', () => copyToClipboard('url'));
  document.getElementById('btn-copy-json').addEventListener('click', () => copyToClipboard('json'));
  document.getElementById('btn-toggle-json').addEventListener('click', () => {
    document.getElementById('json-output').classList.toggle('hidden');
  });

  // Preview collapse toggle (mobile) — default collapsed on small screens
  const previewPanel = document.getElementById('preview-panel');
  document.getElementById('preview-toggle').addEventListener('click', () => {
    previewPanel.classList.toggle('collapsed');
  });
  if (window.innerWidth <= 800) {
    previewPanel.classList.add('collapsed');
  }

  // Remove collapsed state when resizing to desktop, add when entering mobile
  window.addEventListener('resize', () => {
    if (window.innerWidth > 800) {
      previewPanel.classList.remove('collapsed');
    } else {
      previewPanel.classList.add('collapsed');
    }
  });

  loadBadges();
}

// ── Load badges ────────────────────────────────────────────────────────────

async function loadBadges(forceSelectAll = false) {
  const locale = document.getElementById('locale-select').value;
  const context = getContext();
  const saved = forceSelectAll ? null : loadState();
  const previousSelected = forceSelectAll ? new Set() : new Set(selectedBadges);
  fragments = {};
  selectedBadges.clear();
  groupOrder = manifest.groups.map(g => g.id);
  badgeOrder = {};

  // Restore group order if saved
  if (saved?.groupOrder) {
    const savedSet = new Set(saved.groupOrder);
    const validOrder = saved.groupOrder.filter(gid => manifest.groups.some(g => g.id === gid));
    const missing = groupOrder.filter(gid => !savedSet.has(gid));
    groupOrder = [...validOrder, ...missing];
  }

  // Load all fragments in one request
  try {
    const bundle = await fetch(`/output/bundles/${context}-${locale}.json`).then(r => r.json());
    for (const [id, fragment] of Object.entries(bundle)) {
      fragments[id] = fragment;
    }
  } catch (e) {
    console.warn('Bundle not found, falling back to en', e);
    try {
      const bundle = await fetch(`/output/bundles/${context}-en.json`).then(r => r.json());
      for (const [id, fragment] of Object.entries(bundle)) {
        fragments[id] = fragment;
      }
    } catch {}
  }

  // Build deselected set from previous state or saved state.
  // Static badges (res, hdr, etc.) share IDs across contexts.
  // Language badges have separate p-*/s-* IDs — map between them.
  let deselectedIds = new Set();
  const referenceSelected = previousSelected.size > 0
    ? previousSelected
    : (saved?.selectedBadges ? new Set(saved.selectedBadges) : null);

  if (referenceSelected) {
    // Collect all filter IDs that could have been visible in previous state
    const prevContext = saved?.context || 'player';
    const allPrevIds = new Set();
    for (const f of manifest.filters) {
      if (f.context === 'player' && prevContext !== 'player') continue;
      if (f.context === 'source' && prevContext !== 'source') continue;
      allPrevIds.add(f.id);
    }

    for (const id of allPrevIds) {
      if (!referenceSelected.has(id)) {
        deselectedIds.add(id);
        // Map language badge IDs across contexts (p-eng ↔ s-eng)
        const base = id.substring(2); // strip p- or s-
        if (id.startsWith('p-')) deselectedIds.add('s-' + base);
        if (id.startsWith('s-')) deselectedIds.add('p-' + base);
      }
    }
  }

  for (const group of manifest.groups) {
    const groupFilters = manifest.filters.filter(f => {
      if (f.groupId !== group.id) return false;
      if (f.context === 'player' && context !== 'player') return false;
      if (f.context === 'source' && context !== 'source') return false;
      return true;
    });
    badgeOrder[group.id] = groupFilters.map(f => f.id);

    for (const filter of groupFilters) {
      if (!fragments[filter.id]) continue;
      if (deselectedIds.has(filter.id)) continue;
      selectedBadges.add(filter.id);
    }
  }

  buildSidebar();
  updatePreview();
}

// ── Build sidebar ──────────────────────────────────────────────────────────

function buildSidebar() {
  const container = document.getElementById('groups-container');
  container.innerHTML = '';

  for (const groupId of groupOrder) {
    const group = manifest.groups.find(g => g.id === groupId);
    if (!group) continue;
    const badgeIds = badgeOrder[groupId] || [];
    if (badgeIds.length === 0) continue;

    const section = document.createElement('div');
    section.className = 'group-section';
    section.dataset.groupId = groupId;
    section.draggable = true;

    // Group drag & drop
    section.addEventListener('dragstart', event => {
      event.dataTransfer.setData('group', groupId);
      section.style.opacity = '0.4';
    });
    section.addEventListener('dragend', () => { section.style.opacity = ''; });
    section.addEventListener('dragover', event => {
      if (event.dataTransfer.types.includes('group')) {
        event.preventDefault();
        section.classList.add('drag-over');
      }
    });
    section.addEventListener('dragleave', () => section.classList.remove('drag-over'));
    section.addEventListener('drop', event => {
      section.classList.remove('drag-over');
      const fromId = event.dataTransfer.getData('group');
      if (!fromId || fromId === groupId) return;
      const fromIndex = groupOrder.indexOf(fromId);
      const toIndex = groupOrder.indexOf(groupId);
      groupOrder.splice(fromIndex, 1);
      groupOrder.splice(toIndex, 0, fromId);
      buildSidebar();
      updatePreview();
    });

    // Header
    const header = document.createElement('div');
    header.className = 'group-header';

    const groupIndex = groupOrder.indexOf(groupId);

    // Move buttons (mobile — drag doesn't work on touch)
    const moveUp = document.createElement('span');
    moveUp.className = 'move-btn move-up';
    moveUp.textContent = '▲';
    moveUp.style.visibility = groupIndex === 0 ? 'hidden' : '';
    moveUp.addEventListener('click', event => {
      event.stopPropagation();
      if (groupIndex > 0) {
        groupOrder.splice(groupIndex, 1);
        groupOrder.splice(groupIndex - 1, 0, groupId);
        buildSidebar();
        updatePreview();
      }
    });

    const moveDown = document.createElement('span');
    moveDown.className = 'move-btn move-down';
    moveDown.textContent = '▼';
    moveDown.style.visibility = groupIndex === groupOrder.length - 1 ? 'hidden' : '';
    moveDown.addEventListener('click', event => {
      event.stopPropagation();
      if (groupIndex < groupOrder.length - 1) {
        groupOrder.splice(groupIndex, 1);
        groupOrder.splice(groupIndex + 1, 0, groupId);
        buildSidebar();
        updatePreview();
      }
    });

    header.innerHTML = `<span class="group-drag-handle">&#9776;</span><span class="group-name">${group.name}</span>`;
    header.appendChild(moveUp);
    header.appendChild(moveDown);

    const toggleBtn = document.createElement('label');
    toggleBtn.className = 'group-toggle';
    const toggleInput = document.createElement('input');
    toggleInput.type = 'checkbox';
    toggleInput.checked = badgeIds.some(id => selectedBadges.has(id));
    toggleInput.addEventListener('change', event => {
      event.stopPropagation();
      const badgeEls = section.querySelectorAll('.badge-item');
      badgeIds.forEach(id => {
        if (toggleInput.checked) selectedBadges.add(id);
        else selectedBadges.delete(id);
      });
      badgeEls.forEach(el => {
        el.classList.toggle('selected', selectedBadges.has(el.dataset.id));
      });
      updatePreview();
    });
    const toggleSlider = document.createElement('span');
    toggleSlider.className = 'toggle-slider';
    toggleBtn.appendChild(toggleInput);
    toggleBtn.appendChild(toggleSlider);
    header.appendChild(toggleBtn);
    section.appendChild(header);

    // Badge grid
    const grid = document.createElement('div');
    grid.className = 'badge-grid';
    grid.dataset.groupId = groupId;

    for (const badgeId of badgeIds) {
      const fragment = fragments[badgeId];
      if (!fragment) continue;

      const item = document.createElement('div');
      item.className = 'badge-item' + (selectedBadges.has(badgeId) ? ' selected' : '');
      item.dataset.id = badgeId;
      item.innerHTML = `<img src="${fragment.imageURL}" title="${fragment.name}">`;

      // Click to toggle
      item.addEventListener('click', () => {
        if (selectedBadges.has(badgeId)) selectedBadges.delete(badgeId);
        else selectedBadges.add(badgeId);
        item.classList.toggle('selected');
        updatePreview();
      });

      // Badge drag & drop (within lang group only — source context will show multiple)
      if (groupId === 'lang') {
        item.draggable = true;
        item.addEventListener('dragstart', event => {
          event.stopPropagation();
          event.dataTransfer.setData('badge', badgeId);
          event.dataTransfer.setData('sourceGroup', groupId);
          item.classList.add('dragging');
        });
        item.addEventListener('dragend', () => item.classList.remove('dragging'));
        item.addEventListener('dragover', event => {
          if (event.dataTransfer.types.includes('badge')) event.preventDefault();
        });
        item.addEventListener('drop', event => {
          event.stopPropagation();
          const fromId = event.dataTransfer.getData('badge');
          const sourceGroup = event.dataTransfer.getData('sourceGroup');
          if (!fromId || sourceGroup !== groupId) return;
          const order = badgeOrder[groupId];
          const fromIndex = order.indexOf(fromId);
          const toIndex = order.indexOf(badgeId);
          order.splice(fromIndex, 1);
          order.splice(toIndex, 0, fromId);
          buildSidebar();
          updatePreview();
        });
      }

      grid.appendChild(item);
    }

    section.appendChild(grid);
    container.appendChild(section);
  }
}

// ── Update preview & output ────────────────────────────────────────────────

function updatePreview() {
  const previewContainer = document.getElementById('preview');
  previewContainer.innerHTML = '';

  const filters = [];

  for (const groupId of groupOrder) {
    for (const badgeId of (badgeOrder[groupId] || [])) {
      if (!selectedBadges.has(badgeId)) continue;
      const fragment = fragments[badgeId];
      if (!fragment) continue;

      // Render preview chip
      const chip = document.createElement('div');
      chip.className = 'preview-chip';

      const badgeBc = badgeColors[badgeId];
      const borderRgba = (() => {
        const bc = badgeBc || borderColor;
        const bo = badgeBc ? 100 : borderOpacity;
        return `rgba(${parseInt(bc.slice(1,3),16)},${parseInt(bc.slice(3,5),16)},${parseInt(bc.slice(5,7),16)},${bo/100})`;
      })();

      if (currentStyle === 'bordered') {
        chip.style.background = 'transparent';
        chip.style.border = `1px solid ${borderRgba}`;
      } else {
        // Filled: use badge color as fill too (if preset defines it)
        const fc = badgeBc || fillColor;
        const fo = badgeBc ? fillOpacity : fillOpacity;
        const fillRgba = `rgba(${parseInt(fc.slice(1,3),16)},${parseInt(fc.slice(3,5),16)},${parseInt(fc.slice(5,7),16)},${fo/100})`;
        chip.style.background = fillRgba;
        chip.style.border = `1px solid ${borderRgba}`;
      }

      const img = document.createElement('img');
      img.src = recolorDataUri(fragment.imageURL, iconColor);
      chip.appendChild(img);
      previewContainer.appendChild(chip);

      // Build filter for JSON — #AARRGGBB format
      const badgeBorderColor = badgeColors[badgeId] || borderColor;
      const badgeBorderOpacity = badgeColors[badgeId] ? 100 : borderOpacity;
      const tagColorArgb = currentStyle === 'filled'
        ? toArgb(badgeColors[badgeId] || fillColor, fillOpacity)
        : '#00000000';
      const borderColorArgb = toArgb(badgeBorderColor, badgeBorderOpacity);

      filters.push({
        ...fragment,
        imageURL: recolorDataUri(fragment.imageURL, iconColor),
        tagStyle: currentStyle === 'bordered' ? 'bordered' : 'filled',
        tagColor: tagColorArgb,
        borderColor: borderColorArgb,
      });
    }
  }

  if (filters.length === 0) {
    const empty = document.createElement('span');
    empty.className = 'preview-empty';
    empty.textContent = translations.empty;
    previewContainer.appendChild(empty);
  }

  // Build JSON
  const activeGroups = [];
  for (const groupId of groupOrder) {
    if (filters.some(f => f.groupId === groupId)) {
      activeGroups.push(manifest.groups.find(g => g.id === groupId));
    }
  }

  const badgeJson = { groups: activeGroups, filters };
  document.getElementById('json-output').textContent = JSON.stringify(badgeJson, null, 2);

  // Build URL — scheme: g= (groups) + x= (exclusions) + go= (group order)
  const locale = document.getElementById('locale-select').value;
  const context = getContext();
  const activeGroupIds = groupOrder.filter(gid =>
    (badgeOrder[gid] || []).some(id => fragments[id] && selectedBadges.has(id))
  );

  let params = `l=${locale}`;
  if (context !== 'player') {
    params += `&c=${context}`;
  }

  // g= only when not all groups selected (omit = all groups)
  const allGroupIds = manifest.groups.map(g => g.id);
  const isAllGroups = activeGroupIds.length === allGroupIds.length &&
    allGroupIds.every(gid => activeGroupIds.includes(gid));
  if (!isAllGroups) {
    params += `&g=${activeGroupIds.join(',')}`;
  }

  // x= excluded badges (only IDs deselected from active groups)
  const excluded = [];
  for (const gid of activeGroupIds) {
    for (const id of (badgeOrder[gid] || [])) {
      if (fragments[id] && !selectedBadges.has(id)) excluded.push(id);
    }
  }
  if (excluded.length > 0) {
    params += `&x=${excluded.join(',')}`;
  }

  // Style + colors
  if (currentStyle !== DEFAULT_STYLE) {
    params += `&s=${currentStyle}`;
  }
  if (activePreset && activePreset !== 'default') {
    // Preset URL — short, cacheable
    params += `&p=${activePreset}`;
  } else {
    // Custom colors
    const tagColorArgbUrl = currentStyle === 'filled' ? toArgb(fillColor, fillOpacity) : '#00000000';
    const borderColorArgbUrl = toArgb(borderColor, borderOpacity);
    if (tagColorArgbUrl !== '#00000000') {
      params += `&tc=${encodeURIComponent(tagColorArgbUrl)}`;
    }
    if (borderColorArgbUrl !== '#FFFFFFFF') {
      params += `&bc=${encodeURIComponent(borderColorArgbUrl)}`;
    }
    if (iconColor !== '#ffffff') {
      params += `&ic=${encodeURIComponent(iconColor)}`;
    }
  }

  // go= group order (only when reordered from manifest default)
  const defaultGroupOrder = manifest.groups.map(g => g.id)
    .filter(gid => activeGroupIds.includes(gid));
  if (activeGroupIds.join(',') !== defaultGroupOrder.join(',')) {
    params += `&go=${activeGroupIds.join(',')}`;
  }

  // o.{gid}= badge order within group (only when reordered — not used in player context yet)
  for (const gid of activeGroupIds) {
    const currentOrder = (badgeOrder[gid] || []).filter(id => fragments[id] && selectedBadges.has(id));
    const manifestOrder = manifest.filters
      .filter(f => f.groupId === gid)
      .map(f => f.id)
      .filter(id => fragments[id] && selectedBadges.has(id));
    if (currentOrder.join(',') !== manifestOrder.join(',')) {
      params += `&o.${gid}=${currentOrder.join(',')}`;
    }
  }

  document.getElementById('url-output').value = `${location.origin}/v1/badge.json?${params}`;

  saveState();
}

// ── Clipboard ──────────────────────────────────────────────────────────────

function copyToClipboard(type) {
  const text = type === 'url'
    ? document.getElementById('url-output').value
    : document.getElementById('json-output').textContent;

  navigator.clipboard.writeText(text);

  const buttonId = type === 'url' ? 'btn-copy-url' : 'btn-copy-json';
  const button = document.getElementById(buttonId);
  const originalText = button.textContent;
  button.textContent = translations.copied;
  setTimeout(() => { button.textContent = originalText; }, 1500);
}

// ── Start ──────────────────────────────────────────────────────────────────

init();
