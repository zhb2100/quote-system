<script setup>
/**
 * PaginationBar — 通用分页条组件
 * 消除 QuotesView / AdminView 三处完全相同的分页 HTML
 */
defineProps({
  currentPage: { type: Number, required: true },
  totalPages:  { type: Number, required: true },
  pageNumbers: { type: Array,  required: true },
})
const emit = defineEmits(['go-page'])
</script>

<template>
  <nav v-if="totalPages > 1" class="mt-3" aria-label="分页导航">
    <ul class="pagination pagination-modern justify-content-center mb-0">
      <li class="page-item" :class="{ disabled: currentPage <= 1 }">
        <a class="page-link" @click="emit('go-page', 1)" title="首页" role="button">
          <i class="bi bi-chevron-double-left"></i>
        </a>
      </li>
      <li class="page-item" :class="{ disabled: currentPage <= 1 }">
        <a class="page-link" @click="emit('go-page', currentPage - 1)" role="button">上一页</a>
      </li>
      <li v-for="p in pageNumbers" :key="p"
          class="page-item" :class="{ active: p === currentPage }">
        <a class="page-link" @click="emit('go-page', p)" role="button">{{ p }}</a>
      </li>
      <li class="page-item" :class="{ disabled: currentPage >= totalPages }">
        <a class="page-link" @click="emit('go-page', currentPage + 1)" role="button">下一页</a>
      </li>
      <li class="page-item" :class="{ disabled: currentPage >= totalPages }">
        <a class="page-link" @click="emit('go-page', totalPages)" title="末页" role="button">
          <i class="bi bi-chevron-double-right"></i>
        </a>
      </li>
    </ul>
  </nav>
</template>
