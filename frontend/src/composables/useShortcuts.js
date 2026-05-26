import { onMounted, onUnmounted } from 'vue'

export function useShortcuts(handlers = {}) {
  function onKeyDown(e) {
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.tagName === 'SELECT') return
    if (e.ctrlKey && e.key === 'n') { e.preventDefault(); handlers.newItem?.() }
    if (e.key === '/' && !e.ctrlKey && !e.metaKey) { e.preventDefault(); handlers.focusSearch?.() }
    if (e.key === 'Escape') { handlers.closeModal?.() }
  }

  onMounted(() => document.addEventListener('keydown', onKeyDown))
  onUnmounted(() => document.removeEventListener('keydown', onKeyDown))
}
