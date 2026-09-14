/* static/js/custom_outfit.js */
document.addEventListener('DOMContentLoaded', function () {
  const selectableItems = document.querySelectorAll('.selectable-item');
  const itemIdsInput = document.getElementById('item_ids');
  const previewDiv = document.getElementById('item-preview');

  const selected = new Set();

  function updatePreview() {
    previewDiv.innerHTML = '';
    selected.forEach(id => {
      const img = document.createElement('img');
      img.src = document.querySelector(`.selectable-item[data-item-id='${id}'] img`).src;
      img.alt = '';
      img.className = 'me-2 mb-2';
      img.style.width = '60px';
      img.style.height = '60px';
      previewDiv.appendChild(img);
    });
    itemIdsInput.value = Array.from(selected).join(',');
  }

  function enforceRules(clickedItem) {
    const category = clickedItem.dataset.category;
    // Gather current selection per category
    const categoryCounts = {};
    selected.forEach(id => {
      const cat = document.querySelector(`.selectable-item[data-item-id='${id}']`).dataset.category;
      categoryCounts[cat] = (categoryCounts[cat] || 0) + 1;
    });

    // Dress exclusive rule
    if (category === 'Dresses') {
      // If selecting a Dress, disallow any Tops or Bottoms already selected
      const invalid = Array.from(selected).some(id => {
        const c = document.querySelector(`.selectable-item[data-item-id='${id}']`).dataset.category;
        return c === 'Tops' || c === 'Bottoms';
      });
      if (invalid) {
        alert('When a Dress is selected, do not select Tops or Bottoms.');
        return false;
      }
    } else if (category === 'Tops' || category === 'Bottoms') {
      // If a Dress already selected, prevent selecting Top/Bottom
      const hasDress = Array.from(selected).some(id => {
        const c = document.querySelector(`.selectable-item[data-item-id='${id}']`).dataset.category;
        return c === 'Dresses';
      });
      if (hasDress) {
        alert('When a Dress is selected, do not select Tops or Bottoms.');
        return false;
      }
    }

    // Enforce at most one Top and one Bottom
    if ((category === 'Tops' && (categoryCounts['Tops'] || 0) >= 1) ||
        (category === 'Bottoms' && (categoryCounts['Bottoms'] || 0) >= 1)) {
      alert(`Select at most one ${category.slice(0, -1)}.`);
      return false;
    }
    return true;
  }

  selectableItems.forEach(item => {
    item.addEventListener('click', function () {
      const id = this.dataset.itemId;
      if (selected.has(id)) {
        // Deselect
        selected.delete(id);
        this.classList.remove('border-primary');
        this.querySelector('.overlay-check').classList.add('d-none');
      } else {
        if (!enforceRules(this)) return;
        selected.add(id);
        this.classList.add('border-primary');
        this.querySelector('.overlay-check').classList.remove('d-none');
      }
      updatePreview();
    });
  });
});
