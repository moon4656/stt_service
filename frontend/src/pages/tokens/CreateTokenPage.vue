<template>
  <div class="create-token-page">
    <VaCard>
      <VaCardTitle class="va-h4">
        <VaIcon name="vpn_key" class="mr-2" />
        새 API 토큰 등록
      </VaCardTitle>
      
      <VaCardContent>
        <div class="row">
          <div class="flex md6 lg4">
            <VaForm ref="form" @submit.prevent="handleSubmit">
              <div class="row">
                <div class="flex xs12">
                  <VaInput
                    v-model="formData.token_id"
                    label="토큰 이름"
                    placeholder="토큰 이름을 입력하세요"
                    :rules="tokenIdRules"
                    :error="!!errors.token_id"
                    :error-messages="errors.token_id"
                    required
                  />
                </div>
                
                <div class="flex xs12">
                  <VaTextarea
                    v-model="formData.description"
                    label="상세 정보"
                    placeholder="토큰에 대한 설명을 입력하세요"
                    :rules="descriptionRules"
                    :error="!!errors.description"
                    :error-messages="errors.description"
                    rows="4"
                  />
                </div>
                
                <div class="flex xs12">
                  <div class="d-flex justify-space-between">
                    <VaButton
                      preset="secondary"
                      @click="goBack"
                    >
                      취소
                    </VaButton>
                    
                    <VaButton
                      type="submit"
                      :loading="isLoading"
                      :disabled="!isFormValid"
                    >
                      API 키 발행
                    </VaButton>
                  </div>
                </div>
              </div>
            </VaForm>
          </div>
          
          <div class="flex md6 lg8">
            <VaCard color="info" class="mb-4">
              <VaCardContent>
                <VaIcon name="info" class="mr-2" />
                <strong>API 키 발행 안내</strong>
                <ul class="mt-2">
                  <li>토큰 이름은 고유해야 하며, 영문, 숫자, 하이픈(-), 언더스코어(_)만 사용 가능합니다.</li>
                  <li>발행된 API 키는 한 번만 표시되므로 안전한 곳에 보관하세요.</li>
                  <li>API 키는 STT 서비스 호출 시 인증에 사용됩니다.</li>
                </ul>
              </VaCardContent>
            </VaCard>
          </div>
        </div>
      </VaCardContent>
    </VaCard>

    <!-- API 키 발행 성공 모달 -->
    <VaModal
      v-model="showSuccessModal"
      title="API 키 발행 완료"
      size="medium"
      :close-button="false"
    >
      <div class="success-content">
        <div class="text-center mb-4">
          <VaIcon name="check_circle" color="success" size="4rem" />
          <h3 class="va-h5 mt-2">API 키가 성공적으로 발행되었습니다!</h3>
        </div>
        
        <VaAlert color="warning" class="mb-4">
          <VaIcon name="warning" class="mr-2" />
          <strong>중요:</strong> 이 API 키는 한 번만 표시됩니다. 안전한 곳에 복사하여 보관하세요.
        </VaAlert>
        
        <div class="api-key-display">
          <VaInput
            v-model="generatedApiKey"
            label="생성된 API 키"
            readonly
            class="mb-3"
          >
            <template #appendInner>
              <VaButton
                preset="plain"
                icon="content_copy"
                @click="copyApiKey"
                :color="copyButtonColor"
              />
            </template>
          </VaInput>
        </div>
        
        <div class="token-info">
          <p><strong>토큰 이름:</strong> {{ createdTokenInfo?.token_id }}</p>
          <p><strong>생성 시간:</strong> {{ new Date().toLocaleString('ko-KR') }}</p>
        </div>
      </div>
      
      <template #footer>
        <div class="d-flex justify-space-between w-100">
          <VaButton
            preset="secondary"
            @click="goToTokensList"
          >
            토큰 목록으로
          </VaButton>
          
          <VaButton
            @click="createAnother"
          >
            추가 생성
          </VaButton>
        </div>
      </template>
    </VaModal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useToast } from 'vuestic-ui'
import { useTokens } from './composables/useTokens'
import type { TokenCreate } from './types'

const router = useRouter()
const route = useRoute()
const { init: notify } = useToast()
const { create: createToken, isLoading, error } = useTokens()

