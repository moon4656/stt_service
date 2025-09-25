<script setup lang="ts">
import { ref, watchEffect } from 'vue'
import { useI18n } from 'vue-i18n'
import TokensTable from './widgets/TokensTable.vue'
import CreateTokenForm from './widgets/CreateTokenForm.vue'
import { Token, TokenCreate } from './types'
import { useTokens } from './composables/useTokens'
import { useModal, useToast } from 'vuestic-ui'

const { t } = useI18n()

const doShowCreateTokenModal = ref(false)
const createdTokenInfo = ref<{ api_key: string; token_id: string } | null>(null)
const doShowTokenInfoModal = ref(false)

const { tokens, isLoading, filters, sorting, pagination, error, ...tokensApi } = useTokens()

const showCreateTokenModal = () => {
  doShowCreateTokenModal.value = true
}

const { init: notify } = useToast()

watchEffect(() => {
  if (error.value) {
    notify({
      message: error.value.message,
      color: 'danger',
    })
  }
})

const onTokenSaved = async (tokenData: TokenCreate) => {
  try {
    const result = await tokensApi.create(tokenData)
    if (!error.value && result) {

      // 모달 닫기
      doShowCreateTokenModal.value = false

      // 토큰 목록 새로고침
      // await tokensApi.fetch()

      // API 키를 localStorage에 저장
      // const apiKeyData = {
      //   api_key: result.api_key,
      //   token_id: tokenData.token_id,
      //   created_at: new Date().toISOString(),
      //   is_active: true
      // }

      // 기존 API 키 목록 가져오기
      // const existingKeys = JSON.parse(localStorage.getItem('api_key') || '[]')
      
      // // 새 API 키 추가
      // existingKeys.push(apiKeyData)
      
      // // localStorage에 저장
      // localStorage.setItem('api_key', JSON.stringify(existingKeys))
      
      // // 현재 활성 API 키로 설정 (STT 변환 시 사용)
      // localStorage.setItem('current_api_key', result.api_key)

      notify({
        message: `토큰 "${tokenData.token_id}"이 성공적으로 생성되었습니다`,
        color: 'success',
      })

      // Show the created token info
      createdTokenInfo.value = {
        api_key: result.api_key,
        token_id: tokenData.token_id,
      }
      doShowCreateTokenModal.value = false
      doShowTokenInfoModal.value = true
    }
  } catch (err: any) {
    console.error('토큰 생성 오류:', err)
    
    // 서버 에러 메시지 처리
    if (err.response?.data?.detail) {
      if (err.response.data.detail.includes('이미 존재')) {
        notify({
          message: '이미 존재하는 토큰 이름입니다. 다른 이름을 사용해주세요.',
          color: 'danger'
        })
      } else {
        notify({
          message: err.response.data.detail,
          color: 'danger'
        })
      }
    } else if (err.message?.includes('인증')) {
      // 인증 관련 에러는 이미 useTokens에서 처리됨
    } else {
      notify({
        message: '토큰 생성 중 오류가 발생했습니다.',
        color: 'danger'
      })
    }
  }
}

const onTokenRevoke = async (token: Token) => {
  try {
    await tokensApi.revoke({ api_key_hash: token.api_key_hash })
    if (!error.value) {
      notify({
        message: `토큰 "${token.token_id}"이 비활성화되었습니다`,
        color: 'success',
      })
    }
  } catch (err) {
    // Error is already handled in the composable
  }
}

const createFormRef = ref()

const { confirm } = useModal()

const beforeCreateFormModalClose = async (hide: () => unknown) => {
  if (createFormRef.value?.isFormHasUnsavedChanges) {
    const agreed = await confirm({
      maxWidth: '380px',
      message: '저장되지 않은 변경사항이 있습니다. 정말로 닫으시겠습니까?',
      size: 'small',
    })
    if (agreed) {
      hide()
    }
  } else {
    hide()
  }
}

const copyToClipboard = async (text: string) => {
  try {
    await navigator.clipboard.writeText(text)
    notify({
      message: 'API 키가 클립보드에 복사되었습니다',
      color: 'success',
    })
  } catch (err) {
    notify({
      message: 'API 키 복사에 실패했습니다',
      color: 'danger',
    })
  }
}
</script>

<template>
  <h1 class="page-title">{{ t('menu.tokens') }}</h1>

  <VaCard>
    <VaCardContent>
      <div class="flex flex-col md:flex-row gap-2 mb-2 justify-between">
        <div class="flex flex-col md:flex-row gap-2 justify-start">
          <VaButtonToggle
            v-model="filters.isActive"
            color="background-element"
            border-color="background-element"
            :options="[
              { label: 'Active', value: true },
              { label: 'Inactive', value: false },
            ]"
          />
          <VaInput v-model="filters.search" placeholder="Search">
            <template #prependInner>
              <VaIcon name="search" color="secondary" size="small" />
            </template>
          </VaInput>
        </div>
        <div class="flex gap-2">
          <VaButton icon="vpn_key" @click="showCreateTokenModal">API 키 발행</VaButton>
          <!-- <VaButton 
            icon="vpn_key" 
            preset="secondary"
            @click="$router.push({ name: 'create-token' })"
          >
            API 키 발행
          </VaButton> -->
        </div>
      </div>

      <TokensTable
        v-model:sort-by="sorting.sortBy"
        v-model:sorting-order="sorting.sortingOrder"
        :tokens="tokens"
        :loading="isLoading"
        :pagination="pagination"
        @revokeToken="onTokenRevoke"
      />
    </VaCardContent>
  </VaCard>

  <!-- Create Token Modal -->
  <VaModal
    v-slot="{ cancel }"
    v-model="doShowCreateTokenModal"
    size="small"
    mobile-fullscreen
    close-button
    hide-default-actions
    :before-cancel="beforeCreateFormModalClose"
  >
    <h1 class="va-h5 mb-4">새로 등록하기</h1>
    <CreateTokenForm
      ref="createFormRef"
      save-button-label="등록하기"
      @close="cancel"
      @save="
        (tokenData) => {
          onTokenSaved(tokenData)
        }
      "
    />
  </VaModal>

  <!-- Token Info Modal -->
  <VaModal v-model="doShowTokenInfoModal" size="small" mobile-fullscreen close-button hide-default-actions>
    <div class="text-center">
      <VaIcon name="check_circle" size="large" color="success" class="mb-4" />
      <h2 class="va-h5 mb-4">토큰이 생성되었습니다!</h2>

      <div class="bg-gray-50 p-4 rounded-lg mb-4">
        <div class="text-sm text-gray-600 mb-2">API 키</div>
        <div class="font-mono text-sm break-all bg-white p-2 rounded border">
          {{ createdTokenInfo?.api_key }}
        </div>
        <VaButton
          class="mt-2"
          size="small"
          preset="secondary"
          icon="content_copy"
          @click="copyToClipboard(createdTokenInfo?.api_key || '')"
        >
          복사
        </VaButton>
      </div>

      <div class="text-sm text-orange-600 mb-4">⚠️ 이 API 키는 다시 표시되지 않습니다. 안전한 곳에 저장해주세요.</div>

      <VaButton @click="doShowTokenInfoModal = false">확인</VaButton>
    </div>
  </VaModal>
</template>
