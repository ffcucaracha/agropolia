import { QueryClient } from '@tanstack/react-query'

// Shared cache instance can be wiped synchronously during session transitions.
// Cache keys for tenant-owned data are not safe to reuse between users.
export const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, staleTime: 30_000 } },
})
