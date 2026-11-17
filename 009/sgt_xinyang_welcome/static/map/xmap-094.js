/* Xinyang Report Dashboard — Bản đồ khách hàng
 * v4.16.0: màu theo stage / salesperson / pipeline, cụm chia màu theo tỷ lệ, dải chip pipeline → stage,
 * bấm cụm ra danh sách deal, danh sách ↔ bản đồ liên kết 2 chiều, ẩn deal gốc đã copy (gom từ heatmap Argo).
 * Màu và tuỳ chọn lưu trên trình duyệt (localStorage), không ghi gì vào Odoo.
 */
(() => {
  'use strict';
  const $ = (id) => document.getElementById(id);
  const ui = {
    search: $('search'), searchText: $('searchText'), suggestions: $('eventSuggestions'), expo: $('filterExpo'),
    pipeline: $('filterPipeline'), stage: $('filterStage'), event: $('filterEvent'), eventLocation: $('filterLocation'),
    province: $('filterProvince'), district: $('filterDistrict'), owner: $('filterOwner'),
    tag: $('filterTag'), geo: $('filterGeo'), provider: $('filterProvider'), list: $('recordList'), more: $('loadMore'),
    syncStatus: $('syncStatus'), mapEmpty: $('mapEmpty'), emptyTitle: $('emptyTitle'), emptyDescription: $('emptyDescription'),
    strip: $('stageStrip'), legendItems: $('legendItems'), legendTitle: $('legendTitle'),
  };
  const COLORS_KEY = 'xinyang_map_colors_v1';
  const PREFS_KEY = 'xinyang_map_prefs_v1';
  const HEX = /^#[0-9A-Fa-f]{6}$/;
  const NEUTRAL = '#64748B';
  const PEOPLE_PALETTE = ['#142952', '#B72025', '#0F9EAA', '#C98A12', '#7C5CC4', '#2E7D32', '#AD1457', '#5D4037', '#00838F', '#6D4C41'];
  const PIPE_PALETTE = ['#142952', '#B72025', '#0F9EAA', '#C98A12', '#7C5CC4', '#2E7D32', '#AD1457', '#5D4037'];
  const POPUP_PAN = {autoPanPaddingTopLeft: [50, 64], autoPanPaddingBottomRight: [20, 30]};
  const CLUSTER_LIST_PAGE = 60;

  const readStore = (key, fallback) => {
    try { const v = JSON.parse(localStorage.getItem(key) || 'null'); return v && typeof v === 'object' ? v : fallback; }
    catch (_) { return fallback; }
  };
  const writeStore = (key, value) => { try { localStorage.setItem(key, JSON.stringify(value)); } catch (_) { /* chế độ riêng tư */ } };
  const prefs = Object.assign({colorBy: 'stage', showOrigin: false, clusterRadius: 46, mode: 'all'}, readStore(PREFS_KEY, {}));
  if (prefs.mode !== 'potential') prefs.mode = 'all';
  document.body.dataset.mapMode = prefs.mode;
  const custom = Object.assign({stage: {}, salesperson: {}, pipeline: {}}, readStore(COLORS_KEY, {}));

  const state = {
    records: [], visible: [], filtered: [], config: {}, status: {}, map: null, mapReady: false,
    showPoints: true, showHeat: false, rendered: 0, pageSize: 70, selectedId: null,
    stages: [], pipelines: [], stageById: new Map(), stageOrder: new Map(), pipeOrder: new Map(),
    peopleIndex: new Map(), markers: new Map(), hiddenOrigins: 0, geoQuick: '',
  };
  const fmt = (n) => Number(n || 0).toLocaleString(window.XINYANG_I18N ? window.XINYANG_I18N.locale() : 'vi-VN');
  const fold = (str) => String(str || '').normalize('NFD').replace(/[̀-ͯ]/g, '')
    .replace(/[đĐ]/g, 'd').toLowerCase().trim();
  const make = (tag, cls, val) => {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (val !== undefined && val !== null) e.textContent = String(val);
    return e;
  };
  const dot = (color) => { const i = make('i', 'cdot'); i.style.background = color; return i; };
  const url = (suffix) => new URL(suffix, window.location.origin).toString();
  const isMapped = (r) => r.geo_status === 'mapped' && Number.isFinite(r.lat) && Number.isFinite(r.lng) && Math.abs(r.lat) <= 90 && Math.abs(r.lng) <= 180 && !(r.lat === 0 && r.lng === 0);
  const recordTitle = (r) => r.company || r.name || ('CRM #' + r.id);

  /* ------------------------------------------------------------------ màu */
  function inkColor(hex) {
    if (!HEX.test(hex || '')) return '#FFFFFF';
    const lin = [1, 3, 5].map(i => parseInt(hex.slice(i, i + 2), 16) / 255)
      .map(c => c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4);
    return (0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]) > 0.36 ? '#18202F' : '#FFFFFF';
  }
  const stageKey = (r) => r.stage_id ? String(r.stage_id) : 'n:' + (r.stage || '');
  const pipeKey = (r) => r.pipeline_id ? String(r.pipeline_id) : 'n:' + (r.pipeline || '');
  function colorKey(r) {
    if (prefs.colorBy === 'salesperson') return r.salesperson || '';
    if (prefs.colorBy === 'pipeline') return pipeKey(r);
    return stageKey(r);
  }
  function defaultColor(mode, key) {
    if (mode === 'stage') return (state.stageById.get(Number(key)) || {}).color || NEUTRAL;
    if (mode === 'salesperson') return key ? PEOPLE_PALETTE[(state.peopleIndex.get(key) || 0) % PEOPLE_PALETTE.length] : NEUTRAL;
    const idx = state.pipeOrder.get(key);
    return idx === undefined ? NEUTRAL : PIPE_PALETTE[idx % PIPE_PALETTE.length];
  }
  function colorOf(key, mode = prefs.colorBy) {
    const c = (custom[mode] || {})[key];
    return HEX.test(c || '') ? c : defaultColor(mode, key);
  }
  function labelOf(key, mode = prefs.colorBy) {
    if (mode === 'salesperson') return key || 'Chưa giao';
    if (mode === 'pipeline') {
      const p = state.pipelines.find(x => String(x.id) === key);
      return p ? p.name : (key.startsWith('n:') ? key.slice(2) : key) || 'Không có pipeline';
    }
    const s = state.stageById.get(Number(key));
    if (!s) return key.startsWith('n:') ? key.slice(2) : key;
    return state.pipelines.length > 1 && !ui.pipeline.value ? s.pipeline + ' / ' + s.name : s.name;
  }
  function keyOrder(mode = prefs.colorBy) {
    if (mode === 'stage') return (a, b) => (state.stageOrder.get(Number(a)) ?? 999) - (state.stageOrder.get(Number(b)) ?? 999);
    if (mode === 'pipeline') return (a, b) => (state.pipeOrder.get(a) ?? 999) - (state.pipeOrder.get(b) ?? 999);
    return (a, b) => (a === '') - (b === '') || a.localeCompare(b, 'vi');
  }
  function countBy(rows, fn) {
    const out = {};
    for (const r of rows) { const k = fn(r); out[k] = (out[k] || 0) + 1; }
    return out;
  }
  function clusterLook(counts) {
    const keys = Object.keys(counts).sort(keyOrder());
    const total = keys.reduce((s, k) => s + counts[k], 0);
    if (keys.length === 1) { const c = colorOf(keys[0]); return {fill: c, ink: inkColor(c), single: true}; }
    let acc = 0;
    const parts = keys.map(k => {
      const from = acc / total * 360; acc += counts[k];
      return colorOf(k) + ' ' + from.toFixed(1) + 'deg ' + (acc / total * 360).toFixed(1) + 'deg';
    });
    return {fill: 'conic-gradient(' + parts.join(',') + ')', ink: '#18202F', single: false};
  }

  /* ------------------------------------------------------------------ bộ lọc */
  function optionList(select, values) {
    const old = select.value;
    while (select.options.length > 1) select.remove(1);
    [...new Set(values.filter(Boolean))].sort((a, b) => a.localeCompare(b, 'vi')).forEach((value) => {
      const option = document.createElement('option'); option.value = value; option.textContent = value;
      select.append(option);
    });
    select.value = [...select.options].some(o => o.value === old) ? old : '';
  }
  function idOptions(select, items) {
    const old = select.value;
    while (select.options.length > 1) select.remove(1);
    items.forEach(([value, label]) => {
      const option = document.createElement('option'); option.value = value; option.textContent = label;
      select.append(option);
    });
    select.value = [...select.options].some(o => o.value === old) ? old : '';
  }
  function populatePipelines() {
    const present = new Set(state.records.map(pipeKey));
    const items = state.pipelines.filter(p => present.has(String(p.id))).map(p => [String(p.id), p.name]);
    // Deal không có pipeline_id (chưa cài CRM-002): lọc theo tên
    [...new Set(state.records.filter(r => !r.pipeline_id && r.pipeline).map(r => r.pipeline))]
      .forEach(n => items.push(['n:' + n, n]));
    idOptions(ui.pipeline, items);
  }
  function populateStages() {
    const pipe = ui.pipeline.value;
    const present = new Set(state.records.map(stageKey));
    const multi = state.pipelines.length > 1 && !pipe;
    const items = state.stages
      .filter(s => present.has(String(s.id)) && (!pipe || String(s.pipeline_id) === pipe))
      .map(s => [String(s.id), multi ? s.pipeline + ' / ' + s.name : s.name]);
    [...new Set(state.records.filter(r => !r.stage_id && r.stage).map(r => r.stage))].forEach(n => items.push(['n:' + n, n]));
    idOptions(ui.stage, items);
  }
  function populateFilters() {
    const all = state.records;
    optionList(ui.expo, all.map(r => r.expo));
    populatePipelines();
    populateStages();
    populateEvents();
    optionList(ui.eventLocation, all.map(r => r.event_location));
    optionList(ui.province, all.map(r => r.province));
    optionList(ui.owner, all.map(r => r.salesperson));
    optionList(ui.tag, all.flatMap(r => Array.isArray(r.tags) ? r.tags : []));
    optionList(ui.provider, all.map(r => r.geo_provider));
    populateDistricts();
  }
  function populateEvents() {
    const expo = ui.expo.value;
    const rows = state.records.filter(r => !expo || r.expo === expo);
    const old = ui.event.value;
    const counts = new Map();
    rows.forEach(r => {
      const value = String(r.event || '').trim();
      if (value) counts.set(value, (counts.get(value) || 0) + 1);
    });
    while (ui.event.options.length > 1) ui.event.remove(1);
    if (ui.event.options.length) ui.event.options[0].textContent = 'Tất cả x_event (' + fmt(rows.filter(r => r.event).length) + ')';
    [...counts.entries()].sort((a, b) => a[0].localeCompare(b[0], 'vi')).forEach(([value, count]) => {
      const option = document.createElement('option');
      option.value = value; option.textContent = value + ' (' + fmt(count) + ')';
      ui.event.append(option);
    });
    ui.event.value = [...ui.event.options].some(o => o.value === old) ? old : '';
  }
  function populateDistricts() {
    const province = ui.province.value;
    optionList(ui.district, state.records.filter(r => !province || r.province === province).map(r => r.district));
  }
  function renderEventSuggestions() {
    const box = ui.suggestions;
    if (!box) return;
    const term = fold(ui.search.value);
    box.replaceChildren();
    if (!term) { box.hidden = true; return; }
    const expo = ui.expo.value;
    const values = [...new Set(state.records.filter(r => !expo || r.expo === expo).map(r => r.event).filter(Boolean))]
      .filter(v => fold(v).includes(term)).sort((a, b) => a.localeCompare(b, 'vi'));
    if (!values.length) { box.append(make('div', 'event-suggestion-empty', 'Không có x_event phù hợp')); box.hidden = false; return; }
    values.forEach(value => {
      const button = make('button', 'event-suggestion-item', value);
      button.type = 'button';
      button.addEventListener('click', () => { ui.search.value = value; box.hidden = true; applyFilters(); });
      box.append(button);
    });
    box.hidden = false;
  }

  /** Deal gốc đã có bản copy (CRM-002) trong dữ liệu → ẩn để 1 khách = 1 điểm. */
  function computeVisible() {
    if (prefs.showOrigin) { state.visible = state.records; state.hiddenOrigins = 0; return; }
    const ids = new Set(state.records.map(r => r.id));
    const copied = new Set(state.records.filter(r => r.origin_id && ids.has(r.origin_id)).map(r => r.origin_id));
    state.visible = state.records.filter(r => !copied.has(r.id));
    state.hiddenOrigins = copied.size;
  }

  function matches(r, skip) {
    const use = (k) => !skip || !skip.includes(k);
    if (use('pipeline') && ui.pipeline.value && pipeKey(r) !== ui.pipeline.value) return false;
    if (use('stage') && ui.stage.value && stageKey(r) !== ui.stage.value) return false;
    if (ui.expo.value && r.expo !== ui.expo.value) return false;
    if (ui.event.value && r.event !== ui.event.value) return false;
    if (ui.eventLocation.value && r.event_location !== ui.eventLocation.value) return false;
    if (use('prov') && ui.province.value && r.province !== ui.province.value) return false;
    if (use('prov') && ui.district.value && r.district !== ui.district.value) return false;
    if (ui.owner.value && r.salesperson !== ui.owner.value) return false;
    if (ui.tag.value && !(r.tags || []).includes(ui.tag.value)) return false;
    if (ui.provider.value && r.geo_provider !== ui.provider.value) return false;
    if (ui.geo.value && r.geo_status !== ui.geo.value) return false;
    const term = fold(ui.search.value);
    if (term && !fold(r.event).includes(term)) return false;
    if (use('geoq') && state.geoQuick === 'mapped' && !isMapped(r)) return false;
    if (use('geoq') && state.geoQuick === 'off' && isMapped(r)) return false;
    const text = fold(ui.searchText.value);
    if (text) {
      if (r._q === undefined) r._q = fold([r.company, r.name, r.contact, r.address, r.phone, r.mobile, r.email, '#' + (r.pid || r.id)].join(' '));
      for (const part of text.split(/\s+/)) if (!r._q.includes(part)) return false;
    }
    return true;
  }

  function applyFilters(fit) {
    state.filtered = state.visible.filter(r => matches(r));
    const visibleCount = $('visibleCount'); if (visibleCount) visibleCount.textContent = fmt(state.filtered.length) + ' bản ghi';
    state.rendered = 0;
    ui.list.replaceChildren();
    renderMore();
    renderSummary();
    renderStrip();
    renderGeoQuick();
    renderLegend();
    redrawMap(fit);
    const mapped = state.filtered.filter(isMapped).length;
    $('mapSummary').textContent = fmt(mapped) + ' có tọa độ / ' + fmt(state.filtered.length) + (prefs.mode === 'potential' ? ' Contact' : ' khách hàng') +
      (state.hiddenOrigins ? ' · ' + fmt(state.hiddenOrigins) + ' deal gốc đã copy đang ẩn' : '') +
      (prefs.mode === 'all' && status.borrowed ? ' · ' + fmt(status.borrowed) + ' Deal dùng tọa độ Contact' : '') +
      (prefs.mode === 'all' && status.contact_added ? ' · ' + fmt(status.contact_added) + ' Contact MM/Approved từ bản đồ cũ' : '');
  }

  /* Update 096: lọc nhanh Deal đã / chưa lên bản đồ (đếm theo các bộ lọc khác) */
  function renderGeoQuick() {
    const base = state.visible.filter(r => matches(r, ['geoq']));
    const mapped = base.filter(isMapped).length;
    const set = (id, n) => { const el = $(id); if (el) el.textContent = fmt(n); };
    set('geoAll', base.length); set('geoMapped', mapped); set('geoOff', base.length - mapped);
    document.querySelectorAll('[data-geo-quick]').forEach(b => {
      const on = b.dataset.geoQuick === state.geoQuick;
      b.classList.toggle('active', on); b.setAttribute('aria-pressed', String(on));
    });
  }
  document.querySelectorAll('[data-geo-quick]').forEach(b => b.addEventListener('click', () => { state.geoQuick = b.dataset.geoQuick; applyFilters(true); }));

  /* ------------------------------------------------------------------ dải chip pipeline → stage */
  function chip(label, count, color, active, onClick, title) {
    const b = make('button', 'strip-chip' + (active ? ' active' : ''));
    b.type = 'button';
    if (title) b.title = title;
    const head = make('span', 'strip-label');
    if (color) head.append(dot(color));
    head.append(make('span', '', label));
    b.append(head, make('strong', '', fmt(count)));
    b.addEventListener('click', onClick);
    return b;
  }
  function renderStrip() {
    ui.strip.replaceChildren();
    const pipe = ui.pipeline.value;
    const multiPipe = state.pipelines.length > 1 || [...ui.pipeline.options].length > 2;
    if (!pipe && multiPipe) {
      const base = state.visible.filter(r => matches(r, ['pipeline', 'stage']));
      const counts = countBy(base, pipeKey);
      ui.strip.append(chip('Tất cả pipeline', base.length, null, true, () => {}));
      [...ui.pipeline.options].slice(1).forEach(o => {
        ui.strip.append(chip(o.textContent, counts[o.value] || 0, prefs.colorBy === 'pipeline' ? colorOf(o.value, 'pipeline') : null, false, () => {
          ui.pipeline.value = o.value; ui.stage.value = ''; populateStages(); applyFilters(true);
        }, 'Bấm để xem từng stage của pipeline này'));
      });
      return;
    }
    const base = state.visible.filter(r => matches(r, ['stage']));
    const counts = countBy(base, stageKey);
    if (multiPipe) {
      const back = make('button', 'strip-back', '‹ Tất cả pipeline');
      back.type = 'button';
      back.addEventListener('click', () => { ui.pipeline.value = ''; ui.stage.value = ''; populateStages(); applyFilters(true); });
      ui.strip.append(back);
    }
    // Update 100: ô tổng số điểm (mọi stage) đứng đầu dải, bấm để bỏ lọc stage
    const total = chip('Tổng điểm', base.length, null, !ui.stage.value, () => { ui.stage.value = ''; applyFilters(false); }, 'Tổng số điểm theo bộ lọc hiện tại (mọi stage)');
    total.classList.add('strip-total');
    ui.strip.append(total);
    [...ui.stage.options].slice(1).forEach(o => {
      ui.strip.append(chip(o.textContent, counts[o.value] || 0, colorOf(o.value, 'stage'), ui.stage.value === o.value, () => {
        ui.stage.value = ui.stage.value === o.value ? '' : o.value; applyFilters(false);
      }, 'Bấm để lọc theo stage này'));
    });
  }

  function renderLegend() {
    const titles = {stage: 'Stage', salesperson: 'Salesperson', pipeline: 'Pipeline'};
    ui.legendTitle.textContent = titles[prefs.colorBy];
    ui.legendItems.replaceChildren();
    const counts = countBy(state.filtered, colorKey);
    const keys = Object.keys(counts).sort(keyOrder());
    keys.slice(0, 14).forEach(k => {
      const row = make('span', 'legend-row'); row.append(dot(colorOf(k)), make('span', '', labelOf(k))); ui.legendItems.append(row);
    });
    if (keys.length > 14) ui.legendItems.append(make('span', 'legend-more', '+' + (keys.length - 14)));
  }

  function renderSummary() {
    const groups = new Map();
    const rows = state.visible.filter(r => matches(r, ['prov']));
    for (const r of rows) {
      const key = r.province || '';
      const g = groups.get(key) || {total: 0, mapped: 0};
      g.total++; if (isMapped(r)) g.mapped++; groups.set(key, g);
    }
    const body = $('summaryRows'); body.replaceChildren();
    [...groups].sort((a, b) => (a[0] === '') - (b[0] === '') || b[1].total - a[1].total).forEach(([name, g]) => {
      const tr = make('tr', name && ui.province.value === name ? 'active' : (name ? '' : 'muted'));
      tr.append(make('td', '', name || 'Chưa có tỉnh/thành'), make('td', '', fmt(g.total)), make('td', '', fmt(g.mapped)));
      if (name) {
        tr.title = 'Bấm để lọc theo tỉnh/thành này';
        tr.addEventListener('click', () => {
          ui.province.value = ui.province.value === name ? '' : name;
          populateDistricts(); applyFilters(true);
        });
      }
      body.append(tr);
    });
  }

  /* ------------------------------------------------------------------ danh sách */
  function renderMore() {
    const part = state.filtered.slice(state.rendered, state.rendered + state.pageSize);
    state.rendered += part.length;
    part.forEach(r => {
      const card = make('button', 'record-card' + (r.id === state.selectedId ? ' selected' : ''));
      card.type = 'button';
      card.dataset.id = r.id;
      card.style.setProperty('--c', colorOf(colorKey(r)));
      card.append(make('strong', '', recordTitle(r)));
      card.append(make('div', 'address', r.address || ''));
      const meta = make('div', 'record-meta');
      if (r.stage) { const c = make('span', 'chip chip-stage'); c.append(dot(colorOf(stageKey(r), 'stage')), make('span', '', r.stage)); meta.append(c); }
      meta.append(make('span', 'geo-indicator' + (isMapped(r) ? '' : ' off'), isMapped(r) ? '● Map' : '○ Pending'));
      if (r.geo_approx && isMapped(r)) meta.append(make('span', 'chip chip-approx', '≈ ' + r.geo_provider));
      if (r.salesperson) meta.append(make('span', 'chip', r.salesperson));
      if (r.province) meta.append(make('span', 'chip', r.province));
      card.append(meta);
      card.addEventListener('click', () => selectRecord(r, true));
      ui.list.append(card);
    });
    ui.more.hidden = state.rendered >= state.filtered.length;
    if (!state.filtered.length) ui.list.append(make('div', 'empty-list', 'Không có bản ghi phù hợp bộ lọc.'));
  }

  function selectRecord(r, fly) {
    const prev = state.selectedId;
    state.selectedId = r.id;
    for (const id of [prev, r.id]) {
      const m = state.markers.get(id);
      if (m) m.setIcon(pointIcon(m.gRec, id === r.id));
    }
    ui.list.querySelectorAll('.record-card.selected').forEach(el => el.classList.remove('selected'));
    const idx = state.filtered.findIndex(x => x.id === r.id);
    while (idx >= state.rendered && state.rendered < state.filtered.length) renderMore();
    const card = ui.list.querySelector('.record-card[data-id="' + r.id + '"]');
    if (card) { card.classList.add('selected'); if (!fly) card.scrollIntoView({block: 'nearest'}); }
    if (!fly) return;
    const marker = state.markers.get(r.id);
    if (marker && state.mapReady && state.showPoints && state.map.hasLayer(pointLayer)) {
      pointLayer.zoomToShowLayer(marker, () => marker.openPopup());
    } else if (state.mapReady && isMapped(r)) {
      state.map.flyTo([r.lat, r.lng], Math.max(15, state.map.getZoom()));
    } else {
      openRecord(r);
    }
  }

  /* ------------------------------------------------------------------ Update 097: hộp chi tiết = mẫu của bản đồ cũ (XINYANG HEAT MAP) */
  let profileSeq = 0;
  const tr = t => (window.XINYANG_I18N && window.XINYANG_I18N.t ? window.XINYANG_I18N.t(t) : t);
  function dField(root, label, value, link) {
    const r = make('div', 'xy092-field');
    r.append(make('span', 'xy092-key', label));
    const isLink = link && /^https?:\/\//i.test(String(value || ''));
    const v = isLink ? make('a', 'xy092-value', value) : make('span', 'xy092-value', value === undefined || value === null || value === '' ? '—' : value);
    if (isLink) { v.href = value; v.target = '_blank'; v.rel = 'noopener noreferrer'; }
    r.append(v); root.append(r);
  }
  function dSection(parent, title) { const box = make('section', 'xy092-section'); box.append(make('h4', '', title)); parent.append(box); return box; }
  function dStage(box, deals) {
    box.replaceChildren();
    if (!deals.length) { box.append(make('div', 'xy092-stage-empty', 'Chưa có Deal CRM liên kết được xác minh.')); return; }
    const select = make('select', 'xy092-deal-picker'); select.setAttribute('aria-label', 'Chọn Deal cần xem');
    deals.forEach((deal, i) => select.append(new Option(deal.name || ('Deal #' + deal.id), String(i))));
    const value = make('div', 'xy092-stage-value');
    const render = () => { const d = deals[Number(select.value) || 0]; value.textContent = (d && d.stage) || 'Chưa xác minh'; };
    if (deals.length > 1) { box.append(make('p', 'xy092-deal-note', 'Công ty có nhiều Deal. Chọn Deal để xem đúng Stage hiện tại.'), select); select.addEventListener('change', render); }
    box.append(value); render();
  }
  function renderContactProfile(body, r, data) {
    body.replaceChildren();
    const top = make('div', 'xy092-company-head');
    const logo = make('div', 'xy092-logo');
    if (data.logo) { const img = make('img'); img.alt = 'Logo công ty'; img.src = data.logo; logo.append(img); } else logo.append(make('span', '', '▦'));
    top.append(logo, make('div', 'xy092-company-name', data.name || recordTitle(r))); body.append(top);
    const contact = dSection(body, 'Thông tin liên hệ');
    dField(contact, 'Loại', data.is_company === 'True' ? 'Company' : data.is_company === 'False' ? 'Person' : 'Company');
    dField(contact, 'Điện thoại', data.phone_any || data.phone || data.mobile);
    dField(contact, 'Email', data.email); dField(contact, 'Website', data.website, true);
    if (data.contact_person) dField(contact, 'Người liên hệ', data.contact_person);
    const legal = dSection(body, 'Hồ sơ doanh nghiệp');
    dField(legal, 'Mã số thuế', data.vat); dField(legal, 'Năm thành lập', data.founded_year);
    dField(legal, 'Business Type', data.business_type); dField(legal, 'Main Market', data.main_market);
    dField(legal, 'Employee Size', data.employee_size); dField(legal, 'Business Industries', data.business_industries);
    dField(legal, 'Yellow Pages', data.yellow_pages, true);
    const address = dSection(body, 'Địa chỉ & tọa độ');
    ['street', 'street2', 'city', 'state_id', 'country_id', 'zip'].forEach((f, i) => dField(address, ['Street', 'Street 2', 'City', 'State', 'Country', 'ZIP'][i], data[f]));
    const lat = Number(data.partner_latitude), lon = Number(data.partner_longitude);
    if (Number.isFinite(lat) && Number.isFinite(lon) && lat && lon) {
      dField(address, 'Latitude', String(data.partner_latitude)); dField(address, 'Longitude', String(data.partner_longitude));
      if (isMapped(r)) {
        const dist = Math.hypot((lat - r.lat) * 111195, (lon - r.lng) * 111195 * Math.cos(lat * Math.PI / 180));
        if (dist > 25) address.append(make('p', 'xy092-coord-warning', 'Lưu ý: Điểm trên bản đồ khác tọa độ Contact ' + Math.round(dist) + ' m. Cần đối chiếu địa chỉ trước khi xác nhận.'));
      }
    }
    address.append(make('p', 'xy092-coord-note', 'Tọa độ lấy từ Contact Odoo. Chưa xác minh độ chính xác tại số nhà; không tự động ghi đè tọa độ.'));
    const stage = dSection(body, 'Trạng thái Deal hiện tại');
    const stageBox = make('div', 'xy092-deal-stage'); stage.append(stageBox);
    dStage(stageBox, data.deals || []);
    if (data.deals_truncated) stage.append(make('p', 'xy092-coord-warning', 'Danh sách hơn 100 Deal; mở Odoo để xem đầy đủ.'));
    const gaps = data.gap_sources || {}, gk = Object.keys(gaps);
    if (gk.length) body.append(make('p', 'xy092-coord-note', tr('Một số ô trống ở Contact công ty nên được bù từ: ') + [...new Set(gk.map(k => tr(gaps[k])))].join(', ') + tr(' (chỉ đọc, không ghi lại Odoo).')));
    body.append(make('p', 'xy092-source', 'Nguồn: Contact + CRM Odoo XINYANG · dữ liệu đọc trực tiếp khi mở chi tiết'));
  }
  async function fetchProfile(id) {
    const response = await fetch(url('/sgt_home/map/profile/' + encodeURIComponent(id)), {credentials: 'same-origin', headers: {Accept: 'application/json'}, cache: 'no-store'});
    if (!response.ok) { let msg = 'HTTP ' + response.status; try { msg = (await response.json()).detail || msg; } catch (_) { /* giữ HTTP */ } throw Error(msg); }
    return response.json();
  }
  function openRecord(r) {
    const dialog = $('recordDialog'), body = $('detailContent'), foot = $('detailFoot');
    const seq = ++profileSeq;
    const isContact = r.kind === 'partner';
    $('detailTitle').textContent = recordTitle(r);
    body.replaceChildren(make('p', 'xy092-loading', isContact ? 'Đang lấy hồ sơ Contact từ Odoo XINYANG…' : 'Đang mở thông tin Deal CRM…'));
    foot.replaceChildren();
    const odoo = odooLink(r, 'xy050-dlg-odoo');
    if (odoo) { odoo.textContent = isContact ? 'Mở Contact trên Odoo ↗' : 'Mở Deal trên Odoo ↗'; foot.append(odoo); }
    if (isMapped(r)) {
      const loc = make('button', 'xy050-dlg-btn', 'Định vị trên bản đồ'); loc.type = 'button';
      loc.addEventListener('click', () => { dialog.close(); selectRecord(r, true); });
      foot.append(loc);
    }
    const end = make('button', 'xy050-dlg-btn primary', 'Đóng'); end.type = 'button'; end.addEventListener('click', () => dialog.close());
    foot.append(end);
    if (typeof dialog.showModal === 'function') { if (!dialog.open) dialog.showModal(); } else dialog.setAttribute('open', '');
    const alive = () => seq === profileSeq && dialog.open;
    if (isContact) {
      fetchProfile(r.pid || r.id).then(profile => { if (alive()) renderContactProfile(body, r, profile); })
        .catch(e => { if (alive()) body.replaceChildren(make('p', 'xy092-error', 'Không tải được Contact: ' + e.message)); });
      return;
    }
    body.replaceChildren();
    // Update 101: logo công ty của Deal (x_yp_logo_upload → x_image); không có thì dùng logo Contact liên kết
    const head = make('div', 'xy092-company-head');
    const logoBox = make('div', 'xy092-logo'); logoBox.append(make('span', '', '▦'));
    head.append(logoBox, make('div', 'xy092-company-name', r.company || recordTitle(r)));
    body.append(head);
    const setLogo = (uri) => {
      if (!uri || logoBox.dataset.has) return;
      const img = make('img'); img.alt = 'Logo công ty'; img.src = uri;
      logoBox.replaceChildren(img); logoBox.dataset.has = '1';
    };
    fetch(url('/sgt_home/map/lead-logo/' + encodeURIComponent(r.id)), {credentials: 'same-origin', headers: {Accept: 'application/json'}, cache: 'no-store'})
      .then(res => res.ok ? res.json() : null).then(d => { if (alive() && d) setLogo(d.logo); }).catch(() => { /* logo là phụ */ });
    const info = dSection(body, 'Thông tin Deal CRM');
    dField(info, 'Tên Deal', r.name); dField(info, 'Công ty / Contact', r.company || 'Chưa liên kết Contact');
    dField(info, 'Điện thoại', r.phone || r.mobile); dField(info, 'Email', r.email);
    const state = dSection(body, 'Trạng thái Deal hiện tại');
    state.append(make('div', 'xy092-stage-value', [r.pipeline, r.stage].filter(Boolean).join(' / ') || 'Chưa xác định'));
    const location = dSection(body, 'Tọa độ của Deal');
    dField(location, 'Latitude', r.lat === null ? 'Chưa có' : String(r.lat)); dField(location, 'Longitude', r.lng === null ? 'Chưa có' : String(r.lng));
    dField(location, 'Trạng thái định vị', r.geo_status_raw || (isMapped(r) ? 'Có tọa độ' : 'Chưa có trạng thái'));
    dField(location, 'Độ chính xác / nguồn tọa độ', r.geo_provider);
    dField(location, 'Cập nhật', r.geo_updated_at);
    body.append(make('p', 'xy092-source', r.geo_provider === 'Contact' ? 'Nguồn: tọa độ lấy từ Contact (partner_latitude / partner_longitude) vì Deal chưa có tọa độ' : 'Nguồn: crm.lead · x_yp_latitude / x_yp_longitude · không định vị lại địa chỉ'));
    if (r.partner_id) {
      const extra = dSection(body, 'Hồ sơ Contact liên kết');
      extra.append(make('p', 'xy092-loading', 'Đang tải thông tin Contact…'));
      fetchProfile(r.partner_id).then(profile => {
        if (!alive()) return;
        extra.replaceChildren(make('h4', '', 'Hồ sơ Contact liên kết'));
        setLogo(profile.logo);
        dField(extra, 'Tên doanh nghiệp', profile.name); dField(extra, 'Mã số thuế', profile.vat);
        dField(extra, 'Điện thoại', profile.phone_any || profile.phone || profile.mobile); dField(extra, 'Email', profile.email);
        dField(extra, 'Business Type', profile.business_type); dField(extra, 'Main Market', profile.main_market);
        dField(extra, 'Employee Size', profile.employee_size); dField(extra, 'Business Industries', profile.business_industries);
        dField(extra, 'Địa chỉ', [profile.street, profile.city, profile.country_id].filter(Boolean).join(', '));
      }).catch(e => { if (alive()) extra.replaceChildren(make('p', 'xy092-coord-warning', e.message)); });
    }
  }
  $('detailClose').addEventListener('click', () => $('recordDialog').close());
  function odooLink(r, cls) {
    if (!state.config.odoo_url) return null;
    const link = make('a', cls || 'odoo-link', r.kind === 'partner' ? 'Mở Contact trong Xinyang Odoo ↗' : 'Mở Deal trong Xinyang Odoo ↗');
    link.href = state.config.odoo_url + (r.kind === 'partner' ? '/odoo/action-base.action_partner_form/' : '/odoo/action-crm.crm_lead_action_pipeline/') + encodeURIComponent(r.kind === 'partner' ? (r.pid || r.id) : r.id);
    link.target = '_blank'; link.rel = 'noopener';
    return link;
  }

  /* ------------------------------------------------------------------ bản đồ */
  let pointLayer, heatLayer, baseLayer, baseGl, baseTimer;
  let redrawVersion = 0, baseVersion = 0;
  let syncBusy = false;
  const heatGradient = {0.15: '#ef8d82', 0.35: '#dd4439', 0.55: '#c11718', 0.75: '#950b0e', 1: '#530005'};
  const iconCache = new Map();
  function coordinate(value) {
    return value === null || value === undefined || typeof value === 'boolean' || String(value).trim() === '' ? null : Number(value);
  }
  function pointIcon(r, selected) {
    const color = colorOf(colorKey(r));
    const key = color + (selected ? '|s' : '');
    let icon = iconCache.get(key);
    if (!icon) {
      icon = L.divIcon({className: 'gm-icon', html: '<span class="gm-pin gm-solo' + (selected ? ' gm-sel' : '') + '" style="--fill:' + color + '"></span>',
        iconSize: [13, 13], iconAnchor: [6.5, 6.5], popupAnchor: [0, -6]});
      iconCache.set(key, icon);
    }
    return icon;
  }
  function clusterIcon(cluster) {
    const kids = cluster.getAllChildMarkers();
    const look = clusterLook(countBy(kids, m => colorKey(m.gRec)));
    const n = kids.length;
    const size = n >= 1000 ? 54 : n >= 100 ? 48 : n >= 10 ? 40 : 34;
    return L.divIcon({
      html: '<span class="gm-pin gm-cluster' + (look.single ? ' gm-one' : '') + '" style="--fill:' + look.fill + ';--ink:' + look.ink + '"><b>' + fmt(n) + '</b></span>',
      className: 'gm-icon', iconSize: [size, size], iconAnchor: [size / 2, size / 2],
    });
  }
  function popupFor(r) {
    const root = make('div', 'gm-pp');
    root.append(make('div', 'popup-name', recordTitle(r)));
    const chips = make('div', 'gm-pp-chips');
    if (r.stage) { const c = make('span', 'chip chip-stage'); c.append(dot(colorOf(stageKey(r), 'stage')), make('span', '', r.stage)); chips.append(c); }
    if (r.salesperson) chips.append(make('span', 'chip', r.salesperson));
    if (r.pipeline) chips.append(make('span', 'chip', r.pipeline));
    if (r.geo_approx && isMapped(r)) chips.append(make('span', 'chip chip-approx', '≈ ' + r.geo_provider));
    root.append(chips);
    root.append(make('div', 'popup-address', r.address));
    const actions = make('div', 'gm-pp-actions');
    const btn = make('button', 'popup-detail', 'Xem chi tiết'); btn.type = 'button';
    btn.addEventListener('click', () => openRecord(r)); actions.append(btn);
    const link = odooLink(r, 'popup-detail popup-link'); if (link) actions.append(link);
    root.append(actions);
    return root;
  }
  function openClusterPopup(cluster) {
    const recs = cluster.getAllChildMarkers().map(m => m.gRec)
      .sort((a, b) => (state.stageOrder.get(b.stage_id) ?? -1) - (state.stageOrder.get(a.stage_id) ?? -1) || recordTitle(a).localeCompare(recordTitle(b), 'vi'));
    const n = recs.length;
    const counts = countBy(recs, colorKey);
    const root = make('div', 'gm-pp');
    root.append(make('div', 'popup-name', fmt(n) + (prefs.mode === 'potential' ? ' Contact tại khu vực này' : ' deal tại khu vực này')));
    const areas = [...new Set(recs.map(r => [r.district, r.province].filter(Boolean).join(', ')).filter(Boolean))];
    if (areas.length) root.append(make('div', 'popup-address', areas.slice(0, 3).join(' · ') + (areas.length > 3 ? ' …' : '')));
    const bar = make('div', 'gm-pp-bar');
    Object.keys(counts).sort(keyOrder()).forEach(k => {
      const part = make('span'); part.style.flex = String(counts[k]); part.style.background = colorOf(k);
      part.title = labelOf(k) + ': ' + counts[k]; bar.append(part);
    });
    root.append(bar);
    const list = make('div', 'gm-pp-list');
    const more = make('button', 'gm-pp-more'); more.type = 'button';
    let shown = 0;
    const appendNext = () => {
      const upper = Math.min(shown + CLUSTER_LIST_PAGE, n);
      for (; shown < upper; shown++) {
        const r = recs[shown];
        const item = make('button', 'gm-pp-item'); item.type = 'button';
        item.style.setProperty('--c', colorOf(colorKey(r)));
        item.append(make('span', '', recordTitle(r)), make('small', '', [r.stage, r.salesperson].filter(Boolean).join(' · ')));
        item.addEventListener('click', () => { state.map.closePopup(); selectRecord(r, true); });
        list.append(item);
      }
      if (shown < n) more.textContent = 'Xem thêm (' + fmt(n - shown) + ')'; else more.remove();
    };
    more.addEventListener('click', appendNext);
    appendNext();
    root.append(list);
    if (shown < n) root.append(more);
    const zoom = make('button', 'popup-detail gm-pp-zoom', 'Phóng to / tách điểm'); zoom.type = 'button';
    zoom.addEventListener('click', () => {
      state.map.closePopup();
      if (state.map.getZoom() >= state.map.getMaxZoom() - 1 || cluster.getBounds().getNorthEast().equals(cluster.getBounds().getSouthWest())) cluster.spiderfy();
      else cluster.zoomToBounds({padding: [40, 40]});
    });
    root.append(zoom);
    L.popup({maxWidth: 360, minWidth: 270, ...POPUP_PAN}).setLatLng(cluster.getLatLng()).setContent(root).openOn(state.map);
  }
  function makePointLayer() {
    if (pointLayer && state.map.hasLayer(pointLayer)) state.map.removeLayer(pointLayer);
    pointLayer = L.markerClusterGroup({
      maxClusterRadius: Number(prefs.clusterRadius) || 46, showCoverageOnHover: false,
      zoomToBoundsOnClick: false, spiderfyOnMaxZoom: true, animate: false, removeOutsideVisibleBounds: true,
      iconCreateFunction: clusterIcon,
    });
    pointLayer.on('clusterclick', (e) => openClusterPopup(e.layer));
  }
  function redrawMap(fit) {
    if (!state.mapReady) return;
    const version = ++redrawVersion;
    pointLayer.clearLayers();
    state.markers.clear();
    const rows = state.filtered.filter(isMapped);
    heatLayer.setLatLngs(rows.map(r => [r.lat, r.lng, 1]));
    // Thêm theo lô; bộ lọc mới huỷ lô cũ chưa xong.
    let cursor = 0;
    function addBatch() {
      if (version !== redrawVersion) return;
      const batch = rows.slice(cursor, cursor + 500).map(r => {
        const m = L.marker([r.lat, r.lng], {icon: pointIcon(r, r.id === state.selectedId), title: recordTitle(r), keyboard: true});
        m.gRec = r;
        m.bindPopup(() => popupFor(r), {maxWidth: 320, ...POPUP_PAN});
        m.on('click', () => selectRecord(r, false));
        state.markers.set(r.id, m);
        return m;
      });
      pointLayer.addLayers(batch); cursor += batch.length;
      if (cursor < rows.length) setTimeout(addBatch, 0);
    }
    addBatch();
    updateLayerVisibility();
    if (fit) fitMap();
  }
  function showOverlay(title, description) {
    ui.mapEmpty.hidden = false; ui.emptyTitle.textContent = title; ui.emptyDescription.textContent = description;
  }
  function updateMapEmpty() {
    if (!state.mapReady) return;
    if (!state.showPoints && !state.showHeat) showOverlay('Đã tắt các lớp dữ liệu', 'Bật Điểm hoặc Mật độ để xem khách hàng.');
    else if (!state.records.length) showOverlay(prefs.mode === 'potential' ? 'Chưa có Contact tiềm năng' : 'Chưa có deal có địa chỉ', prefs.mode === 'potential' ? 'Chưa có Contact có tọa độ nào có Deal ở 5.Match Making hoặc 6.Approved Match Making.' : 'Xinyang Odoo chưa có Deal nào có địa chỉ hoặc tọa độ.');
    else if (!state.filtered.some(isMapped)) showOverlay('Chưa có điểm GPS cho bộ lọc', fmt(state.filtered.length) + ' khách hàng phù hợp nhưng chưa có tọa độ. Tọa độ lấy từ x_yp_latitude / x_yp_longitude của Deal.');
    else ui.mapEmpty.hidden = true;
  }
  function updateLayerVisibility() {
    if (!state.mapReady) return;
    for (const [layer, show] of [[pointLayer, state.showPoints], [heatLayer, state.showHeat]]) {
      if (show && !state.map.hasLayer(layer)) state.map.addLayer(layer);
      if (!show && state.map.hasLayer(layer)) state.map.removeLayer(layer);
    }
    for (const [id, on] of [['btnPoints', state.showPoints], ['btnHeat', state.showHeat]]) {
      $(id).classList.toggle('active', on); $(id).setAttribute('aria-pressed', String(on));
    }
    $('heatSettings').hidden = !state.showHeat;
    $('heatLegend').hidden = !state.showHeat;
    updateMapEmpty();
  }
  function updateHeatOptions() {
    if (!heatLayer) return;
    const radius = Number($('heatRadius').value), intensity = Number($('heatIntensity').value);
    $('heatRadiusValue').textContent = radius + ' px';
    $('heatIntensityValue').textContent = intensity.toFixed(1) + '×';
    heatLayer.setOptions({radius: radius, blur: Math.round(radius * 0.65), max: 1 / intensity});
  }
  // Nền raster theo thứ tự dự phòng: mạng nào chặn nguồn nào thì tự chuyển nguồn kế tiếp.
  const RASTER = {
    esriStreet: {url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}', opt: {maxNativeZoom: 19, attribution: 'Tiles © Esri'}},
    esriGray: {url: 'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}', opt: {maxNativeZoom: 16, attribution: 'Tiles © Esri'}},
    osmHot: {url: 'https://{s}.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png', opt: {subdomains: 'abc', maxNativeZoom: 19, attribution: '© OpenStreetMap contributors, HOT'}},
    osm: {url: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png', opt: {maxNativeZoom: 19, attribution: '© OpenStreetMap contributors'}},
  };
  // Nền nhạt = nền màu có đủ tên địa danh, làm xám bằng CSS để màu stage nổi bật.
  const RASTER_CHAIN = {light: ['esriStreet', 'osmHot', 'esriGray', 'osm'], color: ['esriStreet', 'osmHot', 'osm'], osm: ['osm', 'osmHot', 'esriStreet']};
  function setBaseMap() {
    const map = state.map, version = ++baseVersion, choice = $('baseMap').value;
    clearTimeout(baseTimer);
    if (baseLayer) { map.removeLayer(baseLayer); baseLayer = null; baseGl = null; }
    $('baseNotice').textContent = '';
    const chain = RASTER_CHAIN[choice] || RASTER_CHAIN.light;
    const useRaster = (index) => {
      if (version !== baseVersion) return;
      clearTimeout(baseTimer);
      if (baseLayer) { map.removeLayer(baseLayer); baseLayer = null; baseGl = null; }
      if (index >= chain.length) { $('baseNotice').textContent = 'Mạng hiện tại chặn các nguồn nền bản đồ. Điểm và bộ lọc vẫn sử dụng được.'; return; }
      const key = chain[index], src = RASTER[key];
      map.getPane('basemap').classList.toggle('base-muted', choice === 'light' && key !== 'esriGray');
      const layer = L.tileLayer(src.url, {pane: 'basemap', maxZoom: 22, ...src.opt}).addTo(map);
      baseLayer = layer;
      let loaded = 0, failed = 0;
      const next = () => { if (version === baseVersion && baseLayer === layer && !loaded) useRaster(index + 1); };
      layer.on('tileload', () => { loaded++; clearTimeout(baseTimer); });
      layer.on('tileerror', () => { failed++; if (!loaded && failed >= 3) next(); });
      baseTimer = setTimeout(next, 8000);
    };
    if (choice === 'osm' || !state.config.maptiles_key || !L.maplibreGL) { useRaster(0); return; }
    map.getPane('basemap').classList.toggle('base-muted', choice === 'light');
    try {
      baseLayer = L.maplibreGL({pane: 'basemap', interactive: false,
        style: 'https://tiles.goong.io/assets/goong_map_web.json?api_key=' + encodeURIComponent(state.config.maptiles_key),
        attribution: '© Goong'}).addTo(map);
      baseGl = baseLayer.getMaplibreMap();
      let loaded = false;
      baseGl.on('load', () => { loaded = true; clearTimeout(baseTimer); });
      baseGl.on('error', () => { if (!loaded) useRaster(0); });
      baseTimer = setTimeout(() => { if (!loaded) useRaster(0); }, 15000);
    } catch (_) { useRaster(0); }
  }
  function initMap() {
    if (!window.L || !L.markerClusterGroup || !L.heatLayer) {
      showOverlay('Không tải được thư viện bản đồ', 'Tải lại trang hoặc kiểm tra các file static/vendor trong gói triển khai.'); return;
    }
    const map = L.map('map', {center: [16.7, 106.1], zoom: 5, minZoom: 2, maxZoom: 22, preferCanvas: true});
    state.map = map;
    map.createPane('basemap'); map.getPane('basemap').style.zIndex = 200;
    L.control.scale({imperial: false, position: 'bottomleft'}).addTo(map);
    makePointLayer();
    heatLayer = L.heatLayer([], {radius: 30, blur: 20, maxZoom: 12, max: 0.55, minOpacity: 0.32, gradient: heatGradient});
    // Leaflet.heat 0.2: không redraw khi đã tách khỏi bản đồ.
    const heatRedraw = heatLayer.redraw;
    heatLayer.redraw = function () { return this._map ? heatRedraw.call(this) : this; };
    heatLayer.on('remove', () => { L.Util.cancelAnimFrame(heatLayer._frame); heatLayer._frame = null; });
    state.mapReady = true;
    setBaseMap();
    redrawMap(true); updateHeatOptions();
    const resize = () => map.invalidateSize({pan: false});
    window.addEventListener('resize', resize);
    new ResizeObserver(resize).observe($('map'));
    $('baseMap').addEventListener('change', setBaseMap);
    $('heatRadius').addEventListener('input', updateHeatOptions);
    $('heatIntensity').addEventListener('input', updateHeatOptions);
  }
  function fitMap() {
    if (!state.mapReady) return;
    const rows = state.filtered.filter(isMapped);
    if (rows.length) state.map.fitBounds(rows.map(r => [r.lat, r.lng]), {padding: [45, 45], maxZoom: 13, animate: false});
  }

  /* ------------------------------------------------------------------ tuỳ chọn màu */
  function savePrefs() { writeStore(PREFS_KEY, prefs); }
  function syncColorButtons() {
    document.querySelectorAll('[data-color-by]').forEach(b => {
      const on = b.dataset.colorBy === prefs.colorBy;
      b.classList.toggle('active', on); b.setAttribute('aria-pressed', String(on));
    });
  }
  function recolor() {
    iconCache.clear();
    applyFilters(false);
  }
  function colorRowsKeys() {
    if (prefs.colorBy === 'stage') {
      return [...ui.stage.options].slice(1).map(o => [o.value, o.textContent]);
    }
    const keys = Object.keys(countBy(state.visible, colorKey)).sort(keyOrder());
    return keys.map(k => [k, labelOf(k)]);
  }
  let colorDraft = {};
  function openColors() {
    const mode = prefs.colorBy;
    const titles = {stage: 'Màu theo stage', salesperson: 'Màu theo Salesperson', pipeline: 'Màu theo pipeline'};
    const helps = {
      stage: 'Mặc định đi từ lạnh đến nóng theo thứ tự stage trong pipeline: xám (mới) → xanh → cam → đỏ; stage Won màu xanh lá. Lưu theo ID stage nên đổi tên stage không mất màu.',
      salesperson: 'Dùng khi muốn xem khu vực của từng người phụ trách.',
      pipeline: 'Dùng khi muốn so sánh vùng khách giữa các kho / pipeline.',
    };
    $('colorTitle').textContent = titles[mode];
    $('colorHelp').replaceChildren(make('span', '', helps[mode]), document.createTextNode(' '), make('span', '', 'Màu lưu trên trình duyệt này.'));
    colorDraft = {};
    const box = $('colorRows'); box.replaceChildren();
    colorRowsKeys().forEach(([key, label]) => {
      const color = colorOf(key, mode);
      colorDraft[key] = color;
      const row = make('div', 'color-row');
      const pv = make('span', 'color-preview', '5'); pv.style.background = color; pv.style.color = inkColor(color);
      const input = make('input'); input.type = 'color'; input.value = color.toLowerCase(); input.setAttribute('aria-label', label);
      const code = make('code', '', color.toUpperCase());
      input.addEventListener('input', () => {
        const v = input.value.toUpperCase(); colorDraft[key] = v;
        pv.style.background = v; pv.style.color = inkColor(v); code.textContent = v;
      });
      row.append(make('span', 'color-label', label), pv, input, code);
      box.append(row);
    });
    if (!box.children.length) box.append(make('div', 'empty-list', 'Chưa có dữ liệu'));
    $('colorDialog').showModal();
  }
  $('openColors').addEventListener('click', openColors);
  $('colorCancel').addEventListener('click', () => $('colorDialog').close());
  $('colorSave').addEventListener('click', () => {
    const mode = prefs.colorBy;
    custom[mode] = custom[mode] || {};
    for (const [k, v] of Object.entries(colorDraft)) {
      if (HEX.test(v) && v.toUpperCase() !== defaultColor(mode, k).toUpperCase()) custom[mode][k] = v.toUpperCase();
      else delete custom[mode][k];
    }
    writeStore(COLORS_KEY, custom);
    $('colorDialog').close();
    recolor();
  });
  $('colorDefault').addEventListener('click', () => {
    custom[prefs.colorBy] = {};
    writeStore(COLORS_KEY, custom);
    $('colorDialog').close();
    recolor();
  });
  document.querySelectorAll('[data-color-by]').forEach(b => b.addEventListener('click', () => {
    prefs.colorBy = b.dataset.colorBy; savePrefs(); syncColorButtons(); recolor();
  }));
  $('showOrigin').checked = Boolean(prefs.showOrigin);
  $('showOrigin').addEventListener('change', (e) => { prefs.showOrigin = e.target.checked; savePrefs(); computeVisible(); applyFilters(false); });
  $('clusterRadius').value = String(prefs.clusterRadius);
  $('clusterRadiusValue').textContent = prefs.clusterRadius + ' px';
  $('clusterRadius').addEventListener('input', (e) => { $('clusterRadiusValue').textContent = e.target.value + ' px'; });
  $('clusterRadius').addEventListener('change', (e) => {
    prefs.clusterRadius = Number(e.target.value) || 46; savePrefs();
    if (state.mapReady) { makePointLayer(); redrawMap(false); }
  });
  syncColorButtons();

  /* ------------------------------------------------------------------ dữ liệu */
  function renderStatus(status) {
    state.status = status || {};
    const type = status.state || (Number(status.total || 0) > 0 ? 'ok' : 'empty_cache');
    const descriptions = {
      ok: 'Đọc trực tiếp Xinyang Odoo bằng tài khoản đang đăng nhập · cache ' + Math.round((status.cache_seconds || 300) / 60) + ' phút',
      empty_cache: 'Chưa có Deal nào có địa chỉ',
      syncing: 'Đang đồng bộ thủ công từ Xinyang Odoo',
      waiting_for_odoo_settings: 'Chưa cấu hình tài khoản Xinyang Odoo',
      odoo_error: 'Lỗi đọc Xinyang Odoo · ' + (status.last_error || 'Kiểm tra quyền/fields') +
        (String(status.last_error || '').startsWith('odoo_missing_fields') ? ' · cần cập nhật CRM-005 (Update 047)' : ''),
    };
    if (prefs.mode === 'potential' && type === 'ok') {
      descriptions.ok = 'Potential Map · Match Making ' + fmt(status.mm_contacts) + ' · Approved ' + fmt(status.approved_contacts) + ' · cả hai ' + fmt(status.both_contacts) +
        ' · ' + fmt(status.matched_deals) + ' deal · cùng dữ liệu bản đồ cũ · cache ' + Math.round((status.cache_seconds || 360) / 60) + ' phút';
      descriptions.empty_cache = 'Chưa có Contact nào có Deal ở Match Making / Approved Match Making';
    }
    if (prefs.mode === 'all' && status.contact_error) descriptions.ok += ' · Không đọc được Contact MM/Approved';
    if (prefs.mode === 'all' && status.contact_geo_error) descriptions.ok += ' · Không đọc được tọa độ Contact của Deal';
    if (ui.syncStatus) ui.syncStatus.textContent = descriptions[type] || type;
    const mapSync = $('mapSyncTime');
    if (mapSync) mapSync.textContent = status.last_sync ? 'Đọc lúc ' + new Date(status.last_sync).toLocaleString(window.XINYANG_I18N ? window.XINYANG_I18N.locale() : 'vi-VN') : '';
  }
  function setMeta(payload) {
    state.stages = Array.isArray(payload.stages) ? payload.stages : [];
    state.pipelines = Array.isArray(payload.pipelines) ? payload.pipelines : [];
    state.stageById = new Map(state.stages.map(s => [s.id, s]));
    state.stageOrder = new Map(state.stages.map((s, i) => [s.id, i]));
    state.pipeOrder = new Map(state.pipelines.map((p, i) => [String(p.id), i]));
    const people = [...new Set(state.records.map(r => r.salesperson).filter(Boolean))].sort((a, b) => a.localeCompare(b, 'vi'));
    state.peopleIndex = new Map(people.map((p, i) => [p, i]));
    iconCache.clear();
  }
  function showSessionExpired(message) {
    showOverlay('Không đọc được dữ liệu', message || 'Phiên đăng nhập Odoo đã hết hạn. Tải lại trang và đăng nhập lại.');
    ui.mapEmpty.hidden = false;
  }
  async function reload(force) {
    if (syncBusy) return; syncBusy = true;
    const button = $('reloadData'); if (button) { button.disabled = true; button.textContent = 'Đang đọc…'; }
    if (ui.syncStatus) ui.syncStatus.textContent = 'Đang đọc dữ liệu Xinyang Odoo…';
    try {
      const response = await fetch(url((prefs.mode === 'potential' ? '/sgt_home/map/potential' : '/sgt_home/map/data') + (force ? '?force=true' : '')), {credentials: 'same-origin', cache: 'no-store'});
      let payload = null; try { payload = await response.json(); } catch (_) { payload = {}; }
      if (response.status === 401) { showSessionExpired(); if (ui.syncStatus) ui.syncStatus.textContent = 'Phiên Odoo đã hết hạn'; return; }
      if (!response.ok) throw Error(typeof payload.detail === 'string' ? payload.detail : ('HTTP ' + response.status));
      state.config = payload.config || {};
      state.records = [...new Map((payload.records || []).map(r => [r.id, r])).values()];
      state.records.forEach(r => { r.lat = coordinate(r.lat); r.lng = coordinate(r.lng); });
      setMeta(payload);
      computeVisible();
      populateFilters(); renderStatus(payload.status || {});
      const first = !state.map;
      if (first) { applyFilters(false); initMap(); }
      else { applyFilters(false); try { state.map.invalidateSize({pan: false}); } catch (_) { /* bỏ qua */ } }
    } catch (err) {
      if (ui.syncStatus) ui.syncStatus.textContent = 'Lỗi: ' + String(err.message || err).slice(0, 160);
      if (!state.records.length) { ui.mapEmpty.hidden = false; showOverlay('Không đọc được dữ liệu bản đồ', String(err.message || err).slice(0, 220)); }
    } finally { syncBusy = false; if (button) { button.disabled = false; button.textContent = '↻ Đọc lại Odoo'; } }
  }

  /* ------------------------------------------------------------------ sự kiện */
  let textTimer = null;
  ui.search.addEventListener('input', () => { renderEventSuggestions(); applyFilters(false); });
  ui.search.addEventListener('focus', renderEventSuggestions);
  ui.searchText.addEventListener('input', () => { clearTimeout(textTimer); textTimer = setTimeout(() => applyFilters(false), 250); });
  document.addEventListener('click', (e) => { if (ui.suggestions && !ui.suggestions.contains(e.target) && e.target !== ui.search) ui.suggestions.hidden = true; });
  ui.expo.addEventListener('change', () => { populateEvents(); renderEventSuggestions(); applyFilters(true); });
  ui.pipeline.addEventListener('change', () => { populateStages(); applyFilters(true); });
  for (const selector of [ui.stage, ui.event, ui.eventLocation, ui.district, ui.owner, ui.tag, ui.geo, ui.provider]) {
    selector.addEventListener('change', () => applyFilters(true));
  }
  ui.province.addEventListener('change', () => { populateDistricts(); applyFilters(true); });
  $('resetFilters').addEventListener('click', () => {
    for (const selector of [ui.search, ui.searchText, ui.pipeline, ui.stage, ui.expo, ui.event, ui.eventLocation, ui.province, ui.district, ui.owner, ui.tag, ui.geo, ui.provider]) selector.value = '';
    if (ui.suggestions) ui.suggestions.hidden = true;
    populateStages(); populateEvents(); populateDistricts();
    state.showPoints = true; state.showHeat = false; state.geoQuick = '';
    $('heatRadius').value = '30'; $('heatIntensity').value = '1.8';
    updateHeatOptions(); applyFilters(true);
  });
  $('loadMore').addEventListener('click', renderMore);
  $('btnPoints').addEventListener('click', () => { state.showPoints = !state.showPoints; updateLayerVisibility(); renderLegend(); });
  $('btnHeat').addEventListener('click', () => { state.showHeat = !state.showHeat; updateLayerVisibility(); });
  $('fitMap').addEventListener('click', fitMap);
  $('toggleSidebar').addEventListener('click', () => {
    const hidden = document.querySelector('.content-layout').classList.toggle('sidebar-hidden');
    $('toggleSidebar').textContent = hidden ? 'Hiện bộ lọc' : 'Ẩn bộ lọc';
    $('toggleSidebar').setAttribute('aria-expanded', String(!hidden));
    if (state.map) state.map.invalidateSize({pan: false});
  });
  if (window.innerWidth < 600) {
    document.querySelector('.content-layout').classList.add('sidebar-hidden');
    $('toggleSidebar').textContent = 'Hiện bộ lọc';
    $('toggleSidebar').setAttribute('aria-expanded', 'false');
  }
  // Chú thích màu thu gọn được (mặc định thu gọn trên điện thoại)
  const legend = $('mapLegend');
  const setLegend = (open) => { legend.classList.toggle('collapsed', !open); $('legendToggle').setAttribute('aria-expanded', String(open)); };
  $('legendToggle').addEventListener('click', () => setLegend(legend.classList.contains('collapsed')));
  setLegend(window.innerWidth >= 600);
  const reloadButton = $('reloadData'); if (reloadButton) reloadButton.addEventListener('click', () => reload(true));
  // Dashboard cha yêu cầu làm mới (nút Làm mới).
  window.addEventListener('message', (e) => { if (e.origin === window.location.origin && e.data === 'xinyang-map-refresh') reload(true); });
  /* ------------------------------------------------------------------ Update 095: 2 chế độ */
  const MODE_TEXT = {
    all: {sub: 'Mọi Deal CRM đang active + Contact MM/Approved · Xinyang Odoo', hint: 'Mọi Deal CRM đang active, tô màu theo Stage. Deal chưa có tọa độ dùng tọa độ của Contact; Deal chưa có cả hai nằm ở danh sách Chờ định vị. Cộng thêm Contact MM/Approved từ bản đồ cũ.', label: 'Tìm Contact / công ty / địa chỉ', list: 'Danh sách khách hàng',
      placeholder: 'Tên Contact, công ty, địa chỉ, #ID...'},
    potential: {sub: 'Contact có Deal ở Match Making & Approved Match Making · Xinyang Odoo', hint: 'Mỗi Công ty một điểm. Chỉ hiện Contact có Deal ở 5.Match Making hoặc 6.Approved Match Making (vàng = MM, xanh lá = Approved, xanh ngọc = cả hai).',
      label: 'Tìm Contact / công ty / thành phố', list: 'Danh sách Contact tiềm năng', placeholder: 'Tên công ty, thành phố...'},
  };
  function applyModeUi() {
    document.body.dataset.mapMode = prefs.mode;
    document.querySelectorAll('[data-map-mode]').forEach(b => {
      const on = b.dataset.mapMode === prefs.mode;
      b.classList.toggle('active', on); b.setAttribute('aria-pressed', String(on));
    });
    const t = MODE_TEXT[prefs.mode];
    const set = (id, v) => { const el = $(id); if (el) el.textContent = v; };
    set('mapSubtitle', t.sub); set('modeHint', t.hint); set('searchTextLabel', t.label); set('listTitle', t.list);
    ui.searchText.placeholder = t.placeholder;
    if (prefs.mode === 'potential' && prefs.colorBy !== 'stage') { prefs.colorBy = 'stage'; syncColorButtons(); }
  }
  async function setMode(mode) {
    if (mode === prefs.mode || syncBusy) return;
    prefs.mode = mode; savePrefs(); applyModeUi();
    for (const selector of [ui.search, ui.searchText, ui.pipeline, ui.stage, ui.expo, ui.event, ui.eventLocation, ui.province, ui.district, ui.owner, ui.tag, ui.geo, ui.provider]) selector.value = '';
    state.selectedId = null; state.geoQuick = ''; state.records = []; state.visible = []; state.filtered = [];
    iconCache.clear();
    applyFilters(false);
    await reload(false);
  }
  document.querySelectorAll('[data-map-mode]').forEach(b => b.addEventListener('click', () => setMode(b.dataset.mapMode)));
  applyModeUi();
  reload(false);
})();
