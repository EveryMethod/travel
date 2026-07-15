<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { completeOAuthLogin } from '@/services'
import type { OAuthProvider } from '@/types'

const route = useRoute()
const status = ref('正在完成登录...')

function readProvider(): OAuthProvider | null {
  return route.query.provider === 'qq' || route.query.provider === 'wechat' ? route.query.provider : null
}

onMounted(async () => {
  const provider = readProvider()
  const code = typeof route.query.code === 'string' ? route.query.code : ''
  const state = typeof route.query.state === 'string' ? route.query.state : ''

  if (!provider) {
    notifyError('缺少或非法第三方登录类型。')
    return
  }

  if (!code || !state) {
    notifyError('缺少登录回调参数。')
    return
  }

  try {
    const auth = await completeOAuthLogin(provider, code, state, false)
    window.opener?.postMessage({ type: 'travel:oauth-success', auth }, window.location.origin)
    status.value = '登录成功，可以关闭此窗口。'
  } catch (error) {
    notifyError(error instanceof Error ? error.message : '第三方登录失败，请重试。')
  }
})

function notifyError(message: string) {
  status.value = message
  window.opener?.postMessage({ type: 'travel:oauth-error', message }, window.location.origin)
}
</script>

<template>
  <main class="callback-page">
    <section class="callback-card">
      <div class="pulse" aria-hidden="true"></div>
      <h1>{{ status }}</h1>
    </section>
  </main>
</template>

<style scoped>
.callback-page {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 24px;
  color: #141414;
  background: #f7f7f7;
  font-family:
    Inter,
    ui-sans-serif,
    system-ui,
    -apple-system,
    BlinkMacSystemFont,
    "Segoe UI",
    sans-serif;
}

.callback-card {
  width: min(100%, 360px);
  display: grid;
  justify-items: center;
  gap: 18px;
  padding: 32px 28px;
  border: 1px solid #e8e8e8;
  border-radius: 24px;
  background: #ffffff;
  box-shadow: 0 20px 50px rgba(20, 20, 20, 0.08);
  text-align: center;
}

.pulse {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: #181818;
  animation: pulse 1.2s ease-in-out infinite;
}

.callback-card h1 {
  margin: 0;
  font-size: 18px;
  line-height: 1.45;
}

@keyframes pulse {
  0%,
  100% {
    transform: scale(0.9);
    opacity: 0.65;
  }
  50% {
    transform: scale(1);
    opacity: 1;
  }
}
</style>
