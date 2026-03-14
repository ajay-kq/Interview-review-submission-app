document.addEventListener('DOMContentLoaded', () => {

  // Auto suggest API buttons
  const suggestButtons = document.querySelectorAll('.ai-suggest-btn');
  suggestButtons.forEach(btn => {
      btn.addEventListener('click', async (e) => {
          e.preventDefault();
          const targetId = btn.getAttribute('data-target');
          const targetElem = document.getElementById(targetId);
          const candidateName = document.getElementById('candidate_name')?.value || '';
          const position = document.getElementById('position')?.value || '';
          
          const csrfToken = document.getElementById('csrf_token') ? document.getElementById('csrf_token').value : '';

          btn.innerHTML = 'Generating...';
          btn.disabled = true;

          try {
              const response = await fetch('/ai_suggest', {
                  method: 'POST',
                  headers: {
                      'Content-Type': 'application/json',
                      'X-CSRFToken': csrfToken
                  },
                  body: JSON.stringify({
                      field_name: targetId,
                      candidate_name: candidateName,
                      position: position
                  })
              });
              const data = await response.json();
              if (data.suggestion) {
                  // Typewriter effect
                  targetElem.value = "";
                  let i = 0;
                  const text = data.suggestion;
                  function typeWriter() {
                      if (i < text.length) {
                          targetElem.value += text.charAt(i);
                          i++;
                          setTimeout(typeWriter, 10);
                      } else {
                          btn.innerHTML = '✨ Generated';
                          setTimeout(() => {
                              btn.innerHTML = '✨ AI Suggest';
                              btn.disabled = false;
                          }, 2000);
                      }
                  }
                  typeWriter();
              }
          } catch (error) {
              console.error("AI Error", error);
              btn.innerHTML = '✨ AI Suggest';
              btn.disabled = false;
          }
      });
  });

  // Star rating logic interaction
  const starContainers = document.querySelectorAll('.stars');
  starContainers.forEach(container => {
      const stars = container.querySelectorAll('.star');
      const key = stars[0]?.getAttribute('data-key');
      const hiddenInput = document.getElementById(key + '_rating_val');

      stars.forEach(star => {
          star.addEventListener('mouseover', () => {
              const val = parseInt(star.getAttribute('data-value'));
              stars.forEach(s => {
                  if (parseInt(s.getAttribute('data-value')) <= val) {
                      s.classList.add('hover');
                  } else {
                      s.classList.remove('hover');
                  }
              });
          });

          star.addEventListener('mouseout', () => {
              stars.forEach(s => s.classList.remove('hover'));
          });

          star.addEventListener('click', () => {
              const val = parseInt(star.getAttribute('data-value'));
              hiddenInput.value = val;
              
              stars.forEach(s => {
                  if (parseInt(s.getAttribute('data-value')) <= val) {
                      s.classList.add('active');
                      s.setAttribute('fill', 'currentColor');
                  } else {
                      s.classList.remove('active');
                      s.setAttribute('fill', 'none');
                  }
              });
          });
      });
  });

});

// Global Toggle for Skill ratings visibility
function toggleRating(skillKey) {
  const cb = document.getElementById(skillKey + '_selected');
  const div = document.getElementById('rating_' + skillKey);
  const hiddenInput = document.getElementById(skillKey + '_rating_val');
  
  if (cb && cb.checked) {
      div.style.display = 'flex';
      if (!hiddenInput.value || hiddenInput.value === '0') {
          const stars = div.querySelectorAll('.star');
          hiddenInput.value = '3';
          stars.forEach(s => {
              if (parseInt(s.getAttribute('data-value')) <= 3) {
                  s.classList.add('active');
                  s.setAttribute('fill', 'currentColor');
              } else {
                  s.classList.remove('active');
                  s.setAttribute('fill', 'none');
              }
          });
      }
  } else if (cb) {
      div.style.display = 'none';
      hiddenInput.value = '0';
      const stars = div.querySelectorAll('.star');
      stars.forEach(s => {
          s.classList.remove('active');
          s.setAttribute('fill', 'none');
      });
  }
}

// Mobile Sidebar Toggle
document.addEventListener('DOMContentLoaded', () => {
  const mobileMenuBtn = document.getElementById('mobileMenuBtn');
  const sidebar = document.getElementById('appSidebar');
  const sidebarOverlay = document.getElementById('sidebarOverlay');

  if (mobileMenuBtn && sidebar && sidebarOverlay) {
    function toggleSidebar() {
      sidebar.classList.toggle('mobile-hidden');
      sidebarOverlay.classList.toggle('active');
    }

    mobileMenuBtn.addEventListener('click', toggleSidebar);
    sidebarOverlay.addEventListener('click', toggleSidebar);
  }

  // Danger Zone Toggle
  const toggleDangerZoneBtn = document.getElementById('toggleDangerZoneBtn');
  const dangerZoneContent = document.getElementById('dangerZoneContent');

  if (toggleDangerZoneBtn && dangerZoneContent) {
    toggleDangerZoneBtn.addEventListener('click', () => {
      const isHidden = dangerZoneContent.classList.toggle('active');
      toggleDangerZoneBtn.textContent = isHidden ? 'Hide Danger Zone' : 'Unlock Danger Zone';
      
      if (isHidden) {
          toggleDangerZoneBtn.classList.replace('btn-outline', 'btn-danger');
      } else {
          toggleDangerZoneBtn.classList.replace('btn-danger', 'btn-outline');
      }
    });
  }
});