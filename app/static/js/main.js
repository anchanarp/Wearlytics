/* Wearlytics Client JavaScript */

document.addEventListener('DOMContentLoaded', () => {
  // Auto-dismiss alerts after 5 seconds
  setTimeout(() => {
    const alerts = document.querySelectorAll('.alert-custom');
    alerts.forEach(alert => {
      alert.style.opacity = '0';
      alert.style.transition = 'opacity 0.5s ease';
      setTimeout(() => alert.remove(), 500);
    });
  }, 5000);
});

// Image Preview for Clothing Upload
function previewUploadImage(input) {
  const previewBox = document.getElementById('imagePreview');
  const previewImg = document.getElementById('previewImg');

  if (input.files && input.files[0]) {
    const reader = new FileReader();
    reader.onload = function(e) {
      previewImg.src = e.target.result;
      previewBox.classList.remove('d-none');
    };
    reader.readAsDataURL(input.files[0]);
    // Clear preset selection if custom image uploaded
    document.getElementById('preset_url').value = '';
    document.querySelectorAll('.preset-card').forEach(card => card.classList.remove('selected'));
  }
}

// Preset Selection for Clothing Upload
function selectPreset(url, element) {
  document.getElementById('preset_url').value = url;
  document.querySelectorAll('.preset-card').forEach(card => card.classList.remove('selected'));
  element.classList.add('selected');

  // Clear file input
  const fileInput = document.getElementById('image_file');
  if (fileInput) fileInput.value = '';
  
  const previewBox = document.getElementById('imagePreview');
  const previewImg = document.getElementById('previewImg');
  if (previewImg && previewBox) {
    previewImg.src = url;
    previewBox.classList.remove('d-none');
  }
}
