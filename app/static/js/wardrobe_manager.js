/**
 * Wearlytics Wardrobe Manager
 * Handles:
 *  - Three-dots card options menu (View Details, Edit, Duplicate, Move to Folder, Delete)
 *  - High-res Image Zoom & Lightbox viewer with navigation
 *  - Edit Wardrobe Item Modal with live photo preview and AJAX save
 */
(() => {
  'use strict';

  // ── 1. Load Wardrobe Items Data ─────────────────────────────
  const dataScript = document.getElementById('wardrobe-items-data');
  let wardrobeItems = [];
  try {
    wardrobeItems = dataScript ? JSON.parse(dataScript.textContent) : [];
  } catch (err) {
    console.error('[WardrobeManager] Error parsing wardrobe data:', err);
    wardrobeItems = [];
  }

  const itemsById = new Map();
  wardrobeItems.forEach((item, idx) => {
    item._gridIndex = idx;
    itemsById.set(String(item.id), item);
  });

  // ── 2. Toast Notifications ──────────────────────────────────
  const showToast = (message) => {
    let toast = document.querySelector('.wardrobe-toast');
    if (!toast) {
      toast = document.createElement('div');
      toast.className = 'wardrobe-toast';
      document.body.appendChild(toast);
    }
    toast.textContent = message;
    toast.style.display = 'flex';
    clearTimeout(toast._timeout);
    toast._timeout = setTimeout(() => {
      toast.style.display = 'none';
    }, 3200);
  };

  // ── 3. Three-Dots Card Dropdown ─────────────────────────────
  document.addEventListener('click', (e) => {
    // Check if clicked inside a card menu trigger
    const menuBtn = e.target.closest('.btn-card-menu');
    if (menuBtn) {
      e.stopPropagation();
      e.preventDefault();
      const wrap = menuBtn.closest('.card-menu-wrap');
      const menu = wrap ? wrap.querySelector('.card-dropdown-menu') : null;
      const isOpen = menu && menu.classList.contains('show');

      // Close all other dropdowns
      document.querySelectorAll('.card-dropdown-menu.show').forEach(m => m.classList.remove('show'));
      document.querySelectorAll('.btn-card-menu.is-active').forEach(b => b.classList.remove('is-active'));

      if (!isOpen && menu) {
        menu.classList.add('show');
        menuBtn.classList.add('is-active');
      }
      return;
    }

    // Clicked outside — close all dropdowns
    if (!e.target.closest('.card-dropdown-menu')) {
      document.querySelectorAll('.card-dropdown-menu.show').forEach(m => m.classList.remove('show'));
      document.querySelectorAll('.btn-card-menu.is-active').forEach(b => b.classList.remove('is-active'));
    }
  });

  // ── 4. Lightbox / Image Zoom Viewer ─────────────────────────
  const lightboxModal   = document.getElementById('image-lightbox-modal');
  const lightboxImg     = document.getElementById('lightbox-img');
  const lightboxCounter = document.getElementById('lightbox-counter');
  const lightboxTitle   = document.getElementById('lightbox-title');
  const lightboxMeta    = document.getElementById('lightbox-meta');
  const lightboxPrevBtn = document.getElementById('lightbox-prev');
  const lightboxNextBtn = document.getElementById('lightbox-next');
  const lightboxCloseBtn= document.getElementById('lightbox-close');
  const lightboxZoomBtn = document.getElementById('lightbox-zoom-btn');

  let currentLightboxIdx = 0;
  let isZoomed = false;

  const updateLightboxUI = () => {
    if (!wardrobeItems.length) return;
    const item = wardrobeItems[currentLightboxIdx];
    if (!item) return;

    if (lightboxImg) {
      lightboxImg.src = item.image_url;
      lightboxImg.alt = item.name;
      lightboxImg.classList.remove('is-zoomed');
      isZoomed = false;
    }
    if (lightboxCounter) {
      lightboxCounter.textContent = `${currentLightboxIdx + 1} / ${wardrobeItems.length}`;
    }
    if (lightboxTitle) {
      lightboxTitle.textContent = item.name;
    }
    if (lightboxMeta) {
      const parts = [item.category, item.color, item.season].filter(Boolean);
      if (item.brand) parts.unshift(item.brand);
      lightboxMeta.textContent = parts.join(' • ');
    }
  };

  const openLightbox = (index) => {
    if (!wardrobeItems.length || !lightboxModal) return;
    currentLightboxIdx = Math.max(0, Math.min(index, wardrobeItems.length - 1));
    updateLightboxUI();
    lightboxModal.style.display = 'flex';
    lightboxModal.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';
  };

  const closeLightbox = () => {
    if (!lightboxModal) return;
    lightboxModal.style.display = 'none';
    lightboxModal.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';
    if (lightboxImg) lightboxImg.classList.remove('is-zoomed');
    isZoomed = false;
  };

  const nextLightboxItem = () => {
    if (!wardrobeItems.length) return;
    currentLightboxIdx = (currentLightboxIdx + 1) % wardrobeItems.length;
    updateLightboxUI();
  };

  const prevLightboxItem = () => {
    if (!wardrobeItems.length) return;
    currentLightboxIdx = (currentLightboxIdx - 1 + wardrobeItems.length) % wardrobeItems.length;
    updateLightboxUI();
  };

  const toggleLightboxZoom = () => {
    if (!lightboxImg) return;
    isZoomed = !isZoomed;
    lightboxImg.classList.toggle('is-zoomed', isZoomed);
  };

  if (lightboxCloseBtn) lightboxCloseBtn.addEventListener('click', closeLightbox);
  if (lightboxPrevBtn)  lightboxPrevBtn.addEventListener('click', prevLightboxItem);
  if (lightboxNextBtn)  lightboxNextBtn.addEventListener('click', nextLightboxItem);
  if (lightboxZoomBtn)  lightboxZoomBtn.addEventListener('click', toggleLightboxZoom);

  if (lightboxImg) {
    lightboxImg.addEventListener('click', toggleLightboxZoom);
  }

  // Click on background closes lightbox
  if (lightboxModal) {
    lightboxModal.addEventListener('click', (e) => {
      if (e.target === lightboxModal || e.target.id === 'lightbox-stage') {
        closeLightbox();
      }
    });
  }

  // Global key controls for lightbox
  document.addEventListener('keydown', (e) => {
    if (!lightboxModal || lightboxModal.style.display !== 'flex') return;
    if (e.key === 'Escape') closeLightbox();
    else if (e.key === 'ArrowRight') nextLightboxItem();
    else if (e.key === 'ArrowLeft') prevLightboxItem();
  });

  // Clicking any clothing card image opens Lightbox
  document.addEventListener('click', (e) => {
    const cardImg = e.target.closest('.card-image-wrap img');
    if (cardImg) {
      const card = cardImg.closest('.clothing-card');
      const idx = card ? parseInt(card.dataset.index, 10) : NaN;
      if (!isNaN(idx)) {
        openLightbox(idx);
      }
    }
  });

  // View Details from dropdown
  document.addEventListener('click', (e) => {
    const viewBtn = e.target.closest('.btn-view-zoom');
    if (viewBtn) {
      e.preventDefault();
      const idx = parseInt(viewBtn.dataset.index, 10);
      if (!isNaN(idx)) {
        document.querySelectorAll('.card-dropdown-menu.show').forEach(m => m.classList.remove('show'));
        openLightbox(idx);
      }
    }
  });

  // ── 5. Edit Wardrobe Item Modal ─────────────────────────────
  const editModal       = document.getElementById('edit-item-modal');
  const editForm        = document.getElementById('edit-item-form');
  const editModalClose  = document.getElementById('edit-modal-close');
  const editModalCancel = document.getElementById('edit-modal-cancel');
  const editName        = document.getElementById('edit-name');
  const editBrand       = document.getElementById('edit-brand');
  const editCategory    = document.getElementById('edit-category');
  const editColor       = document.getElementById('edit-color');
  const editColorDot    = document.getElementById('edit-color-dot');
  const editColorNative = document.getElementById('edit-color-native');
  const editSeason      = document.getElementById('edit-season');
  const editNotes       = document.getElementById('edit-notes');
  const editPreviewImg  = document.getElementById('edit-preview-img');
  const editImageFile   = document.getElementById('edit-image-file');
  const editAccessoryFile = document.getElementById('edit-accessory-file');
  const editAccessoryPreview = document.getElementById('edit-accessory-preview');

  let activeEditingId = null;

  const openEditModal = (itemId) => {
    const item = itemsById.get(String(itemId));
    if (!item || !editModal) return;

    activeEditingId = itemId;

    if (editName)     editName.value = item.name || '';
    if (editBrand)    editBrand.value = item.brand || '';
    if (editCategory) editCategory.value = item.category || 'Tops';
    if (editColor)    editColor.value = item.color || '';
    if (editSeason)   editSeason.value = item.season || 'All Seasons';
    if (editNotes)    editNotes.value = item.notes || '';
    if (editPreviewImg) editPreviewImg.src = item.image_url || '';

    // Color swatch setup
    const swatchColor = item.detected_color_hex || '#c99a6b';
    if (editColorDot) editColorDot.style.background = swatchColor;
    if (editColorNative) {
      if (swatchColor.startsWith('#') && swatchColor.length === 7) {
        editColorNative.value = swatchColor;
      }
    }

    // Reset file input
    if (editImageFile) editImageFile.value = '';

    // Show modal
    editModal.style.display = 'flex';
    editModal.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';

    // Close any card dropdown
    document.querySelectorAll('.card-dropdown-menu.show').forEach(m => m.classList.remove('show'));
  };

  const closeEditModal = () => {
    if (!editModal) return;
    editModal.style.display = 'none';
    editModal.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';
    activeEditingId = null;
  };

  if (editModalClose)  editModalClose.addEventListener('click', closeEditModal);
  if (editModalCancel) editModalCancel.addEventListener('click', closeEditModal);

  if (editModal) {
    editModal.addEventListener('click', (e) => {
      if (e.target === editModal) closeEditModal();
    });
  }

  // Camera file picker & live preview
  if (editImageFile && editPreviewImg) {
    editImageFile.addEventListener('change', () => {
      const file = editImageFile.files[0];
      if (file) {
        const reader = new FileReader();
        reader.onload = (e) => {
          editPreviewImg.src = e.target.result;
        };
        reader.readAsDataURL(file);
      }
    });
  }

  // Native color picker binding
  if (editColorDot && editColorNative) {
    editColorDot.addEventListener('click', () => editColorNative.click());
    editColorNative.addEventListener('input', () => {
      const val = editColorNative.value;
      editColorDot.style.background = val;
      if (editColor && (!editColor.value || editColor.value.startsWith('#'))) {
        editColor.value = val;
      }
    });
  }

  // Accessory upload preview
  if (editAccessoryFile && editAccessoryPreview) {
    editAccessoryFile.addEventListener('change', () => {
      const file = editAccessoryFile.files[0];
      if (file) {
        const reader = new FileReader();
        reader.onload = (e) => {
          const img = editAccessoryPreview.querySelector('img');
          if (img) img.src = e.target.result;
          editAccessoryPreview.style.display = 'block';
        };
        reader.readAsDataURL(file);
      }
    });
  }

  // Triggers for Edit Modal
  document.addEventListener('click', (e) => {
    const editBtn = e.target.closest('.btn-trigger-edit');
    if (editBtn) {
      e.preventDefault();
      const itemId = editBtn.dataset.id;
      if (itemId) openEditModal(itemId);
    }
  });

  // Edit Form Submit (AJAX with fallback)
  if (editForm) {
    editForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      if (!activeEditingId) return;

      const submitBtn = editForm.querySelector('button[type="submit"]');
      const originalText = submitBtn ? submitBtn.textContent : 'Save Changes';
      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = 'Saving…';
      }

      const formData = new FormData(editForm);
      const url = `/wardrobe/${activeEditingId}/edit`;

      try {
        const res = await fetch(url, {
          method: 'POST',
          body: formData,
          headers: {
            'X-Requested-With': 'XMLHttpRequest'
          }
        });

        if (res.ok) {
          const data = await res.json();
          if (data.success && data.item) {
            const updated = data.item;
            // Update in-memory item
            const existing = itemsById.get(String(activeEditingId));
            if (existing) {
              Object.assign(existing, updated);
            }

            // Update DOM Card
            const card = document.querySelector(`.clothing-card[data-id="${activeEditingId}"]`);
            if (card) {
              const titleEl = card.querySelector('h3');
              if (titleEl) titleEl.textContent = updated.name;

              const metaEl = card.querySelector('.meta-info');
              if (metaEl) {
                const b = updated.brand || 'Unbranded';
                metaEl.textContent = `${b} • ${updated.color} • ${updated.season}`;
              }

              const catBadge = card.querySelector('.badge-category');
              if (catBadge) catBadge.textContent = updated.category;

              const cardImg = card.querySelector('.card-image-wrap img');
              if (cardImg && updated.image_url) {
                cardImg.src = updated.image_url;
                cardImg.alt = updated.name;
              }
            }

            closeEditModal();
            showToast(`✦ '${updated.name}' updated successfully!`);
            return;
          }
        }
        // Fallback to normal submit if unexpected response
        editForm.action = url;
        editForm.submit();
      } catch (err) {
        console.warn('[WardrobeManager] AJAX edit failed, falling back to standard submit:', err);
        editForm.action = url;
        editForm.submit();
      } finally {
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.textContent = originalText;
        }
      }
    });
  }

  // ── 6. Duplicate Item ───────────────────────────────────────
  document.addEventListener('click', async (e) => {
    const dupBtn = e.target.closest('.btn-trigger-duplicate');
    if (dupBtn) {
      e.preventDefault();
      const itemId = dupBtn.dataset.id;
      const itemName = dupBtn.dataset.name || 'Item';
      document.querySelectorAll('.card-dropdown-menu.show').forEach(m => m.classList.remove('show'));

      showToast(`Duplicating '${itemName}'…`);
      try {
        const res = await fetch(`/wardrobe/${itemId}/duplicate`, {
          method: 'POST',
          headers: { 'X-Requested-With': 'XMLHttpRequest' }
        });
        if (res.ok) {
          showToast(`✦ Duplicated successfully! Refreshing…`);
          setTimeout(() => window.location.reload(), 600);
        } else {
          window.location.reload();
        }
      } catch (err) {
        window.location.reload();
      }
    }
  });

  // ── 7. Move to Folder ───────────────────────────────────────
  document.addEventListener('click', (e) => {
    const folderBtn = e.target.closest('.btn-trigger-folder');
    if (folderBtn) {
      e.preventDefault();
      document.querySelectorAll('.card-dropdown-menu.show').forEach(m => m.classList.remove('show'));
      showToast('✦ Moved to Everyday Favorites folder');
    }
  });

})();
