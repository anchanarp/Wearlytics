// Wardrobe Accordion JS — AI Stylist
// Unified control bar mode: single "Select from My Wardrobe" toggle button.
// No separate "Let AI Choose" / "Select from My Wardrobe" mode cards.
// DB fields on each item: id, name, category, color, season, style,
//   clothing_type, image_url, is_in_laundry, is_favorite
(() => {
  'use strict';

  /* ── DOM refs ──────────────────────────────────────────────────────── */
  const wardrobeToggleBtn = document.getElementById('wardrobe-toggle-btn');
  const wardrobeSection   = document.getElementById('wardrobe-section');
  const selectionPanel    = document.getElementById('selection-panel');
  const pinnedContainer   = document.getElementById('pinned-hidden-inputs');
  const pinnedPreview     = document.getElementById('pinned-items-preview');
  const selectionCount    = document.getElementById('selection-count');
  const selectionEmpty    = document.getElementById('selection-empty');
  const selectionFooter   = document.getElementById('selection-footer');
  const clearAllBtn       = document.getElementById('clear-all-btn');
  const filterBtn         = document.getElementById('filter-btn');
  const filterPopover     = document.getElementById('filter-popover');
  const searchInput       = document.getElementById('wardrobe-search');
  const accordionRoot     = document.getElementById('wardrobe-accordion');
  const wardrobeSelCount  = document.getElementById('wardrobe-sel-count');
  const wardrobeToggleLabel = document.getElementById('wardrobe-toggle-label');

  const wardrobeDataScript = document.getElementById('wardrobe-data');
  const wardrobe = wardrobeDataScript ? JSON.parse(wardrobeDataScript.textContent) : [];

  /* ── Category mapping ──────────────────────────────────────────────────
     DB categories are already canonical (Tops/Bottoms/Dresses/Shoes/
     Outerwear/Accessories). The map handles lower-cased variants plus any
     legacy string that might exist. Unknown values land in "Other" instead
     of silently mis-classifying as Accessories.
  ─────────────────────────────────────────────────────────────────────── */
  const CANONICAL = new Set(['Tops','Bottoms','Dresses','Shoes','Outerwear','Accessories']);
  const categoryMap = {
    // Added singular forms mapping
    top: 'Tops',
    bottom: 'Bottoms',
    dress: 'Dresses',
    shoe: 'Shoes',
    outerwear: 'Outerwear',
    accessory: 'Accessories',
    tshirt:'Tops', 'tshirts':'Tops', 't-shirts':'Tops', 't shirt':'Tops',
    tees:'Tops', hoodies:'Tops', sweaters:'Tops', knit:'Tops', knitwear:'Tops',
    pants:'Bottoms', trousers:'Bottoms', jeans:'Bottoms',
    shorts:'Bottoms', skirts:'Bottoms', bottoms:'Bottoms', leggings:'Bottoms',
    dresses:'Dresses', dress:'Dresses', gown:'Dresses', gowns:'Dresses',
    jumpsuit:'Dresses', jumpsuits:'Dresses',
    shoes:'Shoes', sneakers:'Shoes', boots:'Shoes',
    sandals:'Shoes', footwear:'Shoes', heels:'Shoes', flats:'Shoes',
    loafers:'Shoes', oxfords:'Shoes',
    jackets:'Outerwear', jacket:'Outerwear',
    coat:'Outerwear', coats:'Outerwear', outerwear:'Outerwear',
    blazer:'Outerwear', blazers:'Outerwear',
    accessories:'Accessories', accessory:'Accessories',
    jewelry:'Accessories', bags:'Accessories', bag:'Accessories',
    hats:'Accessories', hat:'Accessories', belt:'Accessories', belts:'Accessories',
    scarf:'Accessories', scarves:'Accessories',
  };
  const ORDER = ['Tops','Bottoms','Dresses','Shoes','Outerwear','Accessories','Other'];
  const groups = Object.fromEntries(ORDER.map(k => [k, []]));

  wardrobe.forEach(item => {
    const raw = (item.category || '').trim();
    if (CANONICAL.has(raw)) { groups[raw].push(item); return; }
    const mapped = categoryMap[raw.toLowerCase()];
    if (mapped) { groups[mapped].push(item); return; }
    console.warn(`[Wardrobe] Unknown category: "${raw}" — placed in Other`);
    groups['Other'].push(item);
  });

  /* ── Wardrobe section toggle ────────────────────────────────────────── */
  let wardrobeOpen = false;

  const openWardrobe = () => {
    wardrobeOpen = true;
    wardrobeSection.style.display = '';
    wardrobeToggleBtn.classList.add('wardrobe-toggle--active');
    wardrobeToggleBtn.setAttribute('aria-expanded', 'true');
    // Scroll gently into view
    setTimeout(() => wardrobeSection.scrollIntoView({ behavior: 'smooth', block: 'start' }), 80);
  };

  const closeWardrobe = () => {
    wardrobeOpen = false;
    wardrobeSection.style.display = 'none';
    wardrobeToggleBtn.classList.remove('wardrobe-toggle--active');
    wardrobeToggleBtn.setAttribute('aria-expanded', 'false');
  };

  if (wardrobeToggleBtn) {
    wardrobeToggleBtn.addEventListener('click', () => {
      wardrobeOpen ? closeWardrobe() : openWardrobe();
    });
  }

  /* ── Update toggle button badge & label ─────────────────────────────── */
  const updateToggleUI = () => {
    const count = pinnedContainer
      ? pinnedContainer.querySelectorAll('input[name="item_ids"]').length
      : 0;
    if (wardrobeSelCount) {
      if (count > 0) {
        wardrobeSelCount.textContent = count;
        wardrobeSelCount.style.display = '';
        if (wardrobeToggleLabel) wardrobeToggleLabel.textContent = 'Wardrobe Items';
      } else {
        wardrobeSelCount.style.display = 'none';
        if (wardrobeToggleLabel) wardrobeToggleLabel.textContent = 'Select from My Wardrobe';
      }
    }
  };

  /* ── Build filter popover ──────────────────────────────────────────────
     Filters: Color, Season, Style (actual DB fields).
     "Occasion" is NOT a per-item DB field — not included.
  ─────────────────────────────────────────────────────────────────────── */
  const unique = field => [...new Set(wardrobe.map(i => i[field]).filter(Boolean))].sort();
  const colors  = unique('color');
  const seasons = unique('season');
  const styles  = unique('style');

  /* ── Filter logic (defined BEFORE filterPopover block to avoid TDZ) ── */
  const applyFilters = () => {
    if (!filterPopover) return;
    const selColors  = [...filterPopover.querySelectorAll('input[name="f-color"]:checked')].map(c => c.value);
    const selSeasons = [...filterPopover.querySelectorAll('input[name="f-season"]:checked')].map(c => c.value);
    const selStyles  = [...filterPopover.querySelectorAll('input[name="f-style"]:checked')].map(c => c.value);
    if (!accordionRoot) return;
    accordionRoot.querySelectorAll('.wardrobe-card').forEach(card => {
      const d = JSON.parse(card.dataset.item);
      const ok = (!selColors.length  || selColors.includes(d.color))
              && (!selSeasons.length || selSeasons.includes(d.season))
              && (!selStyles.length  || selStyles.includes(d.style));
      card.style.display = ok ? '' : 'none';
    });
  };

  const buildCheckGroup = (label, values, name) => {
    if (!values.length) return null;
    const wrap = document.createElement('div');
    wrap.className = 'filter-group';
    const hdr = document.createElement('strong');
    hdr.textContent = label;
    wrap.appendChild(hdr);
    values.forEach(val => {
      const lbl = document.createElement('label');
      const cb  = document.createElement('input');
      cb.type = 'checkbox'; cb.value = val; cb.name = name;
      lbl.appendChild(cb);
      // Use createTextNode (universally supported) instead of Element.append()
      lbl.appendChild(document.createTextNode('\u00a0' + val));
      wrap.appendChild(lbl);
    });
    return wrap;
  };

  if (filterPopover) {
    try {
      [
        buildCheckGroup('Color',  colors,  'f-color'),
        buildCheckGroup('Season', seasons, 'f-season'),
        buildCheckGroup('Style',  styles,  'f-style'),
      ].forEach(g => { if (g) filterPopover.appendChild(g); });

      const clearFiltersBtn = document.createElement('button');
      clearFiltersBtn.type = 'button';
      clearFiltersBtn.textContent = 'Clear Filters';
      clearFiltersBtn.className = 'btn light-button';
      filterPopover.appendChild(clearFiltersBtn);

      filterBtn && filterBtn.addEventListener('click', e => {
        e.stopPropagation();
        filterPopover.classList.toggle('active');
      });
      document.addEventListener('click', e => {
        if (filterBtn && !filterBtn.contains(e.target) && !filterPopover.contains(e.target))
          filterPopover.classList.remove('active');
      });
      clearFiltersBtn.addEventListener('click', () => {
        filterPopover.querySelectorAll('input[type="checkbox"]').forEach(cb => cb.checked = false);
        applyFilters();
        filterPopover.classList.remove('active');
      });
      filterPopover.addEventListener('change', applyFilters);
    } catch (filterErr) {
      console.warn('[Wardrobe] Filter popover setup error (non-fatal):', filterErr);
    }
  }



  /* ── Render accordion ──────────────────────────────────────────────── */
  if (accordionRoot) {
    ORDER.forEach(groupName => {
      const items = groups[groupName];
      if (!items.length) return;

      const header = document.createElement('div');
      header.className = 'accordion-header';
      header.setAttribute('role', 'button');
      header.setAttribute('aria-expanded', 'false');
      header.innerHTML = `<span>${groupName} (${items.length})</span><span class="chevron">›</span>`;

      const body = document.createElement('div');
      body.className = 'accordion-body';

      items.forEach(item => {
        const card = document.createElement('div');
        card.className = 'wardrobe-card' + (item.is_in_laundry ? ' disabled' : '');
        card.dataset.item = JSON.stringify(item);

        const thumbWrap = document.createElement('div');
        thumbWrap.className = 'wardrobe-card-thumb';
        const img = document.createElement('img');
        img.src = item.image_url; img.alt = item.name; img.loading = 'lazy';
        thumbWrap.appendChild(img);

        const nameEl = document.createElement('div');
        nameEl.className = 'wardrobe-card-name';
        nameEl.textContent = item.name;

        const metaEl = document.createElement('div');
        metaEl.className = 'wardrobe-card-meta';
        metaEl.textContent = `${item.category}\u00a0·\u00a0${item.color}`;

        card.appendChild(thumbWrap);
        card.appendChild(nameEl);
        card.appendChild(metaEl);

        if (item.is_in_laundry) {
          const badge = document.createElement('div');
          badge.className = 'laundry-badge';
          badge.textContent = 'In Laundry';
          card.appendChild(badge);
        } else {
          card.addEventListener('click', () => toggleItem(item, card));
        }
        body.appendChild(card);
      });

      header.addEventListener('click', () => {
        const open = header.getAttribute('aria-expanded') === 'true';
        header.setAttribute('aria-expanded', String(!open));
        body.classList.toggle('active', !open);
      });

      accordionRoot.appendChild(header);
      accordionRoot.appendChild(body);
    });
  }

  /* ── Toggle item selection ─────────────────────────────────────────── */
  const toggleItem = (item, card) => {
    if (!pinnedContainer) return;
    const existing = pinnedContainer.querySelector(`input[value="${item.id}"]`);
    if (existing) {
      existing.remove();
      card.classList.remove('selected');
    } else {
      const inp = document.createElement('input');
      inp.type = 'hidden'; inp.name = 'item_ids'; inp.value = item.id;
      pinnedContainer.appendChild(inp);
      card.classList.add('selected');
    }
    renderSelection();
    updateToggleUI();
  };

  /* ── Render selection panel ────────────────────────────────────────── */
  const renderSelection = () => {
    if (!pinnedContainer) return;
    const ids = [...pinnedContainer.querySelectorAll('input')].map(i => i.value);
    if (selectionCount) selectionCount.textContent = ids.length + (ids.length === 1 ? ' item' : ' items');

    if (pinnedPreview) pinnedPreview.querySelectorAll('.pinned-tag').forEach(t => t.remove());

    if (ids.length === 0) {
      if (selectionEmpty) selectionEmpty.style.display = '';
      if (selectionFooter) selectionFooter.style.display = 'none';
      return;
    }
    if (selectionEmpty) selectionEmpty.style.display = 'none';
    if (selectionFooter) selectionFooter.style.display = 'flex';

    ids.forEach(id => {
      const item = wardrobe.find(i => String(i.id) === String(id));
      if (!item || !pinnedPreview) return;

      const tag = document.createElement('div');
      tag.className = 'pinned-tag';

      const thumbWrap = document.createElement('div');
      thumbWrap.className = 'pinned-tag-thumb';
      const tImg = document.createElement('img');
      tImg.src = item.image_url; tImg.alt = item.name;
      thumbWrap.appendChild(tImg);

      const info = document.createElement('div');
      info.className = 'pinned-tag-info';
      const nameSpan = document.createElement('div');
      nameSpan.className = 'pinned-tag-name'; nameSpan.textContent = item.name;
      const catSpan = document.createElement('div');
      catSpan.className = 'pinned-tag-cat'; catSpan.textContent = item.category;
      info.appendChild(nameSpan); info.appendChild(catSpan);

      const removeBtn = document.createElement('button');
      removeBtn.type = 'button'; removeBtn.className = 'pinned-tag-remove';
      removeBtn.textContent = '\u00d7'; removeBtn.title = 'Remove';
      removeBtn.addEventListener('click', () => {
        const inp = pinnedContainer.querySelector(`input[value="${id}"]`);
        if (inp) inp.remove();
        if (accordionRoot) {
          const card = accordionRoot.querySelector(`.wardrobe-card[data-item*='"id":${id}']`);
          if (card) card.classList.remove('selected');
        }
        renderSelection();
        updateToggleUI();
      });

      tag.appendChild(thumbWrap);
      tag.appendChild(info);
      tag.appendChild(removeBtn);
      pinnedPreview.appendChild(tag);
    });
  };

  /* ── Clear All ─────────────────────────────────────────────────────── */
  if (clearAllBtn) {
    clearAllBtn.addEventListener('click', () => {
      if (pinnedContainer) pinnedContainer.innerHTML = '';
      if (accordionRoot) accordionRoot.querySelectorAll('.wardrobe-card.selected').forEach(c => c.classList.remove('selected'));
      renderSelection();
      updateToggleUI();
    });
  }

  /* ── Search ────────────────────────────────────────────────────────── */
  if (searchInput && accordionRoot) {
    searchInput.addEventListener('input', () => {
      const q = searchInput.value.toLowerCase();
      accordionRoot.querySelectorAll('.accordion-body').forEach(body => {
        let groupHasMatch = false;
        body.querySelectorAll('.wardrobe-card').forEach(card => {
          const d = JSON.parse(card.dataset.item);
          const text = `${d.name} ${d.category} ${d.color} ${d.season} ${d.style}`.toLowerCase();
          const match = !q || text.includes(q);
          card.style.display = match ? '' : 'none';
          if (match) groupHasMatch = true;
        });
        if (q && groupHasMatch) {
          body.classList.add('active');
          body.previousElementSibling.setAttribute('aria-expanded', 'true');
        }
      });
    });
  }

  /* ── Init ──────────────────────────────────────────────────────────── */
  renderSelection();
  updateToggleUI();
  // Start with wardrobe closed (clean unified bar)
  if (wardrobeSection) wardrobeSection.style.display = 'none';

})();
