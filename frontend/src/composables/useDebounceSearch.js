/**
 * useDebounceSearch — 带 IME 输入法防抖的搜索 composable
 * 消除 QuotesView 和 AdminView 中两处相同的防抖搜索逻辑
 */
import { ref } from 'vue'

export function useDebounceSearch(onSearch, delay = 400) {
  const searchTerm = ref('')
  const isComposing = ref(false)
  let timer = null

  function onCompositionStart() {
    isComposing.value = true
  }

  function onCompositionEnd(e) {
    isComposing.value = false
    _trigger(e.target.value)
  }

  function onInput(e) {
    const val = typeof e === 'string' ? e : e.target.value
    if (!isComposing.value) _trigger(val)
  }

  function _trigger(val) {
    clearTimeout(timer)
    timer = setTimeout(() => {
      searchTerm.value = val
      onSearch(val)
    }, delay)
  }

  function clear() {
    clearTimeout(timer)
    searchTerm.value = ''
    onSearch('')
  }

  return { searchTerm, isComposing, onInput, onCompositionStart, onCompositionEnd, clear }
}
