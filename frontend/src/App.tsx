import { useEffect } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useChatStore } from './store/chatStore'
import ChatPage from './pages/ChatPage'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 30_000,
    },
  },
})

export default function App() {
  const darkMode = useChatStore((s) => s.darkMode)

  // Sync dark mode class on <html>
  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }, [darkMode])

  return (
    <QueryClientProvider client={queryClient}>
      <ChatPage />
    </QueryClientProvider>
  )
}
