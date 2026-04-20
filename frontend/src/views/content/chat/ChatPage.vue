<template>
  <div class="ai-practice-container">
    <div class="history-panel">
      <div class="new-chat-container">
        <button class="new-chat-btn" @click="newConversation">
          新建对话
          <el-icon class="plus-icon">
            <Plus />
          </el-icon>
        </button>
      </div>
      <ul class="history-list">
        <li
          v-for="(item, index) in historyList"
          :key="index"
          :class="{ active: currentConversationIndex === index }"
          @click="selectConversation(index)"
        >
          {{ item.title }}
        </li>
      </ul>
    </div>

    <div class="chat-wrapper">
      <div class="chat-panel">
        <div class="chat-messages" ref="chatMessagesRef">
          <div
            v-for="(message, index) in currentConversation.messages"
            :key="index"
            :class="['message', message.role]"
          >
            <div class="avatar">
              <div v-if="message.role !== 'user'" class="ai-avatar">
                <img src="@/assets/images/hailuo2.png" alt="AI Avatar">
              </div>
              <div v-else>
                <img src="@/assets/images/user.png" alt="Me">
              </div>
            </div>
            <div class="content">
              <div v-if="message.imagePath" class="image-path">图片：{{ message.imagePath }}</div>
              {{ message.content }}
            </div>
          </div>
        </div>

        <div class="input-area">
          <div class="input-wrapper">
            <el-icon class="input-icon link-icon">
              <Link />
            </el-icon>
            <input
              v-model="userInput"
              @keyup.enter="sendMessage"
              type="text"
              :disabled="isInputDisabled"
              :placeholder="isImageQaConversation ? '请用文字描述图片现象，例如：果实发黑并有凹陷，这是什么病？' : '输入消息，按回车发送...'"
            >
            <div class="button-group">
              <div class="audio-wave" v-if="isRecording" @click="finishRecording">
                <span v-for="n in 4" :key="n" :style="{ animationDelay: `${n * 0.2}s` }"></span>
              </div>
              <el-icon v-else class="input-icon microphone-icon" @click="toggleRecording">
                <Microphone />
              </el-icon>
              <div class="separator"></div>
              <el-popover
                placement="top"
                :width="220"
                trigger="hover"
                :disabled="canSend"
              >
                <template #reference>
                  <el-button
                    class="send-button"
                    circle
                    :disabled="!canSend"
                    @click="sendMessage"
                  >
                    <el-icon>
                      <Top />
                    </el-icon>
                  </el-button>
                </template>
                <span>{{ sendHint }}</span>
              </el-popover>
            </div>
          </div>
        </div>

        <div class="disclaimer">
          当前页面的文本问答已接入云端 DeepSeek，密钥保存在后端。图像问答入口暂不再调用本地模型。
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue'
import { Link, Microphone, Plus, Top } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { get } from '@/utils/request'
import { API } from '@/api/config'

const historyList = ref([
  {
    title: '小番茄咨询',
    messages: [
      {
        role: 'assistant',
        content: '你好，我是番茄专家助手。当前文本问答已接入云端 DeepSeek，你可以直接问我番茄种植、产量、养护和病害相关问题。'
      }
    ]
  },
  {
    title: '番茄图像问答',
    messages: [
      {
        role: 'assistant',
        content: '当前系统已切换为云端 DeepSeek。由于现阶段接入的是官方文本对话接口，这里暂不支持直接上传本地图片路径做图像问答；你可以先用文字描述图片情况，再继续咨询。'
      }
    ]
  },
  {
    title: '番茄数量预测',
    messages: [
      {
        role: 'assistant',
        content: '这里保留为文本问答入口，后续可以继续接数量预测模型。'
      }
    ]
  },
  {
    title: '番茄植株分析',
    messages: [
      {
        role: 'assistant',
        content: '这里保留为文本问答入口，后续可以继续接植株分析模型。'
      }
    ]
  }
])

const currentConversationIndex = ref(0)
const userInput = ref('')
const chatMessagesRef = ref(null)
const isRecording = ref(false)
const isInputDisabled = ref(false)
const mediaStream = ref(null)
let mediaRecorder = null

