import { createContext, useContext } from 'react'

/** Üst çubuktaki arama kutusunun değeri; Inbox konuşma listesini bununla süzer. */
export const ShellSearchContext = createContext<string>('')
export const useShellSearch = () => useContext(ShellSearchContext)
