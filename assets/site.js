const menuButton = document.querySelector('.menu');
const navigation = document.querySelector('.links');
if (menuButton && navigation) {
  const closeMenu = () => {
    navigation.classList.remove('open');
    menuButton.setAttribute('aria-expanded', 'false');
  };
  menuButton.addEventListener('click', () => {
    const open = navigation.classList.toggle('open');
    menuButton.setAttribute('aria-expanded', String(open));
  });
  navigation.addEventListener('click', event => {
    if (event.target.closest('a')) closeMenu();
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape') closeMenu();
  });
}

// Track production intent and confirmed inquiries, without any visitor-entered values.
function trackEvent(name, params) {
  try {
    if (['rushlo.com', 'www.rushlo.com'].includes(window.location.hostname) && typeof window.gtag === 'function') {
      window.gtag('event', name, params);
    }
  } catch (_) {
    // Analytics must never prevent an inquiry from sending.
  }
}

document.addEventListener('click', event => {
  const link = event.target.closest('a[href]');
  if (!link) return;
  const destination = new URL(link.href, window.location.href);
  if (destination.origin !== window.location.origin) return;
  if (destination.pathname === '/contact.html' || link.hasAttribute('data-inquiry-cta')) {
    trackEvent('contact_click', {
      link_location: link.closest('main') ? 'main' : link.closest('header') ? 'header' : 'footer',
      source_path: window.location.pathname,
      destination_path: destination.pathname
    });
  }
});

const inquiryForm = document.querySelector('#contact');
if (inquiryForm) {
  const service = inquiryForm.dataset.service || 'general';
  let submitting = false;
  inquiryForm.addEventListener('input', () => {
    trackEvent('inquiry_start', { form_id: 'contact', service });
  }, { once: true });
  inquiryForm.addEventListener('submit', async event => {
    event.preventDefault();
    if (submitting || !inquiryForm.reportValidity()) return;
    const status = inquiryForm.querySelector('#status');
    const button = inquiryForm.querySelector('button[type="submit"]');
    const trap = inquiryForm.querySelector('input[name="website"]');
    const buttonLabel = button ? button.textContent : '';
    if (trap && trap.value) {
      inquiryForm.reset();
      if (status) status.textContent = 'Thanks — your message has been received.';
      return;
    }
    submitting = true;
    if (button) { button.disabled = true; button.textContent = 'Sending…'; }
    if (status) status.textContent = 'Sending your message…';
    try {
      const payload = new FormData(inquiryForm);
      payload.set('inquiry_page', window.location.pathname);
      payload.set('service', service);
      const response = await fetch(inquiryForm.action, {
        method: 'POST', body: payload, headers: { Accept: 'application/json' }
      });
      if (response.ok) {
        trackEvent('generate_lead', { form_id: 'contact', service, lead_source: 'website_inquiry' });
        inquiryForm.reset();
        if (status) status.textContent = 'Thanks — your inquiry has been sent. Josh will respond within one business day.';
      } else {
        if (status) status.textContent = 'We couldn’t send your message. Please try again in a moment. Your details are still in the form.';
      }
    } catch (_) {
      if (status) status.textContent = 'We couldn’t send your message. Please check your connection and try again. Your details are still in the form.';
    } finally {
      submitting = false;
      if (button) { button.disabled = false; button.textContent = buttonLabel; }
    }
  });
}
