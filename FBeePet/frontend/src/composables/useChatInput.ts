import { ref, nextTick } from 'vue'

export function useChatInput() {
  const inputMessage = ref('')
  const textareaRef = ref<HTMLTextAreaElement>()
  const isInputFocused = ref(false)

  // 调整输入框高度
  const adjustHeight = () => {
    nextTick(() => {
      if (textareaRef.value) {
        textareaRef.value.style.height = 'auto'
        textareaRef.value.style.height = `${Math.min(textareaRef.value.scrollHeight, 160)}px`
      }
    })
  }

  // 处理输入
  const handleInput = () => {
    adjustHeight()
  }

  // 检测操作系统
  const isMac = () => {
    return navigator.platform.toUpperCase().indexOf('MAC') >= 0 ||
           navigator.userAgent.toUpperCase().indexOf('MAC') >= 0
  }

  // 处理键盘事件
  const handleKeydown = (e: KeyboardEvent, onSend: () => void) => {
    // 正常输入模式 - 根据平台处理发送快捷键
    if (e.key === 'Enter') {
      const macOS = isMac()

      if (macOS) {
        // Mac: Cmd+Enter 发送，Enter 换行
        if (e.metaKey && !e.shiftKey) {
          e.preventDefault()
          onSend()
        }
        // Enter 或 Shift+Enter 都是换行（默认行为）
      } else {
        // Windows/Linux: Enter 发送，Shift+Enter 换行
        if (e.shiftKey) {
          // Shift+Enter 换行（默认行为）
          return
        } else {
          // Enter 发送消息
          e.preventDefault()
          onSend()
        }
      }
    }
  }

  // 清空输入
  const clearInput = () => {
    inputMessage.value = ''
    if (textareaRef.value) {
      textareaRef.value.style.height = 'auto'
    }
  }

  return {
    // 状态
    inputMessage,
    textareaRef,
    isInputFocused,

    // 方法
    handleInput,
    handleKeydown,
    adjustHeight,
    clearInput,

    // 工具函数
    isMac
  }
}