const currentConversation = computed(() => historyList.value[currentConversationIndex.value])
const isImageQaConversation = computed(() => currentConversation.value?.title === '番茄图像问答')
const canSend = computed(() => {
  return !!userInput.value.trim()
})
const sendHint = computed(() => {
  if (isImageQaConversation.value) {
    return '请先用文字描述图片现象，再发送问题'
  }
  return '请输入问题后再发送'
})

const scrollToBottom = () => {
  const chatMessages = chatMessagesRef.value
  if (!chatMessages) {
    return
  }
  chatMessages.scrollTop = chatMessages.scrollHeight
}

const ensureMessages = (conversation) => {
  if (!Array.isArray(conversation.messages)) {
    conversation.messages = []
  }
}

const selectConversation = (index) => {
  currentConversationIndex.value = index
  nextTick(scrollToBottom)
}

const newConversation = () => {
  historyList.value.unshift({
    title: '新对话',
    messages: [
      {
        role: 'assistant',
        content: '你好，我是番茄专家助手。当前文本问答已接入云端 DeepSeek；如果需要图片分析，请先用文字描述图片现象再提问。'
      }
    ]
  })
  currentConversationIndex.value = 0
  nextTick(scrollToBottom)
}

const sendMessage = async () => {
  if (!canSend.value) {
    return
  }

  ensureMessages(currentConversation.value)
  const prompt = userInput.value.trim()
  const requestPrompt = isImageQaConversation.value
    ? `这是一个图片分析场景，但用户当前只能提供文字描述，无法上传图片。请基于以下描述给出番茄种植诊断和建议：${prompt}`
    : prompt

  currentConversation.value.messages.push({
    role: 'user',
    content: prompt
  })
  userInput.value = ''
  nextTick(scrollToBottom)

  const loadingMessage = {
    role: 'assistant',
    content: 'DeepSeek 正在思考...',
    loading: true
  }
  currentConversation.value.messages.push(loadingMessage)
  nextTick(scrollToBottom)

  try {
    const res = await get(API.GENERATE, { prompt: requestPrompt })

    if (res.code === 100) {
      loadingMessage.content = res.data
      loadingMessage.loading = false
    } else {
      loadingMessage.content = res.msg || '获取回复失败，请稍后重试'
      loadingMessage.loading = false
      ElMessage.error(loadingMessage.content)
    }
  } catch (error) {
    console.error('sendMessage error', error)
    const backendMsg = error?.response?.data?.msg || error?.message
    loadingMessage.content = error?.code === 'ECONNABORTED'
      ? '云端模型响应时间过长，请稍后重试。'
      : (backendMsg ? `获取回复失败：${backendMsg}` : '获取回复失败，请检查后端服务和 DeepSeek 配置')
    loadingMessage.loading = false
    ElMessage.error(loadingMessage.content)
  }

  nextTick(scrollToBottom)
}

const finishRecording = () => {
  if (isRecording.value && mediaRecorder && mediaRecorder.state !== 'inactive') {
    mediaRecorder.stop()
    isRecording.value = false
    isInputDisabled.value = false
  }
}

const toggleRecording = async () => {}

const stopMediaStream = () => {
  if (mediaStream.value) {
    mediaStream.value.getTracks().forEach(track => track.stop())
    mediaStream.value = null
  }
}

onMounted(() => {
  nextTick(scrollToBottom)
})

onUnmounted(() => {
  finishRecording()
  stopMediaStream()
})
</script>

<style scoped>
.ai-practice-container {
  display: flex;
  height: 100vh;
  font-family: Arial, sans-serif;
}

.history-panel {
  width: 280px;
  background: linear-gradient(135deg, rgba(230, 240, 255, 0.01), rgba(240, 230, 255, 0.01));
  background-color: #ffffff;
  padding: 20px;
  overflow-y: auto;
}

.new-chat-container {
  display: flex;
  align-items: center;
  margin-bottom: 20px;
}

.new-chat-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  padding: 13px;
  margin-top: 10px;
  margin-bottom: 5px;
  background: linear-gradient(to right, #0069e0, #0052bc);
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: opacity 0.3s;
  font-size: 14px;
  font-weight: bold;
}

.new-chat-btn:hover {
  opacity: 0.9;
}

