import axios, { type AxiosInstance, type AxiosError } from 'axios'
import type { ApiResponse } from '@/types'

const API_BASE = '/api/v1'

const client: AxiosInstance = axios.create({
  baseURL: API_BASE,
  timeout: 15_000,
  headers: { 'Content-Type': 'application/json' },
})

// ── Request interceptor ──
client.interceptors.request.use(
  (config) => config,
  (error) => Promise.reject(error),
)

// ── Response interceptor: unwrap {code, data, message} envelope ──
client.interceptors.response.use(
  (response) => {
    const body = response.data as ApiResponse
    if (body.code !== 200) {
      console.warn(`[API] ${response.config.url} → code=${body.code}: ${body.message}`)
    }
    return response
  },
  (error: AxiosError<ApiResponse>) => {
    const msg = error.response?.data?.message ?? error.message
    console.error(`[API] ${error.config?.url} → ${msg}`)
    return Promise.reject(error)
  },
)

export default client

/** Extract data field from API response */
export function unwrap<T>(response: { data: ApiResponse<T> }): T {
  return response.data.data
}
