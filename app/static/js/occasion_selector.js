// occasion_selector.js
// Powers the custom searchable occasion selector with common options, live search,
// and a "More options…" modal showing the full occasion list.

document.addEventListener('DOMContentLoaded', function () {
  const input      = document.getElementById('occasion-input');
  const hidden     = document.getElementById('occasion-hidden');
  const dropdown   = document.getElementById('occasion-dropdown');
  const dataScript = document.getElementById('occasions-data');
  const modal      = document.getElementById('more-options-modal');
  const modalClose = document.getElementById('modal-close');
  const modalSearch= document.getElementById('more-options-search');
  const modalList  = document.getElementById('more-options-list');

  if (!input || !hidden || !dropdown || !dataScript) return;

  // ── Data ──────────────────────────────────────────────────────────────────
  let serverOccasions = [];
  try {
    serverOccasions = JSON.parse(dataScript.textContent.trim());
  } catch (e) {
    console.error('Failed to parse occasions JSON:', e);
  }

  // Seven common options shown initially in the tiny dropdown
  const COMMON_OCCASIONS = [
    'Casual',
    'Work / Business',
    'College / Campus',
    'Formal',
    'Party',
    'Date Night',
    'Sporty / Workout',
  ];

  // Additional options only needed in the full modal
  const EXTRA_OCCASIONS = [
    'Wedding / Ceremony',
    'Festive / Traditional',
    'Travel / Vacation',
    'Beach / Resort',
    'Brunch / Cafe',
    'Outdoor / Adventure',
    'Home / Relaxed',
    'Any Occasion',
  ];

  // Build a unique full list: common → server → extras (Set preserves insertion order)
  const fullSet = new Set([...COMMON_OCCASIONS, ...serverOccasions, ...EXTRA_OCCASIONS]);
  const FULL_OCCASIONS = Array.from(fullSet);

  // ── Helpers ───────────────────────────────────────────────────────────────
  function selectOccasion(value) {
    input.value  = value;
    hidden.value = value;
    hideDropdown();
    hideModal();
  }

  function makeItem(text, onClick) {
    const el = document.createElement('div');
    el.textContent = text;
    el.className   = 'dropdown-item';
    el.style.cssText = 'padding:8px 12px; cursor:pointer;';
    el.addEventListener('click', onClick);
    return el;
  }

  // ── Tiny dropdown ─────────────────────────────────────────────────────────
  function renderCommonDropdown() {
    dropdown.innerHTML = '';
    COMMON_OCCASIONS.forEach(function (opt) {
      dropdown.appendChild(makeItem(opt, () => selectOccasion(opt)));
    });
    // Separator
    const sep = document.createElement('div');
    sep.style.cssText = 'border-top:1px solid var(--line, #e2e8f0); margin:4px 0;';
    dropdown.appendChild(sep);
    // "More options…" entry
    const more = makeItem('More options…', () => { showModal(); });
    more.style.fontStyle = 'italic';
    more.style.color = 'var(--text-secondary, #888)';
    dropdown.appendChild(more);
  }

  function renderFilteredDropdown(query) {
    const q = query.trim().toLowerCase();
    if (q === '') { renderCommonDropdown(); return; }
    const matches = FULL_OCCASIONS.filter(o => o.toLowerCase().includes(q));
    dropdown.innerHTML = '';
    if (matches.length === 0) {
      const empty = document.createElement('div');
      empty.textContent = 'No matches';
      empty.className   = 'dropdown-item disabled';
      empty.style.cssText = 'padding:8px 12px; color:var(--text-secondary,#888);';
      dropdown.appendChild(empty);
    } else {
      matches.forEach(opt => dropdown.appendChild(makeItem(opt, () => selectOccasion(opt))));
    }
  }

  function showDropdown() { dropdown.style.display = 'block'; }
  function hideDropdown() { dropdown.style.display = 'none';  }

  // ── Modal ─────────────────────────────────────────────────────────────────
  function renderModalList(query) {
    const q = (query || '').trim().toLowerCase();
    const items = q
      ? FULL_OCCASIONS.filter(o => o.toLowerCase().includes(q))
      : FULL_OCCASIONS;
    modalList.innerHTML = '';
    if (items.length === 0) {
      const empty = document.createElement('div');
      empty.textContent = 'No matches';
      empty.style.cssText = 'padding:10px 12px; color:var(--text-secondary,#888);';
      modalList.appendChild(empty);
    } else {
      items.forEach(opt => modalList.appendChild(makeItem(opt, () => selectOccasion(opt))));
    }
  }

  function showModal() {
    hideDropdown();
    modalSearch.value = '';
    renderModalList('');
    modal.style.display = 'flex';
    modalSearch.focus();
  }
  function hideModal() { modal.style.display = 'none'; }

  // ── Event wiring ──────────────────────────────────────────────────────────
  input.addEventListener('focus', function () {
    renderCommonDropdown();
    showDropdown();
  });

  input.addEventListener('input', function (e) {
    renderFilteredDropdown(e.target.value);
    showDropdown();
  });

  modalClose.addEventListener('click', hideModal);
  modal.addEventListener('click', function (e) {
    if (e.target === modal) hideModal();
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') { hideDropdown(); hideModal(); }
  });

  modalSearch.addEventListener('input', function (e) {
    renderModalList(e.target.value);
  });

  // Close on click outside selector area
  document.addEventListener('click', function (e) {
    const inSelector = input.contains(e.target) || dropdown.contains(e.target);
    const inModal    = modal && modal.contains(e.target);
    if (!inSelector && !inModal) {
      hideDropdown();
    }
  });

  // Sync hidden field on form submit
  const form = input.closest('form');
  if (form) {
    form.addEventListener('submit', function () {
      hidden.value = input.value.trim();
    });
  }

  // ── Init ──────────────────────────────────────────────────────────────────
  renderCommonDropdown();

  // Pre-populate input if occasion was already selected (e.g. page reload with filter)
  if (hidden.value) {
    input.value = hidden.value;
  }
});
