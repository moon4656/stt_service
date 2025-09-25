<template>
  <VaForm ref="form" @submit.prevent="submit">
    <h1 class="font-semibold text-4xl mb-4">Log in</h1>
    <p class="text-base mb-4 leading-5">
      아직 계정이 없으신가요?
      <RouterLink :to="{ name: 'signup' }" class="font-semibold text-primary">회원가입</RouterLink>
    </p>

    <!-- 에러 메시지 표시 -->
    <VaAlert v-if="errorMessage" color="danger" class="mb-4">
      {{ errorMessage }}
    </VaAlert>

    <VaInput
      v-model="formData.email"
      :rules="[validators.required, validators.email]"
      class="mb-4"
      label="Email"
      type="email"
    />
    <VaValue v-slot="isPasswordVisible" :default-value="false">
      <VaInput
        v-model="formData.password"
        :rules="[validators.required]"
        :type="isPasswordVisible.value ? 'text' : 'password'"
        class="mb-4"
        label="Password"
        @clickAppendInner.stop="isPasswordVisible.value = !isPasswordVisible.value"
      >
        <template #appendInner>
          <VaIcon
            :name="isPasswordVisible.value ? 'mso-visibility_off' : 'mso-visibility'"
            class="cursor-pointer"
            color="secondary"
          />
        </template>
      </VaInput>
    </VaValue>

    <div class="auth-layout__options flex flex-col sm:flex-row items-start sm:items-center justify-between">
      <VaCheckbox v-model="formData.keepLoggedIn" class="mb-2 sm:mb-0" label="로그인 상태 유지" />
      <RouterLink :to="{ name: 'recover-password' }" class="mt-2 sm:mt-0 sm:ml-1 font-semibold text-primary">
        비밀번호를 잊어버렸나요?
      </RouterLink>
    </div>

    <div class="flex justify-center mt-4">
      <VaButton class="w-full" :loading="isLoading" :disabled="isLoading" @click="submit">
        {{ isLoading ? '로그인 중...' : 'Login' }}
      </VaButton>
    </div>
  </VaForm>
</template>

<script lang="ts" setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useForm, useToast } from 'vuestic-ui'
import { validators } from '../../services/utils'
import authService from '../../services/auth-service'
import { useUserStore } from '../../stores/user-store'

// setup 함수 내부에 추가
const userStore = useUserStore()
const { validate } = useForm('form')
const { push } = useRouter()
const { init } = useToast()

const formData = reactive({
  email: 'test_01@sample.com',
  password: 'test',
  keepLoggedIn: false,
})

const errorMessage = ref('')
const isLoading = ref(false)

const submit = async () => {
  if (!validate()) {
    return
  }

  isLoading.value = true
  errorMessage.value = ''

  try {
    const response = await authService.login({
      email: formData.email, // email을 user_id로 전송
      password: formData.password,
    })

    // 응답 데이터 검증
    if (response && response.access_token) {
      // 토큰을 로컬 스토리지에 저장 (authService에서 처리됨)
      init({ message: '로그인에 성공하였습니다', color: 'success' })

      // 사용자 정보가 있다면 추가 처리
      if (response.user) {
        console.log('로그인한 사용자:', response.user)
        userStore.setUserInfo(response.user)
      }

      // 대시보드로 이동
      await push({ name: 'dashboard' })
    } else {
      throw new Error('로그인 응답이 올바르지 않습니다.')
    }
  } catch (error: any) {
    console.error('Login failed:', error)

    // 에러 메시지 처리
    let displayMessage = '로그인 중 오류가 발생했습니다.'

    if (error.response) {
      // 서버에서 반환한 에러
      const serverError = error.response.data
      if (serverError && serverError.detail) {
        displayMessage = serverError.detail
      } else if (error.response.status === 401) {
        displayMessage = '이메일 또는 비밀번호가 올바르지 않습니다.'
      } else if (error.response.status === 423) {
        displayMessage = '계정이 잠겨있습니다. 관리자에게 문의하세요.'
      } else if (error.response.status >= 500) {
        displayMessage = '서버 오류가 발생했습니다. 잠시 후 다시 시도해주세요.'
      }
    } else if (error.message) {
      displayMessage = error.message
    }

    errorMessage.value = displayMessage

    // 계정 잠금 상태일 때 추가 안내
    if (displayMessage.includes('계정이 잠겨있습니다') || displayMessage.includes('잠금')) {
      init({
        message: displayMessage,
        color: 'warning',
        duration: 7000,
      })
    } else {
      init({
        message: displayMessage,
        color: 'danger',
        duration: 4000,
      })
    }
  } finally {
    isLoading.value = false
  }
}
</script>
