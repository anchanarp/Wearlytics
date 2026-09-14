/* Wearlytics Client JavaScript */

// ============================================================
// Dark Mode Toggle
// ============================================================
(function() {
  var html = document.documentElement;
  var btn = null;

  function applyTheme(theme) {
    if (theme === 'dark') {
      html.setAttribute('data-theme', 'dark');
    } else {
      html.removeAttribute('data-theme');
    }
    updateToggleIcon(theme);
    localStorage.setItem('wearlytics-theme', theme);
  }

  function updateToggleIcon(theme) {
    var sun = document.querySelector('.icon-sun');
    var moon = document.querySelector('.icon-moon');
    if (!sun || !moon) return;
    if (theme === 'dark') {
      sun.style.display = '';
      moon.style.display = 'none';
    } else {
      sun.style.display = 'none';
      moon.style.display = '';
    }
  }

  function currentTheme() {
    return html.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';
  }

  document.addEventListener('DOMContentLoaded', function() {
    btn = document.getElementById('themeToggle');
    if (btn) {
      btn.addEventListener('click', function() {
        var next = currentTheme() === 'dark' ? 'light' : 'dark';
        applyTheme(next);
      });
    }
    // Sync icon with current theme on page load
    updateToggleIcon(currentTheme());
  });
})();


// ============================================================
// Auto-dismiss alerts after 5 seconds
// ============================================================
document.addEventListener('DOMContentLoaded', function() {
  setTimeout(function() {
    var alerts = document.querySelectorAll('.alert-custom');
    alerts.forEach(function(alert) {
      alert.style.opacity = '0';
      alert.style.transition = 'opacity 0.5s ease';
      setTimeout(function() { alert.remove(); }, 500);
    });
  }, 5000);
});


// ============================================================
// Image Preview for Clothing Upload
// ============================================================
function previewUploadImage(input) {
  var previewBox = document.getElementById('imagePreview');
  var previewImg = document.getElementById('previewImg');

  if (input.files && input.files[0]) {
    var reader = new FileReader();
    reader.onload = function(e) {
      previewImg.src = e.target.result;
      previewBox.classList.remove('d-none');
    };
    reader.readAsDataURL(input.files[0]);
    // Clear preset selection if custom image uploaded
    document.getElementById('preset_url').value = '';
    document.querySelectorAll('.preset-card').forEach(function(card) { card.classList.remove('selected'); });
  }
}

// Preset Selection for Clothing Upload
function selectPreset(url, element) {
  document.getElementById('preset_url').value = url;
  document.querySelectorAll('.preset-card').forEach(function(card) { card.classList.remove('selected'); });
  element.classList.add('selected');

  // Clear file input
  var fileInput = document.getElementById('image_file');
  if (fileInput) fileInput.value = '';

  var previewBox = document.getElementById('imagePreview');
  var previewImg = document.getElementById('previewImg');
  if (previewImg && previewBox) {
    previewImg.src = url;
    previewBox.classList.remove('d-none');
  }
}
