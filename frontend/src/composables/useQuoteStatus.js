/**
 * useQuoteStatus — 报价单状态颜色/CSS类统一映射
 * 消除原来散落在 QuotesView / DashboardView / ProjectDetailView 四处的重复定义
 */

/** Bootstrap badge CSS 类映射 */
export const STATUS_CSS = {
  '项目报价中':       'bg-info',
  '项目已报价未付款': 'bg-warning text-dark',
  '项目生产中':       'bg-primary',
  '项目完结':         'bg-success',
  '项目返工':         'bg-warning',
  '项目终止':         'bg-danger',
}

/** 图表/流程图十六进制颜色映射 */
export const STATUS_HEX = {
  '项目报价中':       '#0dcaf0',
  '项目已报价未付款': '#ffc107',
  '项目生产中':       '#0d6efd',
  '项目完结':         '#198754',
  '项目返工':         '#fd7e14',
  '项目终止':         '#dc3545',
}

/** 所有状态的有序列表（用于遍历） */
export const STATUS_ORDER = [
  '项目报价中',
  '项目已报价未付款',
  '项目生产中',
  '项目完结',
  '项目返工',
  '项目终止',
]

export function useQuoteStatus() {
  /** 返回 Bootstrap badge class 字符串 */
  function statusClass(s) {
    return STATUS_CSS[s] || 'bg-secondary'
  }

  /** 返回显示文字（空时显示破折号） */
  function statusBadge(s) {
    return s || '—'
  }

  /** 返回十六进制颜色（用于图表/流程图） */
  function statusColor(s) {
    return STATUS_HEX[s] || '#6c757d'
  }

  return { statusClass, statusBadge, statusColor, STATUS_CSS, STATUS_HEX, STATUS_ORDER }
}