// 폼 데이터
const formData = reactive<TokenCreate>({
  token_id: route.params.token_id as string || '',
  description: ''
})

// 에러 상태
const errors = reactive({
  token_id: '',
  description: ''
})

// 모달 상태
const showSuccessModal = ref(false)
const generatedApiKey = ref('')
const createdTokenInfo = ref<{ token_id: string; api_key: string } | null>(null)
const copyButtonColor = ref('primary')

// 폼 검증 규칙
const tokenIdRules = [
  (value: string) => !!value || '토큰 이름은 필수입니다.',
  (value: string) => value.length >= 3 || '토큰 이름은 최소 3자 이상이어야 합니다.',
  (value: string) => value.length <= 50 || '토큰 이름은 최대 50자까지 가능합니다.',
  (value: string) => /^[a-zA-Z0-9_-]+$/.test(value) || '영문, 숫자, 하이픈(-), 언더스코어(_)만 사용 가능합니다.'
]

const descriptionRules = [
  (value: string) => !value || value.length <= 500 || '설명은 최대 500자까지 가능합니다.'
]

// 폼 유효성 검사
const isFormValid = computed(() => {
  const isValid = formData.token_id.length >= 3 && 
         /^[a-zA-Z0-9_-]+$/.test(formData.token_id) &&
         formData.description.length <= 500
  console.log('Form validation:', {
    token_id: formData.token_id,
    token_id_length: formData.token_id.length,
    token_id_valid: /^[a-zA-Z0-9_-]+$/.test(formData.token_id),
    description_length: formData.description.length,
    isValid
  })
  return isValid
})

// 폼 제출 처리
const handleSubmit = async () => {
  console.log('handleSubmit called with formData:', formData)
  console.log('isFormValid:', isFormValid.value)
  console.log('isLoading:', isLoading.value)
  
  try {
    // 에러 초기화
    errors.token_id = ''
    errors.description = ''
    
    console.log('Calling createToken with:', formData)
    const result = await createToken(formData)
    
    if (result && !error.value) {
      generatedApiKey.value = result.api_key
      createdTokenInfo.value = {
        token_id: formData.token_id,
        api_key: result.api_key
      }
      showSuccessModal.value = true
      
      notify({
        message: `토큰 "${formData.token_id}"이 성공적으로 생성되었습니다.`,
        color: 'success'
      })
    }
  } catch (err: any) {
    console.error('토큰 생성 오류:', err)
    
    // 서버 에러 메시지 처리
    if (err.response?.data?.detail) {
      if (err.response.data.detail.includes('이미 존재')) {
        errors.token_id = '이미 존재하는 토큰 이름입니다.'
      } else {
        notify({
          message: err.response.data.detail,
          color: 'danger'
        })
      }
    } else {
      notify({
        message: '토큰 생성 중 오류가 발생했습니다.',
        color: 'danger'
      })
    }
  }
}

// API 키 복사
const copyApiKey = async () => {
  try {
    await navigator.clipboard.writeText(generatedApiKey.value)
    copyButtonColor.value = 'success'
    notify({
      message: 'API 키가 클립보드에 복사되었습니다.',
      color: 'success'
    })
    
    setTimeout(() => {
      copyButtonColor.value = 'primary'
    }, 2000)
  } catch (err) {
    notify({
      message: 'API 키 복사에 실패했습니다.',
      color: 'danger'
    })
  }
}

// 뒤로 가기
const goBack = () => {
  router.push({ name: 'tokens' })
}

// 토큰 목록으로 이동
const goToTokensList = () => {
  showSuccessModal.value = false
  router.push({ name: 'tokens' })
}

// 추가 생성
const createAnother = () => {
  showSuccessModal.value = false
  formData.token_id = ''
  formData.description = ''
  generatedApiKey.value = ''
  createdTokenInfo.value = null
}
</script>

<style scoped>
.create-token-page {
  padding: 1rem;
}

.success-content {
  padding: 1rem 0;
}

.api-key-display {
  background: #f8f9fa;
  padding: 1rem;
  border-radius: 0.5rem;
  margin-bottom: 1rem;
}

.token-info {
  background: #f1f3f4;
  padding: 1rem;
  border-radius: 0.5rem;
  font-size: 0.9rem;
}

.token-info p {
  margin: 0.5rem 0;
}
</style>