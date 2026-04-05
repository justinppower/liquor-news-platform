// ===================================
// Liquor News Magazine - Main JavaScript
// ===================================

(function() {
  'use strict';

  // ===================================
  // Mobile Menu Toggle
  // ===================================

  const hamburger = document.querySelector('.hamburger');
  const siteNav = document.querySelector('.site-nav');

  if (hamburger) {
    hamburger.addEventListener('click', function() {
      hamburger.classList.toggle('active');
      siteNav.classList.toggle('active');
    });

    // Close menu when clicking on a link
    const navLinks = siteNav.querySelectorAll('a');
    navLinks.forEach(link => {
      link.addEventListener('click', function() {
        hamburger.classList.remove('active');
        siteNav.classList.remove('active');
      });
    });
  }

  // ===================================
  // Newsletter Form Validation
  // ===================================

  const newsletterForms = document.querySelectorAll('.newsletter-form');

  newsletterForms.forEach(form => {
    const input = form.querySelector('input[type="email"]');
    const button = form.querySelector('button');
    const messageContainer = document.createElement('div');
    messageContainer.className = 'form-message';
    form.appendChild(messageContainer);

    button.addEventListener('click', function(e) {
      e.preventDefault();

      const email = input.value.trim();
      const messageDiv = form.querySelector('.form-message');

      // Reset message
      messageDiv.classList.remove('success', 'error');
      messageDiv.textContent = '';

      // Simple email validation regex
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

      if (!email) {
        messageDiv.textContent = 'Please enter your email address.';
        messageDiv.classList.add('error');
        messageDiv.style.display = 'block';
        return;
      }

      if (!emailRegex.test(email)) {
        messageDiv.textContent = 'Please enter a valid email address.';
        messageDiv.classList.add('error');
        messageDiv.style.display = 'block';
        return;
      }

      // Success message
      messageDiv.textContent = 'Thank you for subscribing!';
      messageDiv.classList.add('success');
      messageDiv.style.display = 'block';
      input.value = '';

      // Optional: Clear success message after 4 seconds
      setTimeout(() => {
        messageDiv.style.display = 'none';
      }, 4000);
    });

    // Allow Enter key to submit
    input.addEventListener('keypress', function(e) {
      if (e.key === 'Enter') {
        button.click();
      }
    });
  });

  // ===================================
  // Sticky Sidebar Behavior
  // ===================================

  function initStickySidebar() {
    const sidebars = document.querySelectorAll('.sidebar-box');

    sidebars.forEach(sidebar => {
      const parentContainer = sidebar.closest('.main-content') || sidebar.parentElement;

      // Only apply sticky positioning on larger screens
      if (window.innerWidth > 1024) {
        sidebar.style.position = 'sticky';
        sidebar.style.top = '100px';
      } else {
        sidebar.style.position = 'static';
      }
    });
  }

  initStickySidebar();
  window.addEventListener('resize', initStickySidebar);

  // ===================================
  // Share Button - Copy to Clipboard
  // ===================================

  const shareButtons = document.querySelectorAll('.share-button');

  shareButtons.forEach(button => {
    // Twitter share
    if (button.classList.contains('twitter')) {
      button.addEventListener('click', function() {
        const url = window.location.href;
        const title = document.querySelector('h1')?.textContent || 'Check this out';
        const twitterUrl = `https://twitter.com/intent/tweet?text=${encodeURIComponent(title)}&url=${encodeURIComponent(url)}`;
        window.open(twitterUrl, '_blank', 'width=550,height=420');
      });
    }

    // Facebook share
    if (button.classList.contains('facebook')) {
      button.addEventListener('click', function() {
        const url = window.location.href;
        const facebookUrl = `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(url)}`;
        window.open(facebookUrl, '_blank', 'width=550,height=420');
      });
    }

    // LinkedIn share
    if (button.classList.contains('linkedin')) {
      button.addEventListener('click', function() {
        const url = window.location.href;
        const linkedinUrl = `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(url)}`;
        window.open(linkedinUrl, '_blank', 'width=550,height=420');
      });
    }

    // Copy link to clipboard
    if (button.classList.contains('copy-link')) {
      button.addEventListener('click', function(e) {
        e.preventDefault();
        const url = window.location.href;
        const tooltip = document.createElement('span');
        tooltip.textContent = 'Copied!';
        tooltip.style.position = 'absolute';
        tooltip.style.top = '-30px';
        tooltip.style.fontSize = '0.85rem';
        tooltip.style.color = '#22c55e';
        tooltip.style.whiteSpace = 'nowrap';
        tooltip.style.fontWeight = '600';

        button.style.position = 'relative';
        button.appendChild(tooltip);

        // Copy to clipboard
        navigator.clipboard.writeText(url).catch(() => {
          // Fallback for older browsers
          const textarea = document.createElement('textarea');
          textarea.value = url;
          document.body.appendChild(textarea);
          textarea.select();
          document.execCommand('copy');
          document.body.removeChild(textarea);
        });

        // Remove tooltip after 2 seconds
        setTimeout(() => {
          tooltip.remove();
        }, 2000);
      });
    }
  });

  // ===================================
  // Lazy Loading Images
  // ===================================

  const imageObserverOptions = {
    root: null,
    rootMargin: '50px',
    threshold: 0.01
  };

  const imageObserver = new IntersectionObserver(function(entries) {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const img = entry.target;

        // If data-src exists, use it; otherwise use src
        if (img.dataset.src) {
          img.src = img.dataset.src;
          img.removeAttribute('data-src');
        }

        // Add loaded class for fade-in effect
        img.classList.add('loaded');
        imageObserver.unobserve(img);
      }
    });
  }, imageObserverOptions);

  // Observe all images with data-src attribute
  const lazyImages = document.querySelectorAll('img[data-src]');
  lazyImages.forEach(img => {
    imageObserver.observe(img);
  });

  // ===================================
  // News Ticker Pause on Hover
  // ===================================

  const ticker = document.querySelector('.ticker-content');
  const tickerItems = document.querySelector('.ticker-items');

  if (ticker && tickerItems) {
    // Pause/resume animation on hover
    ticker.addEventListener('mouseenter', function() {
      tickerItems.style.animationPlayState = 'paused';
    });

    ticker.addEventListener('mouseleave', function() {
      tickerItems.style.animationPlayState = 'running';
    });
  }

  // ===================================
  // Article Card Interactions
  // ===================================

  const articleCards = document.querySelectorAll('.article-card');

  articleCards.forEach(card => {
    // Add keyboard navigation support
    const cardLink = card.querySelector('a');
    if (cardLink) {
      card.addEventListener('keypress', function(e) {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          cardLink.click();
        }
      });
    }
  });

  // ===================================
  // Smooth Scroll Support
  // ===================================

  // Check if browser supports smooth scroll, if not apply polyfill
  if (!('scrollBehavior' in document.documentElement.style)) {
    document.documentElement.style.scrollBehavior = 'auto';
  }

  // ===================================
  // Utility: Throttle Function
  // ===================================

  function throttle(func, wait) {
    let timeout;
    return function executedFunction(...args) {
      const later = () => {
        clearTimeout(timeout);
        func(...args);
      };
      clearTimeout(timeout);
      timeout = setTimeout(later, wait);
    };
  }

  // ===================================
  // Dynamic Image Loading Fallback
  // ===================================

  // If a lazy image fails to load, try without data-src
  document.addEventListener('error', function(e) {
    if (e.target.tagName === 'IMG' && !e.target.src) {
      if (e.target.dataset.src) {
        e.target.src = e.target.dataset.src;
      }
    }
  }, true);

  // ===================================
  // Accessibility: Skip to Content Link
  // ===================================

  const skipLink = document.querySelector('.skip-link');
  if (skipLink) {
    skipLink.addEventListener('click', function(e) {
      e.preventDefault();
      const target = document.querySelector(this.getAttribute('href'));
      if (target) {
        target.focus();
        target.tabIndex = -1;
      }
    });
  }

  // ===================================
  // Initialize on DOM Ready
  // ===================================

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() {
      // Any initialization that requires DOM to be fully loaded
    });
  }

})();
