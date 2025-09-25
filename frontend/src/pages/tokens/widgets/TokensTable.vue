<script setup lang="ts">
import { defineVaDataTableColumns, useModal } from 'vuestic-ui'
import { Token } from '../types'
import { PropType, computed, toRef } from 'vue'
import { Pagination, Sorting } from '../composables/useTokens'
import { useVModel } from '@vueuse/core'

const columns = defineVaDataTableColumns([
  { label: '토큰 ID', key: 'token_id', sortable: true },
  { label: '설명', key: 'description', sortable: true },
  { label: '생성일', key: 'created_at', sortable: true },
  { label: '사용 횟수', key: 'usage_count', sortable: true },
  { label: '마지막 사용', key: 'last_used', sortable: true },
  { label: '활성화', key: 'is_active', sortable: true },
  { label: ' ', key: 'actions', align: 'right' },
])

const props = defineProps({
  tokens: {
    type: Array as PropType<Token[]>,
    required: true,
  },
  loading: { type: Boolean, default: false },
  pagination: { type: Object as PropType<Pagination>, required: true },
  sortBy: { type: String as PropType<Sorting['sortBy']>, required: true },
  sortingOrder: { type: String as PropType<Sorting['sortingOrder']>, default: null },
})

const emit = defineEmits<{
  (event: 'revoke-token', token: Token): void
  (event: 'update:sortBy', sortBy: Sorting['sortBy']): void
  (event: 'update:sortingOrder', sortingOrder: Sorting['sortingOrder']): void
  (event: 'update:pagination', pagination: Pagination): void
}>()

const tokens = toRef(props, 'tokens')
const sortByVModel = useVModel(props, 'sortBy', emit)
const sortingOrderVModel = useVModel(props, 'sortingOrder', emit)

const totalPages = computed(() => Math.ceil(props.pagination.total / props.pagination.perPage))

const { confirm } = useModal()

const onTokenRevoke = async (token: Token) => {
  const agreed = await confirm({
    title: '토큰 비활성화',
    message: `정말로 "${token.token_id}" 토큰을 비활성화하시겠습니까?`,
    okText: '비활성화',
    cancelText: '취소',
    size: 'small',
    maxWidth: '380px',
  })

  if (agreed) {
    emit('revoke-token', token)
  }
}

const formatDate = (dateString: string | undefined) => {
  if (!dateString) return '-'
  return new Date(dateString).toLocaleString('ko-KR')
}

const copyToClipboard = async (text: string) => {
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text)
    } else {
      // Fallback for older browsers or non-secure contexts
      const textArea = document.createElement('textarea')
      textArea.value = text
      textArea.style.position = 'fixed'
      textArea.style.left = '-999999px'
      textArea.style.top = '-999999px'
      document.body.appendChild(textArea)
      textArea.focus()
      textArea.select()
      document.execCommand('copy')
      textArea.remove()
    }
    // You can add a toast notification here if needed
    console.log('API 키가 클립보드에 복사되었습니다')
  } catch (err) {
    console.error('클립보드 복사 실패:', err)
  }
}

// const formatApiKey = (apiKey: string) => {
//   if (apiKey.length <= 8) return apiKey
//   return `${apiKey.substring(0, 4)}...${apiKey.substring(apiKey.length - 4)}`
// }
</script>

<template>
  <VaDataTable
    :sorting-order="sortingOrderVModel"
    :columns="columns"
    :items="tokens"
    :loading="loading"
    :no-data-html="'토큰이 없습니다'"
    @update:sortBy="sortByVModel = $event"
    @update:sortingOrder="sortingOrderVModel = $event"
  >
    <template #cell(token_id)="{ rowData }">
      <div class="flex items-center gap-2 max-w-[230px]">
        <VaIcon name="vpn_key" size="small" color="primary" />
        <span class="truncate font-medium">{{ rowData.token_id }}</span>
      </div>
    </template>

    <template #cell(description)="{ rowData }">
      <div class="max-w-[200px]">
        <span class="truncate" :title="rowData.description">{{ rowData.description }}</span>
      </div>
    </template>

    <template #cell(created_at)="{ rowData }">
      <span class="text-sm">{{ formatDate(rowData.created_at) }}</span>
    </template>

    <template #cell(usage_count)="{ rowData }">
      <VaBadge :text="(rowData.usage_count || 0).toString()" color="info" />
    </template>

    <template #cell(last_used)="{ rowData }">
      <span class="text-sm">{{ formatDate(rowData.last_used) }}</span>
    </template>

    <template #cell(is_active)="{ rowData }">
      <VaBadge :text="rowData.is_active ? '활성' : '비활성'" :color="rowData.is_active ? 'success' : 'danger'" />
    </template>

    <template #cell(actions)="{ rowData }">
      <div class="flex gap-2 justify-end">
        <VaButton
          v-if="rowData.is_active"
          preset="plain"
          icon="block"
          color="danger"
          size="small"
          title="토큰 비활성화"
          @click="onTokenRevoke(rowData)"
        />
        <VaButton
          preset="plain"
          icon="content_copy"
          color="primary"
          size="small"
          title="API 키 복사 (보안상 해시값만 표시)"
          @click="copyToClipboard(rowData.api_key_hash)"
          disabled
        />
      </div>
    </template>
  </VaDataTable>

  <div class="flex flex-col-reverse md:flex-row gap-2 justify-between items-center py-2">
    <div>
      <b>{{ pagination.total }}</b>
      개 중
      <b>{{ Math.min(pagination.perPage, pagination.total) }}</b>
      개 표시
    </div>

    <VaPagination
      :model-value="pagination.page"
      buttons-preset="secondary"
      :pages="totalPages"
      :visible-pages="5"
      :boundary-links="false"
      :direction-links="false"
      @update:modelValue="$emit('update:pagination', { ...pagination, page: $event })"
    />
  </div>
</template>
