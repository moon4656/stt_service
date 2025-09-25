<script setup lang="ts">
import { ref, computed } from 'vue'
import { TokenCreate } from '../types'

defineProps<{
  saveButtonLabel?: string
}>()

const emit = defineEmits<{
  (event: 'close'): void
  (event: 'save', token: TokenCreate): void
}>()

const defaultNewToken: TokenCreate = {
  token_id: '',
  description: '',
}

const newToken = ref<TokenCreate>({ ...defaultNewToken })
const formRef = ref()

const isFormHasUnsavedChanges = computed(() => {
  return Object.keys(newToken.value).some((key) => {
    return newToken.value[key as keyof TokenCreate] !== defaultNewToken[key as keyof TokenCreate]
  })
})

// CreateTokenPage.vue와 동일한 유효성 검사 규칙 적용
const tokenIdRules = [
  (value: string) => !!value || '토큰 이름은 필수입니다.',
  (value: string) => value.length >= 3 || '토큰 이름은 최소 3자 이상이어야 합니다.',
  (value: string) => value.length <= 50 || '토큰 이름은 최대 50자까지 가능합니다.',
  (value: string) => /^[a-zA-Z0-9_-]+$/.test(value) || '영문, 숫자, 하이픈(-), 언더스코어(_)만 사용 가능합니다.'
]

const descriptionRules = [
  (value: string) => !value || value.length <= 500 || '설명은 최대 500자까지 가능합니다.'
]

const isFormValid = computed(() => {
  return newToken.value.token_id.trim() !== '' && newToken.value.description.trim() !== ''
})

const saveToken = async () => {
  if (formRef.value) {
    const isValid = await formRef.value.validate()
    if (isValid) {
      emit('save', newToken.value)
      resetForm()
    }
  }
}

const resetForm = () => {
  newToken.value = { ...defaultNewToken }
  if (formRef.value) {
    formRef.value.resetValidation()
  }
}

defineExpose({
  isFormHasUnsavedChanges,
})
</script>

<template>
  <VaForm ref="formRef" @submit.prevent="saveToken">
    <div class="flex flex-col gap-4">
      <VaInput
        v-model="newToken.token_id"
        label="토큰 이름"
        placeholder="토큰 이름을 입력하세요"
        :rules="tokenIdRules"
        required
      />

      <VaTextarea
        v-model="newToken.description"
        label="상세 정보"
        placeholder="토큰에 대한 설명을 입력하세요 (선택사항)"
        :rules="descriptionRules"
        :min-rows="3"
        :max-rows="5"
      />

      <VaAlert color="info" class="mb-2">
        <VaIcon name="info" class="mr-2" />
        <div>
          <strong>토큰 생성 안내</strong>
          <ul class="mt-1 ml-4">
            <li>토큰 이름은 고유해야 하며, 영문, 숫자, 하이픈(-), 언더스코어(_)만 사용 가능합니다.</li>
            <li>발행된 API 키는 한 번만 표시되므로 안전한 곳에 보관하세요.</li>
          </ul>
        </div>
      </VaAlert>
      
      <div class="flex gap-2 flex-col-reverse items-stretch justify-end w-full sm:flex-row sm:items-center">
        <VaButton preset="secondary" color="secondary" @click="$emit('close')">취소</VaButton>
        <VaButton type="submit" :disabled="!isFormValid">{{ saveButtonLabel || '생성' }}</VaButton>
      </div>
    </div>
  </VaForm>
</template>