.history-list {
  list-style-type: none;
  padding: 0;
}

.history-list li {
  padding: 10px;
  margin-bottom: 10px;
  background-color: #ffffff;
  border-radius: 8px;
  cursor: pointer;
  transition: background-color 0.3s;
}

.history-list li:hover,
.history-list li.active {
  background-color: rgba(0, 105, 224, 0.15);
  color: #0052bc;
}

.chat-wrapper {
  flex: 1;
  display: flex;
  justify-content: center;
  align-items: center;
  background: linear-gradient(135deg, rgba(0, 105, 224, 0.08), rgba(0, 56, 148, 0.08));
}

.chat-panel {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  background-color: transparent;
  box-shadow: none;
  padding-top: 12px;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding-top: 20px;
  padding-left: 10%;
  padding-right: 10%;
  background-color: transparent;
  scrollbar-width: thin;
  scrollbar-color: rgba(0, 105, 224, 0.3) transparent;
}

.chat-messages::-webkit-scrollbar {
  width: 6px;
}

.chat-messages::-webkit-scrollbar-track {
  background: transparent;
}

.chat-messages::-webkit-scrollbar-thumb {
  background-color: rgba(0, 105, 224, 0.3);
  border-radius: 3px;
}

.message {
  display: flex;
  margin-bottom: 20px;
}

.message .avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background-color: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 10px;
  overflow: hidden;
}

.message .avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 50%;
  background-color: #ffffff;
}

.message .content {
  background-color: rgba(255, 255, 255, 1);
  padding: 12px 18px;
  border-radius: 10px;
  max-width: 80%;
  font-size: 16px;
  line-height: 1.8;
  white-space: pre-wrap;
}

.message.user {
  flex-direction: row-reverse;
}

.message.user .avatar {
  margin-right: 0;
  margin-left: 10px;
}

.message.user .content {
  background-color: rgba(0, 105, 224, 0.12);
  color: black;
}

.image-path {
  margin-bottom: 6px;
  color: #0052bc;
  font-size: 13px;
  word-break: break-all;
}

.input-area {
  padding: 20px 10% 0 10%;
  background-color: transparent;
}

.input-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}

input {
  width: 100%;
  padding: 12px 110px 12px 50px;
  border: 1px solid rgba(204, 204, 204, 0.5);
  border-radius: 25px;
  font-size: 16px;
  background-color: rgba(255, 255, 255, 0.7);
  transition: border-color 0.3s;
  height: 55px;
}

input:focus {
  outline: none;
  border-color: #0069e0;
}

input::placeholder {
  color: #969696;
}

.button-group {
  position: absolute;
  right: 10px;
  top: 50%;
  transform: translateY(-50%);
  display: flex;
  align-items: center;
}

.input-icon {
  color: #0069e0;
  font-size: 24px;
  cursor: pointer;
}

.link-icon {
  position: absolute;
  left: 18px;
  top: 50%;
  transform: translateY(-50%);
}

.separator {
  width: 1px;
  height: 25px;
  background-color: rgba(204, 204, 204, 0.5);
  margin: 0 10px;
}

.send-button {
  width: 40px;
  height: 40px;
  background: linear-gradient(to right, #0069e0, #0052bc);
  border: none;
  color: white;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
}

.send-button:disabled {
  background: rgba(0, 105, 224, 0.1);
  color: rgba(0, 82, 188, 0.3);
  cursor: default;
}

.send-button :deep(.el-icon) {
  font-size: 24px;
}

.send-button:not(:disabled):hover {
  opacity: 0.9;
}

.disclaimer {
  font-size: 10px;
  color: #999;
  text-align: center;
  margin-top: 12px;
  margin-bottom: 12px;
}

.audio-wave {
  display: flex;
  align-items: center;
  height: 24px;
  width: 24px;
}

.audio-wave span {
  display: inline-block;
  width: 3px;
  height: 100%;
  margin-right: 1px;
  background: #0069e0;
  animation: audio-wave 0.8s infinite ease-in-out;
}

@keyframes audio-wave {
  0%, 100% {
    transform: scaleY(0.3);
  }
  50% {
    transform: scaleY(1);
  }
}
</style>
