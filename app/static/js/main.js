/* Wearlytics Client JavaScript */

// ============================================================
// Premium Hero Carousel — Auto-slide, arrows, dots, Ken Burns
// ============================================================
document.addEventListener('DOMContentLoaded', function () {
  var carousel = document.getElementById('heroCarousel');
  if (!carousel) return;

  var slides   = carousel.querySelectorAll('.hero-slide');
  var dots     = carousel.querySelectorAll('.hero-dot');
  var prevBtn  = document.getElementById('heroPrev');
  var nextBtn  = document.getElementById('heroNext');
  var total    = slides.length;
  var current  = 0;
  var autoInterval;
  var INTERVAL = 5000; // 5 seconds between slides

  function goTo(idx) {
    // Clamp & wrap
    idx = ((idx % total) + total) % total;

    // Deactivate current
    slides[current].classList.remove('active');
    if (dots[current]) {
      dots[current].classList.remove('active');
      dots[current].setAttribute('aria-selected', 'false');
    }

    // Force Ken Burns reset on new slide background before activating
    var newBg = slides[idx].querySelector('.hero-slide-img');
    if (newBg) {
      newBg.style.transition = 'none';
      newBg.style.transform  = 'scale(1.04)';
      // Force reflow so the browser registers the reset
      void newBg.offsetWidth;
      newBg.style.transition = '';
    }

    current = idx;

    // Activate new slide
    slides[current].classList.add('active');
    if (dots[current]) {
      dots[current].classList.add('active');
      dots[current].setAttribute('aria-selected', 'true');
    }
  }

  function startAuto() {
    clearInterval(autoInterval);
    autoInterval = setInterval(function () { goTo(current + 1); }, INTERVAL);
  }

  function stopAuto() {
    clearInterval(autoInterval);
  }

  // Arrow buttons
  if (prevBtn) {
    prevBtn.addEventListener('click', function () {
      goTo(current - 1);
      stopAuto(); startAuto();
    });
  }

  if (nextBtn) {
    nextBtn.addEventListener('click', function () {
      goTo(current + 1);
      stopAuto(); startAuto();
    });
  }

  // Dot navigation
  dots.forEach(function (dot) {
    dot.addEventListener('click', function () {
      var idx = parseInt(this.getAttribute('data-dot'), 10);
      goTo(idx);
      stopAuto(); startAuto();
    });
  });

  // Pause on hover; resume on leave
  carousel.addEventListener('mouseenter', stopAuto);
  carousel.addEventListener('mouseleave', startAuto);

  // Touch/swipe support
  var touchStartX = 0;
  carousel.addEventListener('touchstart', function (e) {
    touchStartX = e.touches[0].clientX;
  }, { passive: true });
  carousel.addEventListener('touchend', function (e) {
    var delta = e.changedTouches[0].clientX - touchStartX;
    if (Math.abs(delta) > 40) {
      goTo(delta < 0 ? current + 1 : current - 1);
      stopAuto(); startAuto();
    }
  }, { passive: true });

  // Keyboard accessibility
  carousel.setAttribute('tabindex', '0');
  carousel.addEventListener('keydown', function (e) {
    if (e.key === 'ArrowLeft')  { goTo(current - 1); stopAuto(); startAuto(); }
    if (e.key === 'ArrowRight') { goTo(current + 1); stopAuto(); startAuto(); }
  });

  // Pause when tab is hidden to save battery
  document.addEventListener('visibilitychange', function () {
    if (document.hidden) stopAuto(); else startAuto();
  });

  // Kick off
  startAuto();
});

