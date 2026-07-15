# 登录维护 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 用最小改动补齐现有登录链路的守卫、鉴权请求头、退出兜底和 OAuth provider 校验。

**Architecture:** 继续复用现有 `front/src/services/index.ts` 作为 token 单一读写点，不新增 Pinia auth store。路由层只基于本地 token presence 做轻量守卫，OAuth callback fail-closed。

**Tech Stack:** Vue 3、Vue Router、TypeScript、现有浏览器 `localStorage/sessionStorage`、现有 `fetch` 服务层。

## Global Constraints

- 不新增依赖。
- 不新增 Pinia auth store。
- 不实现 refresh-token 自动续期。
- 不实现 `/api/auth/me`、忘记密码、修改密码、账号资料页。
- 不提交 commit，除非用户明确要求。
- 计划文档使用中文。

---

## File Structure

- Modify: `front/src/services/index.ts`
  - 负责 token 存取、共享请求、登录/注册/OAuth/退出 API。
  - 本次集中加入 Authorization header 和 logout best-effort 兜底。

- Modify: `front/src/router/index.ts`
  - 负责路由定义。
  - 本次加入最小 `beforeEach` 守卫，复用 `getAuthTokens()`。

- Modify: `front/src/views/AuthCallbackView.vue`
  - 负责 OAuth 弹窗回调。
  - 本次把 provider 从隐式 fallback 改为显式校验。

---

### Task 1: 服务层自动带 token，并让 logout 不阻塞本地退出

**Files:**
- Modify: `front/src/services/index.ts:122-171`

**Interfaces:**
- Consumes: `getAuthTokens(): AuthTokens | null`、`clearAuthTokens(): void`
- Produces: `request<T>(url, options)` 在有 token 时自动发送 `Authorization`；`logout(): Promise<void>` 不再因后端失败阻塞本地退出。

- [ ] **Step 1: 修改 `logout()` 为 best-effort 后端请求 + 必定清本地 token**

把 `front/src/services/index.ts` 中现有 `logout()` 替换为：

```ts
export async function logout(): Promise<void> {
  const tokens = getAuthTokens()
  try {
    if (tokens) {
      await request('/api/auth/logout', {
        method: 'POST',
        body: {
          access_token: tokens.access_token,
          refresh_token: tokens.refresh_token,
        },
      })
    }
  } catch {
    // ponytail: logout is best-effort; local tokens must clear even if backend is down.
  } finally {
    clearAuthTokens()
  }
}
```

- [ ] **Step 2: 修改 `request()` 自动注入 Authorization**

把 `request()` 中的 `fetch` 调用前加入 token 读取，并把 headers 改成下面这样：

```ts
async function request<T = unknown>(
  url: string,
  options: { method?: string; body?: unknown; headers?: HeadersInit } = {},
): Promise<T> {
  let response: Response
  const tokens = getAuthTokens()

  try {
    response = await fetch(url, {
      method: options.method ?? 'GET',
      headers: {
        ...(options.body === undefined ? {} : { 'Content-Type': 'application/json' }),
        ...(tokens ? { Authorization: `Bearer ${tokens.access_token}` } : {}),
        ...options.headers,
      },
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
    })
  } catch {
    throw new Error('无法连接后端 API，请确认服务正在运行。')
  }

  if (!response.ok) {
    throw new Error(await getErrorMessage(response))
  }

  if (response.status === 204) {
    return undefined as T
  }

  return response.json() as Promise<T>
}
```

- [ ] **Step 3: 运行前端构建验证类型和打包**

Run:

```bash
corepack pnpm --dir front build
```

Expected:

- PASS，Vite build 完成。
- 如果失败，先看 TypeScript 报错是否来自 `HeadersInit` spread；若是，用现有项目允许的最小对象 header 方式修复，不新增工具函数。

---

### Task 2: 给 `/home` 和 `/login` 加最小路由守卫

**Files:**
- Modify: `front/src/router/index.ts:1-30`

**Interfaces:**
- Consumes: `getAuthTokens(): AuthTokens | null` from `@/services`
- Produces: Vue Router `beforeEach` guard

- [ ] **Step 1: 导入 `getAuthTokens`**

