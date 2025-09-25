<template>
  <VaForm ref="form" @submit.prevent="submit">
    <h1 class="font-semibold text-4xl mb-4">회원가입</h1>
    <p class="text-base mb-4 leading-5">
      이미 계정을 가지고 계시나요?
      <RouterLink :to="{ name: 'login' }" class="font-semibold text-primary">Login</RouterLink>
    </p>
    <!--
      <VaInput
      v-model="formData.id"
      :rules="[(v) => !!v || 'ID field is required']"
      class="mb-4"
      label="ID"
      />
    -->
    <VaInput
      v-model="formData.email"
      :rules="[
        (v) => !!v || '이메일 필드는 필수입니다',
        (v) => /.+@.+\..+/.test(v) || '이메일 형식이 올바르지 않습니다',
      ]"
      class="mb-4"
      label="Email"
      type="email"
    />
    <VaInput v-model="formData.name" :rules="[(v) => !!v || '이름 필드는 필수입니다']" class="mb-4" label="Name" />
    <VaInput
      v-model="formData.phone"
      :rules="[
        (v) => !!v || '전화번호 필드는 필수입니다',
        (v) => /^[0-9-+()]{10,15}$/.test(v) || '전화번호 형식이 올바르지 않습니다',
      ]"
      class="mb-4"
      label="Phone"
    />
    <VaValue v-slot="isPasswordVisible" :default-value="false">
      <VaInput
        ref="password1"
        v-model="formData.password"
        :rules="passwordRules"
        :type="isPasswordVisible.value ? 'text' : 'password'"
        class="mb-4"
        label="Password"
        messages="비밀번호는 8자 이상이어야 하며, 문자, 숫자, 특수 문자를 포함해야 합니다."
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
      <VaInput
        ref="password2"
        v-model="formData.repeatPassword"
        :rules="[
          (v) => !!v || '비밀번호 확인 필드는 필수입니다',
          (v) => v === formData.password || '비밀번호가 일치하지 않습니다',
        ]"
        :type="isPasswordVisible.value ? 'text' : 'password'"
        class="mb-4"
        label="Repeat Password"
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

    <div class="flex justify-center mt-4">
      <VaButton class="w-full" @click="submit"> Create account</VaButton>
    </div>
  </VaForm>
</template>

<script lang="ts" setup>
import { reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useForm, useToast } from 'vuestic-ui'
import authService from '../../services/auth-service'

const { validate } = useForm('form')
const { push } = useRouter()
const { init } = useToast()

const formData = reactive({
  id: '', // id 필드 제거
  email: '',
  name: '',
  phone: '',
  password: '',
  repeatPassword: '',
})

const submit = async () => {
  if (validate()) {
    try {
      // 회원가입 요청 데이터 준비
      const signupData = {
        user_id: formData.email, // id를 email로 사용
        email: formData.email,
        name: formData.name,
        user_type: '개인', // 기본값으로 '개인' 설정
        phone_number: formData.phone,
        password: formData.password,
      }

      // API 호출
      const response = await authService.signup(signupData)

      // 성공 메시지 표시 (서버 응답 활용)
      init({
        message: response?.message || `${formData.name}님, 회원가입이 성공적으로 완료되었습니다!`,
        color: 'success',
      })

      console.log('회원가입 성공:', response)

      // 로그인 페이지로 이동
      push({ name: 'login' })
    } catch (error: any) {
      // 에러 메시지 표시
      init({
        message: error.response?.data?.detail || '회원가입 중 오류가 발생했습니다.',
        color: 'danger',
      })
    }
  }
}

const passwordRules: ((v: string) => boolean | string)[] = [
  (v) => !!v || '비밀번호 필드는 필수입니다',
  (v) => (v && v.length >= 8) || '비밀번호는 8자 이상이어야 합니다',
  (v) => (v && /[A-Za-z]/.test(v)) || '비밀번호에는 문자가 포함되어야 합니다',
  (v) => (v && /\d/.test(v)) || '비밀번호에는 숫자가 포함되어야 합니다',
  (v) => (v && /[!@#$%^&*(),.?":{}|<>]/.test(v)) || '비밀번호에는 특수 문자가 포함되어야 합니다',
]
</script>
