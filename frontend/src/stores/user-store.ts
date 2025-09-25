import { defineStore } from 'pinia'

interface UserState {
  userName: string
  email: string
  memberSince: string
  pfp: string
  is2FAEnabled: boolean
  isLoggedIn: boolean
}

export const useUserStore = defineStore('user', {
  state: (): UserState => {
    return {
      userName: '',
      email: '',
      memberSince: '',
      pfp: '',
      is2FAEnabled: false,
      isLoggedIn: false,
    }
  },

  actions: {
    // 로그인 시 사용자 정보 설정
    setUserInfo(userInfo: any) {
      this.userName = userInfo.name || userInfo.user_id || ''
      this.email = userInfo.email || ''
      this.memberSince = userInfo.created_at ? new Date(userInfo.created_at).toLocaleDateString() : ''
      this.pfp = userInfo.avatar || 'https://picsum.photos/id/22/200/300'
      this.is2FAEnabled = userInfo.is_2fa_enabled || false
      this.isLoggedIn = true
    },

    // localStorage에서 사용자 정보 로드
    loadUserFromStorage() {
      const storedUser = localStorage.getItem('user')
      if (storedUser) {
        try {
          const userData = JSON.parse(storedUser)
          if (userData.user) {
            this.setUserInfo(userData.user)
          }
        } catch (error) {
          console.error('Failed to parse stored user data:', error)
        }
      }
    },

    // 로그아웃 시 사용자 정보 초기화
    clearUserInfo() {
      this.userName = ''
      this.email = ''
      this.memberSince = ''
      this.pfp = ''
      this.is2FAEnabled = false
      this.isLoggedIn = false
    },

    toggle2FA() {
      this.is2FAEnabled = !this.is2FAEnabled
    },

    changeUserName(userName: string) {
      this.userName = userName
    },
  },
})