把文件顶部改为：

```ts
import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { getAuthTokens } from '@/services'
```

- [ ] **Step 2: 保留现有 routes，不改页面结构**

`routes` 仍然保持：

```ts
const routes: RouteRecordRaw[] = [
  {
    path: '/',
    redirect: '/login',
  },
  {
    path: '/home',
    name: 'home',
    component: () => import('@/views/HomeView.vue'),
  },
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/LoginView.vue'),
  },
  {
    path: '/auth/callback',
    name: 'auth-callback',
    component: () => import('@/views/AuthCallbackView.vue'),
  },
]
```

- [ ] **Step 3: 在 `createRouter` 后加入 guard**

在 `const router = createRouter(...)` 后、`export default router` 前加入：

```ts
router.beforeEach((to) => {
  const isLoggedIn = getAuthTokens() !== null

  if (to.name === 'home' && !isLoggedIn) {
    return { name: 'login' }
  }

  if ((to.name === 'login' || to.path === '/') && isLoggedIn) {
    return { name: 'home' }
  }

  return true
})
```

- [ ] **Step 4: 运行前端构建验证路由类型**

Run:

```bash
corepack pnpm --dir front build
```

Expected:

- PASS。
- 没有 Vue Router 类型错误。

---

### Task 3: OAuth callback provider 显式校验

**Files:**
- Modify: `front/src/views/AuthCallbackView.vue:1-33`

**Interfaces:**
- Consumes: `OAuthProvider = 'qq' | 'wechat'`
- Produces: `readProvider(): OAuthProvider | null`

- [ ] **Step 1: 把 provider computed 替换为显式读取函数**

把当前：

```ts
const provider = computed<OAuthProvider>(() => (route.query.provider === 'qq' ? 'qq' : 'wechat'))
```

替换为：

```ts
function readProvider(): OAuthProvider | null {
  return route.query.provider === 'qq' || route.query.provider === 'wechat' ? route.query.provider : null
}
```

同时从 Vue import 里删除未使用的 `computed`：

```ts
import { onMounted, ref } from 'vue'
```

- [ ] **Step 2: 在 mounted 流程先校验 provider**

把 `onMounted` 开头改为：

```ts
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
```

- [ ] **Step 3: 运行前端构建验证 Vue/TS**

Run:

```bash
corepack pnpm --dir front build
```

Expected:

- PASS。
- 没有 `computed` unused/import 错误。
- 没有 `OAuthProvider | null` 传参类型错误。

---

### Task 4: 最终验证和结果汇报

**Files:**
- Verify only, no source file changes expected.

**Interfaces:**
- Consumes: Task 1-3 的修改。
- Produces: 可交付结果说明。

- [ ] **Step 1: 查看工作区变更**

Run:

```bash
git diff -- front/src/services/index.ts front/src/router/index.ts front/src/views/AuthCallbackView.vue
```

Expected:

- 只包含本计划三处登录维护变更。
- 不包含 unrelated 格式化或 UI 大改。

- [ ] **Step 2: 运行最终前端构建**

Run:

```bash
corepack pnpm --dir front build
```

Expected:

- PASS。

- [ ] **Step 3: 汇报结果**

汇报必须包含：

```md
已完成：
- `/home` 未登录跳 `/login`，已登录访问 `/login` 跳 `/home`。
- service 请求有 token 时自动带 `Authorization`。
- logout 后端失败也会清本地 token。
- OAuth callback provider 只接受 `qq` / `wechat`。

验证：
- `corepack pnpm --dir front build` 通过。或者如失败，贴出失败原因。

未做：
- refresh 自动续期、`/me`、忘记密码、Pinia auth store；等实际需要再加。
```

---

## Self-Review

- Spec coverage: 路由守卫、Authorization header、logout 兜底、OAuth provider 校验、前端 build 验证均有任务覆盖。
- Placeholder scan: 无 TBD/TODO/“稍后实现”。
- Type consistency: `OAuthProvider`、`getAuthTokens()`、`clearAuthTokens()`、`request<T>()` 名称与现有代码一致。
- Scope check: 只触碰 3 个前端文件，不新增依赖，不做 refresh/auth store。