// ============================================================
// Dark & Light Mode Toggle
// ============================================================
(function() {
  var html = document.documentElement;

  function applyTheme(theme) {
    if (theme === 'light') {
      html.setAttribute('data-theme', 'light');
    } else {
      html.setAttribute('data-theme', 'dark');
      theme = 'dark';
    }
    updateToggleIcon(theme);
    try {
      localStorage.setItem('wearlytics-theme', theme);
    } catch(e) {}
  }

  function updateToggleIcon(theme) {
    var sun = document.querySelector('.icon-sun');
    var moon = document.querySelector('.icon-moon');
    if (!sun || !moon) return;
    if (theme === 'dark') {
      // In Dark Mode, show the Sun icon so user can switch to Light Mode
      sun.style.display = 'block';
      moon.style.display = 'none';
    } else {
      // In Light Mode, show the Moon icon so user can switch to Dark Mode
      sun.style.display = 'none';
      moon.style.display = 'block';
    }
  }

  function currentTheme() {
    return html.getAttribute('data-theme') === 'light' ? 'light' : 'dark';
  }

  function initTheme() {
    var saved = localStorage.getItem('wearlytics-theme');
    var theme = (saved === 'light') ? 'light' : 'dark';
    applyTheme(theme);

    var btn = document.getElementById('themeToggle');
    if (btn) {
      btn.onclick = function() {
        var next = currentTheme() === 'dark' ? 'light' : 'dark';
        applyTheme(next);
      };
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initTheme);
  } else {
    initTheme();
  }
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
  var dropzoneContent = document.getElementById('dropzoneContent') || document.querySelector('.dropzone-content') || document.querySelector('.dropzone-label');
  var dropzone = document.getElementById('dropzone');

  if (input.files && input.files[0]) {
    var reader = new FileReader();
    reader.onload = function(e) {
      if (previewImg) previewImg.src = e.target.result;
      if (previewBox) previewBox.classList.remove('d-none');
      if (dropzoneContent) dropzoneContent.classList.add('d-none');
      if (dropzone) dropzone.classList.add('has-preview');
    };
    reader.readAsDataURL(input.files[0]);
    var presetInput = document.getElementById('preset_url');
    if (presetInput) presetInput.value = '';
    document.querySelectorAll('.preset-card').forEach(function(card) { card.classList.remove('selected'); });
  }
}

function clearUploadPreview() {
  var fileInput = document.getElementById('image_file');
  if (fileInput) fileInput.value = '';
  var previewBox = document.getElementById('imagePreview');
  var previewImg = document.getElementById('previewImg');
  var dropzoneContent = document.getElementById('dropzoneContent') || document.querySelector('.dropzone-content') || document.querySelector('.dropzone-label');
  var dropzone = document.getElementById('dropzone');

  if (previewImg) previewImg.src = '#';
  if (previewBox) previewBox.classList.add('d-none');
  if (dropzoneContent) dropzoneContent.classList.remove('d-none');
  if (dropzone) dropzone.classList.remove('has-preview');

  var presetInput = document.getElementById('preset_url');
  if (presetInput) presetInput.value = '';

  // Reset AI suggestion panel if present
  var aiPanel = document.getElementById('aiSuggestionPanel');
  if (aiPanel) aiPanel.classList.add('d-none');
  var aiSource = document.getElementById('aiSourceLabel');
  if (aiSource) aiSource.textContent = '✦ Ready for Image';
}

// Preset Selection for Clothing Upload
function selectPreset(url, element) {
  var presetInput = document.getElementById('preset_url');
  if (presetInput) presetInput.value = url;
  document.querySelectorAll('.preset-card').forEach(function(card) { card.classList.remove('selected'); });
  element.classList.add('selected');

  // Clear file input
  var fileInput = document.getElementById('image_file');
  if (fileInput) fileInput.value = '';

  var previewBox = document.getElementById('imagePreview');
  var previewImg = document.getElementById('previewImg');
  var dropzoneContent = document.getElementById('dropzoneContent') || document.querySelector('.dropzone-content') || document.querySelector('.dropzone-label');
  var dropzone = document.getElementById('dropzone');

  if (previewImg && previewBox) {
    previewImg.src = url;
    previewBox.classList.remove('d-none');
    if (dropzoneContent) dropzoneContent.classList.add('d-none');
    if (dropzone) dropzone.classList.add('has-preview');
  }
}

// ============================================================
// Top Navigation Search & Mobile Drawer
// ============================================================
document.addEventListener('DOMContentLoaded', function() {
  // Top nav search popover
  var searchTrigger = document.getElementById('navSearchTrigger');
  var searchBar = document.getElementById('navSearchBar');
  var searchClose = document.getElementById('navSearchClose');

  if (searchTrigger && searchBar) {
    searchTrigger.addEventListener('click', function(e) {
      e.stopPropagation();
      searchBar.classList.toggle('active');
      if (searchBar.classList.contains('active')) {
        var input = searchBar.querySelector('input');
        if (input) input.focus();
      }
    });

    if (searchClose) {
      searchClose.addEventListener('click', function(e) {
        e.stopPropagation();
        searchBar.classList.remove('active');
      });
    }

    document.addEventListener('click', function(e) {
      if (!searchBar.contains(e.target) && e.target !== searchTrigger && !searchTrigger.contains(e.target)) {
        searchBar.classList.remove('active');
      }
    });
  }

  // Top nav notifications dropdown
  var notifTrigger = document.getElementById('navNotifTrigger');
  var notifDropdown = document.getElementById('navNotifDropdown');
  var notifDot = document.getElementById('navNotifDot');
  var btnClearNotifs = document.getElementById('btnClearNotifs');

  if (notifTrigger && notifDropdown) {
    // Check if user has previously marked all notifications as read
    try {
      if (localStorage.getItem('wearlytics_notifs_read') === 'true') {
        if (notifDot) notifDot.style.display = 'none';
        notifTrigger.classList.remove('has-dot');
      }
    } catch (e) {}

    notifTrigger.addEventListener('click', function(e) {
      e.stopPropagation();
      var isOpen = notifDropdown.classList.contains('show');
      
      // Close search bar if open
      if (searchBar) searchBar.classList.remove('active');

      if (!isOpen) {
        notifDropdown.classList.add('show');
        notifTrigger.setAttribute('aria-expanded', 'true');
      } else {
        notifDropdown.classList.remove('show');
        notifTrigger.setAttribute('aria-expanded', 'false');
      }
    });

    if (btnClearNotifs) {
      btnClearNotifs.addEventListener('click', function(e) {
        e.stopPropagation();
        if (notifDot) notifDot.style.display = 'none';
        notifTrigger.classList.remove('has-dot');
        try {
          localStorage.setItem('wearlytics_notifs_read', 'true');
        } catch (err) {}
        btnClearNotifs.textContent = 'All caught up ✓';
        btnClearNotifs.style.opacity = '0.7';
        btnClearNotifs.style.pointerEvents = 'none';
      });
    }

    document.addEventListener('click', function(e) {
      if (!notifDropdown.contains(e.target) && e.target !== notifTrigger && !notifTrigger.contains(e.target)) {
        notifDropdown.classList.remove('show');
        notifTrigger.setAttribute('aria-expanded', 'false');
      }
    });
  }

  // Mobile drawer toggle
  var mobileToggle = document.getElementById('mobileMenuToggle');
  var mobileDrawer = document.getElementById('mobileDrawer');
  if (mobileToggle && mobileDrawer) {
    mobileToggle.addEventListener('click', function() {
      mobileDrawer.classList.toggle('active');
    });
  }
});


