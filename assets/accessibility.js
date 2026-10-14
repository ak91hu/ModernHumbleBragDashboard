/* Keyboard focus management for the app's two dialogs. */
(() => {
  let active = null, previousFocus = null;
  const visible = el => el && el.style.display === 'flex';
  const focusables = el => [...el.querySelectorAll('button:not(:disabled),a[href],input:not(:disabled),[tabindex="0"]')].filter(node => node.getClientRects().length);
  const update = () => {
    const dialog = ['goal-dialog', 'detail-dialog'].map(id => document.getElementById(id)).find(visible);
    if (dialog && active !== dialog) {
      if (!active) previousFocus = document.activeElement;
      active = dialog;
      document.body.style.overflow = 'hidden';
      requestAnimationFrame(() => focusables(dialog)[0]?.focus());
    } else if (!dialog && active) {
      active = null;
      document.body.style.overflow = '';
      if (previousFocus?.isConnected) previousFocus.focus();
      else document.getElementById('main-content')?.focus();
    }
    document.querySelectorAll('.nav-item').forEach(node => {
      if (node.classList.contains('active')) node.setAttribute('aria-current', 'page');
      else node.removeAttribute('aria-current');
    });
  };
  document.addEventListener('keydown', event => {
    if (!active) return;
    if (event.key === 'Escape') {
      event.preventDefault();
      active.querySelector('#cancel-goals,#close-detail')?.click();
    } else if (event.key === 'Tab') {
      const nodes = focusables(active), first = nodes[0], last = nodes.at(-1);
      if (!first) return;
      if (event.shiftKey && (document.activeElement === first || !active.contains(document.activeElement))) {event.preventDefault();last.focus();}
      else if (!event.shiftKey && (document.activeElement === last || !active.contains(document.activeElement))) {event.preventDefault();first.focus();}
    }
  });
  document.addEventListener('click', event => {
    if (event.target.classList.contains('modal-overlay')) event.target.querySelector('#cancel-goals,#close-detail')?.click();
  });
  new MutationObserver(update).observe(document.documentElement, {subtree:true,childList:true,attributes:true,attributeFilter:['style','class']});
})();
