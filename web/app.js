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
let noBorder = false;

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
  document.getElementById('pill-none').textContent = translations.none;
  document.getElementById('t-fill').textContent = translations.fill;
  document.getElementById('t-noborder').textContent = translations.noborder;
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
  const defaultLocale = manifest.availableLocales.includes(uiLang) ? uiLang : 'en';
  localeSelect.value = defaultLocale;
  localeSelect.addEventListener('change', () => loadBadges());

  // Context selector
  document.getElementById('context-select').addEventListener('change', () => loadBadges());

  // Style pills
  document.querySelectorAll('#style-pills .pill').forEach(pill => {
    pill.addEventListener('click', () => {
      currentStyle = pill.dataset.value;
      document.querySelectorAll('#style-pills .pill').forEach(p =>
        p.classList.toggle('active', p === pill)
      );
      document.getElementById('filled-options').classList.toggle('visible', currentStyle === 'filled');
      updatePreview();
    });
  });

  // Fill color
  document.getElementById('fill-color-picker').addEventListener('input', event => {
    fillColor = event.target.value;
    document.getElementById('fill-color-hex').value = fillColor;
    updatePreview();
  });
  document.getElementById('fill-color-hex').addEventListener('input', event => {
    fillColor = event.target.value;
    updatePreview();
  });

  // No border checkbox
  document.getElementById('no-border-checkbox').addEventListener('change', event => {
    noBorder = event.target.checked;
    updatePreview();
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

async function loadBadges() {
  const locale = document.getElementById('locale-select').value;
  const context = document.getElementById('context-select').value;
  fragments = {};
  selectedBadges.clear();
  groupOrder = manifest.groups.map(g => g.id);
  badgeOrder = {};

  // Load all fragments in one request (bundle = static + lang for this locale/context)
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

  for (const group of manifest.groups) {
    const groupFilters = manifest.filters.filter(f => {
      if (f.groupId !== group.id) return false;
      if (f.context === 'player' && context !== 'player') return false;
      if (f.context === 'source' && context !== 'source') return false;
      return true;
    });
    badgeOrder[group.id] = groupFilters.map(f => f.id);

    for (const filter of groupFilters) {
      if (fragments[filter.id]) {
        selectedBadges.add(filter.id);
      }
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

    const toggleBtn = document.createElement('span');
    toggleBtn.className = 'group-toggle-btn';
    toggleBtn.textContent = translations.toggle;
    toggleBtn.addEventListener('click', event => {
      event.stopPropagation();
      const allSelected = badgeIds.every(id => selectedBadges.has(id));
      badgeIds.forEach(id => {
        if (allSelected) selectedBadges.delete(id);
        else selectedBadges.add(id);
      });
      buildSidebar();
      updatePreview();
    });
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

      if (currentStyle === 'bordered') {
        chip.style.background = 'transparent';
        chip.style.border = '1px solid rgba(255, 255, 255, 0.24)';
      } else if (currentStyle === 'filled') {
        chip.style.background = fillColor;
        chip.style.border = noBorder ? '1px solid transparent' : '1px solid rgba(255, 255, 255, 0.24)';
      } else {
        chip.style.background = 'transparent';
        chip.style.border = '1px solid transparent';
      }

      const img = document.createElement('img');
      img.src = fragment.imageURL;
      chip.appendChild(img);
      previewContainer.appendChild(chip);

      // Build filter for JSON
      const fillHex = fillColor.length === 7
        ? 'FF' + fillColor.substring(1)
        : fillColor.replace('#', '');

      filters.push({
        ...fragment,
        tagStyle: currentStyle === 'bordered' ? 'bordered' : 'filled',
        tagColor: currentStyle === 'filled' ? '#' + fillHex : '#00000000',
        borderColor: (currentStyle === 'none' || (currentStyle === 'filled' && noBorder))
          ? '#00000000'
          : '#FFFFFFFF',
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
  const context = document.getElementById('context-select').value;
  const activeGroupIds = groupOrder.filter(gid =>
    (badgeOrder[gid] || []).some(id => fragments[id] && selectedBadges.has(id))
  );

  let params = `l=${locale}`;
  if (context !== 'player') {
    params += `&c=${context}`;
  }

  // Always use g= with active groups
  params += `&g=${activeGroupIds.join(',')}`;

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

  // Style
  if (currentStyle !== DEFAULT_STYLE) {
    params += `&s=${currentStyle}`;
  }
  if (currentStyle === 'filled') {
    if (fillColor !== '#000000') {
      params += `&fc=${encodeURIComponent(fillColor)}`;
    }
    if (noBorder) {
      params += `&nb=1`;
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
