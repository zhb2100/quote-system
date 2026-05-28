import { ref, computed } from 'vue'

const BASE_URL = import.meta.env.BASE_URL === '/' ? '' : import.meta.env.BASE_URL.replace(/\/$/, '')
const authToken = ref(localStorage.getItem('quote_token') || '')
const currentUser = ref(null)
const registrationOpen = ref(true)

export { BASE_URL }

export function useApi() {
  const loggedIn = computed(() => !!authToken.value)
  const admin = computed(() => currentUser.value?.role === 'admin')

  function setToken(token) {
    authToken.value = token
    if (token) localStorage.setItem('quote_token', token)
    else localStorage.removeItem('quote_token')
  }

  function isLoggedIn() { return loggedIn.value }
  function isAdmin() { return admin.value }

  function _buildOpts(method, body) {
    const isFormData = body instanceof FormData
    const headers = isFormData
      ? { Accept: 'application/json' }
      : { 'Content-Type': 'application/json', Accept: 'application/json' }
    if (authToken.value) headers['Authorization'] = 'Bearer ' + authToken.value
    const opts = { method, headers }
    if (body) opts.body = isFormData ? body : JSON.stringify(body)
    return opts
  }

  function _handle401() {
    setToken('')
    currentUser.value = null
  }

  async function api(url, method = 'GET', body = null, timeoutMs = 0) {
    const opts = _buildOpts(method, body)
    let timeoutId = null
    if (timeoutMs > 0) {
      const controller = new AbortController()
      opts.signal = controller.signal
      timeoutId = setTimeout(() => controller.abort(), timeoutMs)
    }

    let r
    try {
      r = await fetch(BASE_URL + url, opts)
    } finally {
      if (timeoutId !== null) clearTimeout(timeoutId)
    }

    if (r.status === 401) { _handle401(); return { error: '请先登录' } }
    if (r.status === 204) return null

    const ct = r.headers.get('Content-Type') || ''
    if (!ct.includes('application/json')) {
      if (!r.ok) throw new Error(`HTTP ${r.status}`)
      return r
    }

    const data = await r.json()
    // 确保非 2xx 响应始终有 error 字段
    if (!r.ok && !data.error) data.error = `HTTP ${r.status}`
    return data
  }

  return {
    api, authToken, currentUser, registrationOpen,
    setToken, isLoggedIn, isAdmin,
    loggedIn, admin,
  }
}
