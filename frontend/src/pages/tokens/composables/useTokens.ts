import { Ref, ref, watch, computed } from 'vue'
import { Token, TokenCreate, TokenRevoke } from '../types'
import axios from 'axios'

const API_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export type Filters = {
  isActive: boolean
  search: string
}

export type Pagination = {
  page: number
  perPage: number
  total: number
}

export type Sorting = {
  sortBy: keyof Token | null
  sortingOrder: 'asc' | 'desc' | null
}

const makePaginationRef = () => ref<Pagination>({ page: 1, perPage: 10, total: 0 })
const makeSortingRef = () => ref<Sorting>({ sortBy: 'created_at', sortingOrder: 'desc' })
const makeFiltersRef = () => ref<Partial<Filters>>({ isActive: true, search: '' })

export const useTokens = (options?: {
  pagination?: Ref<Pagination>
  sorting?: Ref<Sorting>
  filters?: Ref<Partial<Filters>>
}) => {
  const isLoading = ref(false)
  const error = ref<Error | null>(null)
  const tokens = ref<Token[]>([])

  const { filters = makeFiltersRef(), sorting = makeSortingRef(), pagination = makePaginationRef() } = options || {}

  // Get auth token from localStorage
  const getAuthToken = () => {
    // access_token 우선 확인, 없으면 auth_token 확인
    return localStorage.getItem('access_token') || localStorage.getItem('auth_token')
  }

  // Create axios instance with auth header
  const createAuthHeaders = () => {
    const token = getAuthToken()
    if (!token) {
      throw new Error('인증 토큰이 없습니다. 다시 로그인해주세요.')
    }
    return { Authorization: `Bearer ${token}` }
  }

  const create = async (tokenData: TokenCreate) => {
    isLoading.value = true
    error.value = null
    try {
      // 실제 API 호출로 변경
      const authHeaders = createAuthHeaders()
  
      const response = await axios.post(
        `${API_URL}/tokens/${tokenData.token_id}?description=${encodeURIComponent(tokenData.description)}`,
        {}, // 빈 body
        {
          headers: {
            ...authHeaders,
            'Content-Type': 'application/json',
          },
        },
      )
  
      if (response.data.message) {
        await fetch() // Refresh the list
        return {
          api_key: response.data.api_key,
          token_id: response.data.token_id,
          description: response.data.description,
          status: 'success',
        }
      } else {
        throw new Error(response.data.detail || 'Failed to create token')
      }
      
      // 목업 코드 제거
      /*
      console.log('Creating token with data:', tokenData)
      await new Promise(resolve => setTimeout(resolve, 2000))
      const mockApiKey = `sk-${Math.random().toString(36).substring(2, 15)}${Math.random().toString(36).substring(2, 15)}`
      console.log('Mock API key generated:', mockApiKey)
      return {
        api_key: mockApiKey,
        token_id: tokenData.token_id,
        description: tokenData.description,
        status: 'success'
      }
      */
    } catch (err: any) {
      console.error('Token creation error details:', err.response || err)

      if (err.response?.status === 401 || err.response?.status === 403) {
        // 인증 실패 시 로그인 페이지로 리다이렉트 또는 토큰 갱신
        localStorage.removeItem('auth_token')
        error.value = new Error('인증이 만료되었습니다. 다시 로그인해주세요.')
        // 필요시 로그인 페이지로 리다이렉트
        window.location.href = '/login'
      } else if (err.response?.status === 400) {
        error.value = new Error(err.response.data.detail || '토큰 생성에 실패했습니다.')
      } else if (err.message === '인증 토큰이 없습니다. 다시 로그인해주세요.') {
        error.value = err
        window.location.href = '/login'
      } else {
        error.value = new Error('토큰 생성 중 오류가 발생했습니다.')
      }
      throw err
    } finally {
      isLoading.value = false
    }
  }

  const fetch = async () => {
    console.log('🔍 fetch 시작 - isLoading:', isLoading.value)
    isLoading.value = true
    error.value = null
    try {
      const response = await axios.get(`${API_URL}/tokens/`, {
        headers: createAuthHeaders(),
        params: {
          is_active: filters.value.isActive,
          search: filters.value.search,
        }
      })

      console.log('📥 API 응답:', response.data)

      if (response.data.status === 'success') {
        tokens.value = response.data.tokens
        pagination.value.total = response.data.tokens.length
        console.log('✅ 토큰 설정 완료:', tokens.value.length, '개')
      } else {
        throw new Error(response.data.message || 'Failed to fetch tokens')
      }
    } catch (err: any) {
      console.error('❌ fetch 에러:', err)

      if (err.response?.status === 401 || err.response?.status === 403) {
        // 인증 실패 시 처리
        localStorage.removeItem('access_token')
        localStorage.removeItem('auth_token')
        error.value = new Error('인증이 만료되었습니다. 다시 로그인해주세요.')
        // 필요시 로그인 페이지로 리다이렉트
        // window.location.href = '/login'
      } else {
        error.value = err
      }
    } finally {
      console.log('🏁 fetch 완료 - isLoading:', false)
      isLoading.value = false
    }
  }

  const revoke = async (tokenData: TokenRevoke) => {
    isLoading.value = true
    error.value = null
    try {
      const response = await axios.post(
        `${API_URL}/tokens/revoke`,
        {
          api_key_hash: tokenData.api_key_hash,
        },
        {
          headers: createAuthHeaders(),
        },
      )

      if (response.data.status === 'success') {
        await fetch() // Refresh the list
        return response.data
      } else {
        throw new Error(response.data.message || 'Failed to revoke token')
      }
    } catch (err: any) {
      error.value = err
      console.error('Error revoking token:', err)
      throw err
    } finally {
      isLoading.value = false
    }
  }

  watch(
    filters,
    () => {
      pagination.value.page = 1
      fetch()
    },
    { deep: true },
  )

  // Filter and sort tokens
  const filteredTokens = computed(() => {
    let result = [...tokens.value]

    // Apply filters
    if (filters.value.isActive !== undefined) {
      result = result.filter((token) => token.is_active === filters.value.isActive)
    }

    if (filters.value.search) {
      const searchTerm = filters.value.search.toLowerCase()
      result = result.filter(
        (token) =>
          token.token_id.toLowerCase().includes(searchTerm) || token.description.toLowerCase().includes(searchTerm),
      )
    }

    // Apply sorting
    if (sorting.value.sortBy && sorting.value.sortingOrder) {
      result.sort((a, b) => {
        const aVal = a[sorting.value.sortBy!]
        const bVal = b[sorting.value.sortBy!]

        // 타입별로 안전한 비교 수행
        if (typeof aVal === 'string' && typeof bVal === 'string') {
          const comparison = aVal.localeCompare(bVal)
          return sorting.value.sortingOrder === 'asc' ? comparison : -comparison
        }

        if (typeof aVal === 'number' && typeof bVal === 'number') {
          return sorting.value.sortingOrder === 'asc' ? aVal - bVal : bVal - aVal
        }

        if (typeof aVal === 'boolean' && typeof bVal === 'boolean') {
          const aNum = aVal ? 1 : 0
          const bNum = bVal ? 1 : 0
          return sorting.value.sortingOrder === 'asc' ? aNum - bNum : bNum - aNum
        }

        return 0
      })
    }

    return result
  })

  // Initialize
  fetch()

  return {
    tokens: filteredTokens,
    isLoading,
    error,
    filters,
    sorting,
    pagination,
    fetch,
    create,
    revoke,
  }
}
