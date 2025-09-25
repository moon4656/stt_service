import axios from 'axios'

const API_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export interface SignupRequest {
  user_id: string
  email: string
  name: string
  user_type: string
  phone_number?: string
  password: string
}

export interface LoginRequest {
  email: string
  password: string
}

const authService = {
  signup: async (userData: SignupRequest) => {
    try {
      const response = await axios.post(`${API_URL}/users/`, userData)
      return response.data
    } catch (error) {
      console.error('Signup error:', error)
      throw error
    }
  },

  login: async (loginData: LoginRequest) => {
    try {
      const response = await axios.post(`${API_URL}/auth/login`, loginData)
      if (response.data.access_token) {
        localStorage.setItem('user', JSON.stringify(response.data))
        localStorage.setItem('access_token', response.data.access_token)
      }
      return response.data
    } catch (error: any) {
      console.error('Login error:', error)
      // 에러 메시지 처리
      if (error.response?.status === 401) {
        throw new Error(error.response.data.detail || '메일 또는 비밀번호를 확인해주세요.')
      } else if (error.response?.status === 423) {
        throw new Error(error.response.data.detail || '계정이 잠겨있습니다.')
      }
      throw error
    }
  },

  // logout 함수 수정
  logout: () => {
    localStorage.removeItem('user')
    localStorage.removeItem('access_token')
    // user-store 초기화는 로그아웃 컴포넌트에서 처리
  },
}

export default authService
