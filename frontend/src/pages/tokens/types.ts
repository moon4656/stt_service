export type UUID = `${string}-${string}-${string}-${string}-${string}`

export type Token = {
  api_key_hash: string
  token_id: string
  description: string
  created_at: string
  is_active: boolean
  usage_count: number
  last_used?: string
  revoked_at?: string
}

export type TokenCreate = {
  token_id: string
  description: string
}

export type TokenRevoke = {
  api_key_hash: string
}

export type TokenHistory = {
  action: string
  api_key_hash: string
  user_uuid: string
  timestamp: string
}
