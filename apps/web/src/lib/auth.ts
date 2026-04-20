import { create } from 'zustand'
import { api } from './api'
import type { User } from '@/types'

interface AuthState {
  user: User | null
  loading: boolean
  initialized: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => Promise<void>
  checkAuth: () => Promise<void>
}

export const useAuth = create<AuthState>((set) => ({
  user: null,
  loading: false,
  initialized: false,

  async login(email, password) {
    set({ loading: true })
    try {
      const { data } = await api.post('/auth/login', { email, password })
      set({ user: data.user, loading: false })
    } catch (err) {
      set({ loading: false })
      throw err
    }
  },

  async logout() {
    try {
      await api.post('/auth/logout')
    } catch {
      // ignore
    }
    set({ user: null })
  },

  async checkAuth() {
    try {
      const { data } = await api.get('/auth/me')
      set({ user: data, initialized: true })
    } catch {
      set({ user: null, initialized: true })
    }
  },
}))
