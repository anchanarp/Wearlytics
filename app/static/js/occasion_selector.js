// occasion_selector.js
// Powers the custom searchable occasion selector and unified season dropdown
// with luxury styling, instant opening, live search, and full modal options.

document.addEventListener('DOMContentLoaded', function () {
  const input          = document.getElementById('occasion-input');
  const hidden         = document.getElementById('occasion-hidden');
  const dropdown       = document.getElementById('occasion-dropdown');
  const dataScript     = document.getElementById('occasions-data');
  const occasionCard   = document.getElementById('occasion-filter-card');
  const occasionArrow  = document.getElementById('occasion-arrow');

  const seasonCard     = document.getElementById('season-filter-card');
  const seasonDropdown = document.getElementById('season-dropdown');
  const seasonInput    = document.getElementById('stylist-season');
  const seasonLabel    = document.getElementById('season-display-label');
  const seasonArrow    = document.getElementById('season-arrow');

  const modal          = document.getElementById('more-options-modal');
  const modalClose     = document.getElementById('modal-close');
  const modalSearch    = document.getElementById('more-options-search');
  const modalList      = document.getElementById('more-options-list');

  if (!input || !hidden || !dropdown) return;

  // ── Data ──────────────────────────────────────────────────────────────────
  let serverOccasions = [];
  if (dataScript) {
    try {
      serverOccasions = JSON.parse(dataScript.textContent.trim());
    } catch (e) {
      console.error('Failed to parse occasions JSON:', e);
    }
  }

  // Common options shown initially in the dropdown
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

  // ── Visual Helper Functions ───────────────────────────────────────────────
  function setArrow(arrowEl, isOpen) {
    if (arrowEl) {
      arrowEl.style.transform = isOpen ? 'rotate(180deg)' : 'rotate(0deg)';
    }
  }

  function setCardOpen(cardEl, isOpen) {
    if (cardEl) {
      if (isOpen) cardEl.classList.add('is-open');
      else cardEl.classList.remove('is-open');
    }
  }

  function makeItem(text, isSelected, onClick) {
    const el = document.createElement('div');
    el.textContent = text;
    el.className   = 'ref-dropdown-item dropdown-item' + (isSelected ? ' is-selected' : '');
    el.addEventListener('click', onClick);
    return el;
  }

  // ── Occasion Dropdown Logic ───────────────────────────────────────────────
  function selectOccasion(value) {
    input.value  = value;
    hidden.value = value;
    closeOccasionDropdown();
    hideModal();
  }

  function renderCommonDropdown() {
    dropdown.innerHTML = '';
    const currentVal = (input.value || hidden.value || '').trim().toLowerCase();
    COMMON_OCCASIONS.forEach(function (opt) {
      const isSel = (opt.toLowerCase() === currentVal);
      dropdown.appendChild(makeItem(opt, isSel, function (e) {
        e.stopPropagation();
        selectOccasion(opt);
      }));
    });

    // Separator
    const sep = document.createElement('div');
    sep.className = 'ref-dropdown-sep';
    dropdown.appendChild(sep);

    // "More options…" entry
    const more = document.createElement('div');
    more.className = 'ref-dropdown-item-more';
    more.textContent = 'More options…';
    more.addEventListener('click', function (e) {
      e.stopPropagation();
      showModal();
    });
    dropdown.appendChild(more);
  }

  function renderFilteredDropdown(query) {
    const q = query.trim().toLowerCase();
    if (q === '') {
      renderCommonDropdown();
      return;
    }
    const matches = FULL_OCCASIONS.filter(o => o.toLowerCase().includes(q));
    dropdown.innerHTML = '';
    const currentVal = (input.value || hidden.value || '').trim().toLowerCase();

    if (matches.length === 0) {
      const empty = document.createElement('div');
      empty.textContent = 'No matches found';
      empty.className   = 'ref-dropdown-item disabled';
      empty.style.color = 'var(--text-muted, #8c7d72)';
      empty.style.cursor = 'default';
      dropdown.appendChild(empty);
    } else {
      matches.forEach(function (opt) {
        const isSel = (opt.toLowerCase() === currentVal);
        dropdown.appendChild(makeItem(opt, isSel, function (e) {
          e.stopPropagation();
          selectOccasion(opt);
        }));
      });
    }
  }

  function openOccasionDropdown() {
    closeSeasonDropdown();
    renderCommonDropdown();
    dropdown.classList.add('is-open');
    dropdown.style.display = 'block';
    setCardOpen(occasionCard, true);
    setArrow(occasionArrow, true);
  }

  function closeOccasionDropdown() {
    dropdown.classList.remove('is-open');
    dropdown.style.display = 'none';
    setCardOpen(occasionCard, false);
    setArrow(occasionArrow, false);
  }

  function toggleOccasionDropdown() {
    const isOpen = dropdown.classList.contains('is-open') || dropdown.style.display === 'block';
    if (isOpen) {
      closeOccasionDropdown();
    } else {
      openOccasionDropdown();
    }
  }

  // ── Season Dropdown Logic ─────────────────────────────────────────────────
  function selectSeason(value) {
    if (seasonInput) seasonInput.value = value;
    if (seasonLabel) seasonLabel.textContent = value;
    if (seasonDropdown) {
      const items = seasonDropdown.querySelectorAll('.ref-dropdown-item');
      items.forEach(function (it) {
        const itVal = it.getAttribute('data-season') || it.textContent.trim();
        if (itVal.toLowerCase() === value.toLowerCase()) {
          it.classList.add('is-selected');
        } else {
          it.classList.remove('is-selected');
        }
      });
    }
    closeSeasonDropdown();
  }

  function openSeasonDropdown() {
    closeOccasionDropdown();
    if (seasonDropdown) {
      seasonDropdown.classList.add('is-open');
      seasonDropdown.style.display = 'block';
      setCardOpen(seasonCard, true);
      setArrow(seasonArrow, true);
    }
  }

  function closeSeasonDropdown() {
    if (seasonDropdown) {
      seasonDropdown.classList.remove('is-open');
      seasonDropdown.style.display = 'none';
      setCardOpen(seasonCard, false);
      setArrow(seasonArrow, false);
    }
  }

  function toggleSeasonDropdown() {
    if (!seasonDropdown) return;
    const isOpen = seasonDropdown.classList.contains('is-open') || seasonDropdown.style.display === 'block';
    if (isOpen) {
      closeSeasonDropdown();
    } else {
      openSeasonDropdown();
    }
  }

  // ── Modal Logic ───────────────────────────────────────────────────────────
  function renderModalList(query) {
    if (!modalList) return;
    const q = (query || '').trim().toLowerCase();
    const items = q
      ? FULL_OCCASIONS.filter(o => o.toLowerCase().includes(q))
      : FULL_OCCASIONS;
    modalList.innerHTML = '';
    const currentVal = (input.value || hidden.value || '').trim().toLowerCase();

    if (items.length === 0) {
      const empty = document.createElement('div');
      empty.textContent = 'No matches found';
      empty.className   = 'ref-dropdown-item disabled';
      empty.style.padding = '10px 14px';
      empty.style.color = 'var(--text-muted, #8c7d72)';
      modalList.appendChild(empty);
    } else {
      items.forEach(function (opt) {
        const isSel = (opt.toLowerCase() === currentVal);
        modalList.appendChild(makeItem(opt, isSel, function (e) {
          e.stopPropagation();
          selectOccasion(opt);
        }));
      });
    }
  }

  function showModal() {
    closeOccasionDropdown();
    closeSeasonDropdown();
    if (!modal) return;
    if (modalSearch) modalSearch.value = '';
    renderModalList('');
    modal.style.display = 'flex';
    if (modalSearch) modalSearch.focus();
  }

  function hideModal() {
    if (modal) modal.style.display = 'none';
  }

  // ── Event Wiring ──────────────────────────────────────────────────────────
  if (occasionCard) {
    occasionCard.addEventListener('click', function (e) {
      if (dropdown.contains(e.target)) return;
      if (e.target === input) {
        if (!dropdown.classList.contains('is-open') && dropdown.style.display !== 'block') {
          openOccasionDropdown();
        }
        return;
      }
      toggleOccasionDropdown();
      if (dropdown.classList.contains('is-open')) {
        input.focus();
      }
    });
  }

  input.addEventListener('focus', function () {
    if (!dropdown.classList.contains('is-open') && dropdown.style.display !== 'block') {
      openOccasionDropdown();
    }
  });

  input.addEventListener('input', function (e) {
    renderFilteredDropdown(e.target.value);
    openOccasionDropdown();
  });

  if (seasonCard && seasonDropdown) {
    seasonCard.addEventListener('click', function (e) {
      if (seasonDropdown.contains(e.target)) return;
      toggleSeasonDropdown();
    });

    const seasonItems = seasonDropdown.querySelectorAll('.ref-dropdown-item');
    seasonItems.forEach(function (item) {
      item.addEventListener('click', function (e) {
        e.stopPropagation();
        const val = item.getAttribute('data-season') || item.textContent.trim();
        selectSeason(val);
      });
    });
  }

  if (modalClose) {
    modalClose.addEventListener('click', hideModal);
  }

  if (modal) {
    modal.addEventListener('click', function (e) {
      if (e.target === modal) hideModal();
    });
  }

  if (modalSearch) {
    modalSearch.addEventListener('input', function (e) {
      renderModalList(e.target.value);
    });
  }

  // Close dropdowns on click outside
  document.addEventListener('click', function (e) {
    const inOccasion = (occasionCard && occasionCard.contains(e.target)) ||
                       (input && input.contains(e.target)) ||
                       (dropdown && dropdown.contains(e.target));
    const inSeason   = (seasonCard && seasonCard.contains(e.target)) ||
                       (seasonDropdown && seasonDropdown.contains(e.target));

    if (!inOccasion) {
      closeOccasionDropdown();
    }
    if (!inSeason) {
      closeSeasonDropdown();
    }
  });

  // Close on Escape
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') {
      closeOccasionDropdown();
      closeSeasonDropdown();
      hideModal();
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

  if (hidden.value) {
    input.value = hidden.value;
  }
});
