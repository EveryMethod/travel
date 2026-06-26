<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, reactive, ref } from 'vue'
import { Chrome, Eye, EyeOff } from 'lucide-vue-next'

type Mood = 'idle' | 'email' | 'password' | 'peek' | 'fail' | 'success'

type CharacterTone = 'orange' | 'purple' | 'black' | 'yellow'

interface Character {
  name: string
  tone: CharacterTone
  label: string
}

const characters: Character[] = [
  { name: 'Sunny', tone: 'orange', label: 'Cheerful orange semicircle character' },
  { name: 'Violet', tone: 'purple', label: 'Expressive purple rectangle character' },
  { name: 'Mono', tone: 'black', label: 'Calm black vertical rectangle character' },
  { name: 'Mellow', tone: 'yellow', label: 'Gentle yellow rounded rectangle character' },
]

const form = reactive({
  email: '',
  password: '',
  remember: false,
})

const mood = ref<Mood>('idle')
const passwordVisible = ref(false)
const message = ref('')
const pointer = reactive({ x: 0, y: 0 })
const emailInput = ref<HTMLInputElement | null>(null)
const passwordInput = ref<HTMLInputElement | null>(null)
const characterEls = ref<Array<HTMLElement | null>>([])
let resultTimer: number | undefined

const canSubmit = computed(() => form.email.trim().length > 0 && form.password.length > 0)
const isResultMood = computed(() => mood.value === 'fail' || mood.value === 'success')

function setCharacterRef(el: unknown, index: number) {
  characterEls.value[index] = el instanceof HTMLElement ? el : null
}

function clearResultTimer() {
  if (resultTimer) {
    window.clearTimeout(resultTimer)
    resultTimer = undefined
  }
}

function setMood(nextMood: Mood) {
  clearResultTimer()
  mood.value = nextMood
}

function updatePointer(event: PointerEvent) {
  pointer.x = event.clientX
  pointer.y = event.clientY

  if (isResultMood.value) return

  const activeElement = document.activeElement
  if (!activeElement || !['INPUT', 'BUTTON'].includes(activeElement.tagName)) {
    mood.value = 'idle'
  }
}

function centerOf(el: HTMLElement | null) {
  if (!el) return null

  const rect = el.getBoundingClientRect()
  return {
    x: rect.left + rect.width / 2,
    y: rect.top + rect.height / 2,
  }
}

function targetPoint() {
  if (mood.value === 'email') return centerOf(emailInput.value)
  if (mood.value === 'password' || mood.value === 'peek') return centerOf(passwordInput.value)
  return null
}

function characterStyle(index: number) {
  const el = characterEls.value[index]
  const point = targetPoint() ?? pointer

  if (!el || !point.x) {
    return {
      '--eye-x': '0px',
      '--eye-y': '0px',
      '--turn': '0deg',
      '--lean': '0px',
      '--lift': '0px',
    }
  }

  const rect = el.getBoundingClientRect()
  const originX = rect.left + rect.width / 2
  const originY = rect.top + rect.height * 0.32
  const dx = point.x - originX
  const dy = point.y - originY
  const distance = Math.max(Math.hypot(dx, dy), 1)
  const focusBoost = mood.value === 'email' || mood.value === 'password' || mood.value === 'peek'
  const maxX = focusBoost ? 10 : 6
  const maxY = focusBoost ? 7 : 4
  const turnLimit = focusBoost ? 11 : 7

  return {
    '--eye-x': `${(dx / distance) * maxX}px`,
    '--eye-y': `${(dy / distance) * maxY}px`,
    '--turn': `${Math.max(Math.min(dx / 38, turnLimit), -turnLimit)}deg`,
    '--lean': mood.value === 'password' || mood.value === 'peek' ? '12px' : '0px',
    '--lift': mood.value === 'email' ? '-4px' : '0px',
  }
}

function focusEmail() {
  message.value = ''
  setMood('email')
}

function focusPassword() {
  message.value = ''
  setMood(passwordVisible.value ? 'peek' : 'password')
}

function blurField() {
  if (!isResultMood.value) mood.value = 'idle'
}

async function togglePassword() {
  passwordVisible.value = !passwordVisible.value
  setMood(passwordVisible.value ? 'peek' : 'password')
  await nextTick()
  passwordInput.value?.focus()
}

function submitLogin() {
  if (!canSubmit.value) return

  if (form.email.includes('@') && form.password === 'travel123') {
    mood.value = 'success'
    message.value = 'Login successful. Welcome back!'
  } else {
    mood.value = 'fail'
    message.value = 'Login failed. Try travel123 as the demo password.'
  }

  clearResultTimer()
  resultTimer = window.setTimeout(() => {
    if (document.activeElement === passwordInput.value) {
      mood.value = passwordVisible.value ? 'peek' : 'password'
      return
    }

    if (document.activeElement === emailInput.value) {
      mood.value = 'email'
      return
    }

    mood.value = 'idle'
  }, 2200)
}

onMounted(() => {
  pointer.x = window.innerWidth * 0.28
  pointer.y = window.innerHeight * 0.36
})

onUnmounted(() => {
  clearResultTimer()
  characterEls.value = []
})
</script>

<template>
  <main class="login-page" :class="`mood-${mood}`" @pointermove="updatePointer">
    <section class="character-panel" aria-label="Animated login characters">
      <div class="panel-copy" aria-hidden="true">
        <p>Four tiny guardians are watching the form with you.</p>
      </div>

      <div class="stage-line" aria-hidden="true"></div>

      <div class="characters" aria-hidden="true">
        <div
          v-for="(character, index) in characters"
          :key="character.name"
          :ref="(el) => setCharacterRef(el, index)"
          class="character"
          :class="[character.tone, `character-${index + 1}`]"
          :style="characterStyle(index)"
          :aria-label="character.label"
        >
          <div class="face">
            <span class="eye left-eye"><span></span></span>
            <span class="eye right-eye"><span></span></span>
            <span class="mouth"></span>
          </div>
        </div>
      </div>
    </section>

    <section class="form-panel" aria-label="Login form">
      <form class="login-card" @submit.prevent="submitLogin">
        <div class="brand-mark" aria-hidden="true">
          <span></span>
        </div>

        <div class="title-block">
          <h1>Welcome back!</h1>
          <p>Please enter your details.</p>
        </div>

        <label class="field" for="login-email">
          <span>Email</span>
          <input
            id="login-email"
            ref="emailInput"
            v-model="form.email"
            type="email"
            autocomplete="email"
            placeholder="Enter your email"
            @focus="focusEmail"
            @blur="blurField"
          />
        </label>

        <label class="field password-field" for="login-password">
          <span>Password</span>
          <div class="password-row">
            <input
              id="login-password"
              ref="passwordInput"
              v-model="form.password"
              :type="passwordVisible ? 'text' : 'password'"
              autocomplete="current-password"
              placeholder="Enter your password"
              @focus="focusPassword"
              @blur="blurField"
            />
            <button
              class="eye-button"
              type="button"
              :aria-label="passwordVisible ? 'Hide password' : 'Show password'"
              @click="togglePassword"
            >
              <EyeOff v-if="passwordVisible" :size="22" stroke-width="2.25" />
              <Eye v-else :size="22" stroke-width="2.25" />
            </button>
          </div>
        </label>

        <div class="form-options">
          <label class="remember">
            <input v-model="form.remember" type="checkbox" />
            <span>Remember me</span>
          </label>
          <a href="#" @click.prevent>Forgot password?</a>
        </div>

        <p v-if="message" class="login-message" :class="mood" role="status" aria-live="polite">
          {{ message }}
        </p>

        <button class="login-button" type="submit" :disabled="!canSubmit">Log In</button>

        <button class="google-button" type="button">
          <Chrome :size="24" stroke-width="2.25" />
          <span>Log in with Google</span>
        </button>

        <p class="signup-copy">Don't have an account? <a href="#">Sign Up</a></p>
      </form>
    </section>
  </main>
</template>

<style scoped>
.login-page {
  --ink: #141414;
  --muted: #75757b;
  --paper: #ffffff;
  --panel: #ededed;
  --panel-soft: #f7f7f7;
  --line: #d8d8d8;
  --seam-glow: rgba(255, 255, 255, 0.66);
  --soft-shadow: 0 24px 70px rgba(18, 18, 18, 0.08);
  height: 100vh;
  height: 100svh;
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(0, 1.12fr) minmax(430px, 0.88fr);
  overflow: hidden;
  background:
    radial-gradient(circle at 54% 48%, var(--seam-glow) 0 9%, rgba(255, 255, 255, 0) 31%),
    linear-gradient(90deg, var(--panel) 0 49%, #f2f2f1 58%, var(--panel-soft) 100%);
  color: var(--ink);
  font-family:
    Inter,
    ui-sans-serif,
    system-ui,
    -apple-system,
    BlinkMacSystemFont,
    "Segoe UI",
    sans-serif;
}

.character-panel {
  position: sticky;
  top: 0;
  align-self: start;
  min-height: 100vh;
  height: 100vh;
  background: transparent;
  overflow: hidden;
}

.panel-copy {
  position: absolute;
  left: clamp(28px, 5vw, 72px);
  top: clamp(26px, 5vw, 66px);
  width: min(310px, 42vw);
  color: #8a8a8e;
  font-size: 15px;
  font-weight: 750;
  letter-spacing: -0.01em;
  line-height: 1.5;
}

.stage-line {
  position: absolute;
  left: clamp(24px, 9vw, 120px);
  right: 12%;
  bottom: clamp(38px, 6vh, 74px);
  height: 7px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.92);
  box-shadow: 0 18px 42px rgba(20, 20, 20, 0.1);
}

.characters {
  position: absolute;
  left: clamp(32px, 11vw, 150px);
  right: 8%;
  bottom: clamp(38px, 6vh, 74px);
  height: min(42vw, 378px);
}

.character {
  position: absolute;
  bottom: 0;
  transform: translateY(calc(var(--lean) + var(--lift))) rotate(var(--turn));
  transform-origin: 50% 92%;
  transition:
    transform 360ms cubic-bezier(0.16, 1, 0.3, 1),
    border-radius 320ms cubic-bezier(0.22, 1, 0.36, 1);
  will-change: transform;
}

.character::after {
  content: "";
  position: absolute;
  left: 16%;
  right: 16%;
  bottom: -2px;
  height: 12px;
  background: inherit;
}

.orange {
  left: 0;
  width: clamp(148px, 14.5vw, 218px);
  height: clamp(100px, 10vw, 150px);
  background: #ff6a2f;
  border-radius: 999px 999px 0 0;
  z-index: 4;
}

.purple {
  left: clamp(128px, 13vw, 220px);
  width: clamp(90px, 8.9vw, 140px);
  height: clamp(226px, 23.8vw, 356px);
  background: #8431cf;
  z-index: 2;
}

.black {
  left: clamp(216px, 21.5vw, 342px);
  width: clamp(70px, 6.4vw, 106px);
  height: clamp(162px, 15.4vw, 248px);
  background: #151515;
  z-index: 5;
}

.yellow {
  left: clamp(282px, 27.5vw, 436px);
  width: clamp(82px, 7.7vw, 122px);
  height: clamp(156px, 15.4vw, 244px);
  background: #ffd521;
  border-radius: clamp(22px, 2.6vw, 36px) clamp(22px, 2.6vw, 36px) 10px 10px;
  z-index: 3;
}

.face {
  position: absolute;
  inset: 0;
}

.eye {
  position: absolute;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: #ffffff;
  transition:
    height 260ms cubic-bezier(0.22, 1, 0.36, 1),
    width 260ms cubic-bezier(0.22, 1, 0.36, 1),
    transform 280ms cubic-bezier(0.16, 1, 0.3, 1),
    background 220ms ease;
}

.eye span {
  position: absolute;
  left: 8px;
  top: 8px;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #141414;
  transform: translate(var(--eye-x), var(--eye-y));
  transition:
    transform 180ms cubic-bezier(0.16, 1, 0.3, 1),
    opacity 180ms ease,
    width 220ms cubic-bezier(0.22, 1, 0.36, 1),
    height 220ms cubic-bezier(0.22, 1, 0.36, 1);
}

.orange .left-eye {
  left: 43%;
  top: 30%;
}

.orange .right-eye {
  left: 58%;
  top: 30%;
}

.purple .left-eye {
  left: 37%;
  top: 13%;
}

.purple .right-eye {
  left: 59%;
  top: 13%;
}

.black .left-eye {
  left: 33%;
  top: 19%;
}

.black .right-eye {
  left: 58%;
  top: 19%;
}

.yellow .left-eye {
  left: 30%;
  top: 21%;
}

.yellow .right-eye {
  left: 54%;
  top: 21%;
}

.black .eye span {
  width: 9px;
  height: 9px;
}

.mouth {
  position: absolute;
  width: 26px;
  height: 12px;
  border-bottom: 4px solid #121212;
  border-radius: 0 0 24px 24px;
  transition:
    transform 280ms cubic-bezier(0.16, 1, 0.3, 1),
    border-radius 260ms cubic-bezier(0.22, 1, 0.36, 1),
    height 260ms cubic-bezier(0.22, 1, 0.36, 1),
    width 260ms cubic-bezier(0.22, 1, 0.36, 1),
    border-color 220ms ease,
    border-width 220ms ease;
}

.orange .mouth {
  left: 50%;
  top: 53%;
}

.purple .mouth {
  left: 48%;
  top: 22%;
  width: 21px;
  height: 6px;
  border-bottom-width: 3px;
  border-radius: 0 0 2px 2px;
  transform: rotate(-8deg);
}

.black .mouth {
  left: 49%;
  top: 32%;
  width: 13px;
  height: 13px;
  border: 4px solid #ffffff;
  border-radius: 50%;
}

.yellow .mouth {
  left: 38%;
  top: 34%;
  width: 30px;
  height: 0;
  border-radius: 0;
}

.mood-email .character,
.mood-password .character,
.mood-peek .character {
  transition-duration: 300ms;
}

.mood-email .eye {
  width: 31px;
  height: 31px;
}

.mood-email .eye span,
.mood-password .eye span,
.mood-peek .orange .eye span {
  left: 10px;
  top: 10px;
}

.mood-email .purple .mouth {
  width: 28px;
  border-radius: 0 0 999px 999px;
  transform: rotate(0deg);
}

.mood-password .eye {
  width: 29px;
  height: 29px;
}

.mood-password .mouth {
  transform: scaleX(0.88);
}

.mood-password .black .mouth {
  transform: scale(1.12);
}

.mood-peek .character:not(.orange) .eye {
  height: 4px;
  border-radius: 999px;
  transform: translateY(8px);
}

.mood-peek .character:not(.orange) .eye span {
  opacity: 0;
}

.mood-peek .orange .eye {
  width: 33px;
  height: 33px;
}

.mood-peek .orange .mouth {
  width: 18px;
  height: 18px;
  border: 4px solid #121212;
  border-radius: 50%;
}

.mood-peek .character:not(.orange) .mouth {
  width: 26px;
  height: 0;
  border-bottom: 4px solid #121212;
  border-radius: 0;
}

.mood-peek .black .mouth {
  border-bottom-color: #ffffff;
}

.mood-fail .character {
  animation: login-character-shake 520ms ease-in-out;
}

.mood-fail .eye {
  height: 10px;
  border-radius: 999px;
  transform: translateY(6px);
}

.mood-fail .eye span {
  opacity: 0;
}

.mood-fail .mouth {
  height: 16px;
  border-top: 4px solid #111111;
  border-bottom: 0;
  border-radius: 24px 24px 0 0;
  transform: translateY(8px);
}

.mood-fail .black .mouth {
  width: 22px;
  height: 12px;
  border: 0;
  border-top: 4px solid #ffffff;
  border-radius: 24px 24px 0 0;
}

.mood-success .character {
  animation: login-character-bounce 640ms ease;
}

.mood-success .eye {
  height: 8px;
  border-radius: 999px;
  transform: translateY(6px);
}

.mood-success .eye span {
  opacity: 0;
}

.mood-success .mouth {
  height: 14px;
  border-bottom-width: 4px;
  border-radius: 0 0 999px 999px;
}

.mood-success .black .mouth {
  width: 22px;
  height: 12px;
  border: 0;
  border-bottom: 4px solid #ffffff;
  border-radius: 0 0 999px 999px;
}

.form-panel {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  padding: clamp(24px, 3.4vw, 46px);
  background:
    linear-gradient(90deg, rgba(247, 247, 247, 0.46), rgba(247, 247, 247, 0.92) 42%, var(--panel-soft));
}

.login-card {
  width: min(100%, 510px);
  padding: clamp(26px, 3.1vw, 40px);
  background: rgba(255, 255, 255, 0.94);
  border: 1px solid rgba(238, 238, 238, 0.86);
  border-radius: 30px;
  box-shadow: var(--soft-shadow);
  backdrop-filter: blur(8px);
}

.brand-mark {
  display: grid;
  place-items: center;
  width: 52px;
  height: 52px;
  border-radius: 50%;
  background: #000000;
}

.brand-mark span {
  width: 22px;
  height: 22px;
  background: #ffffff;
  transform: rotate(45deg);
}

.title-block {
  margin: 28px 0 34px;
}

.title-block h1 {
  margin: 0;
  color: #11131b;
  font-size: clamp(34px, 3vw, 42px);
  font-weight: 900;
  letter-spacing: -0.045em;
  line-height: 0.98;
  white-space: nowrap;
}

.title-block p {
  margin: 12px 0 0;
  color: var(--muted);
  font-size: 19px;
  line-height: 1.4;
}

.field {
  display: block;
  margin-top: 22px;
}

.field > span {
  display: block;
  margin-bottom: 12px;
  color: #3a3a42;
  font-size: 16px;
  font-weight: 850;
}

.field input {
  width: 100%;
  min-height: 44px;
  border: 0;
  border-bottom: 2px solid var(--line);
  border-radius: 0;
  padding: 8px 0;
  color: #141414;
  background: transparent;
  font-size: 18px;
  line-height: 1.2;
  outline: none;
  transition:
    border-color 240ms cubic-bezier(0.22, 1, 0.36, 1),
    color 240ms cubic-bezier(0.22, 1, 0.36, 1);
}

.field input::placeholder {
  color: #85858a;
}

.field input:focus {
  border-color: #111111;
}

.password-row {
  display: flex;
  align-items: center;
  gap: 12px;
  border-bottom: 2px solid var(--line);
  transition: border-color 180ms ease;
}

.password-row:focus-within {
  border-color: #111111;
}

.password-row input {
  border: 0;
}

.eye-button {
  display: grid;
  place-items: center;
  flex: 0 0 44px;
  width: 44px;
  height: 44px;
  border: 0;
  border-radius: 50%;
  color: #9b9ba0;
  background: transparent;
  cursor: pointer;
  transition:
    color 180ms ease,
    background 180ms ease,
    transform 180ms ease;
}

.eye-button:hover {
  color: #111111;
  background: #eeeeee;
}

.eye-button:focus-visible {
  color: #111111;
  background: #f2ecfb;
  outline: 3px solid #8431cf;
  outline-offset: 3px;
}

.eye-button:active {
  transform: scale(0.94);
}

.form-options {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin: 20px 0;
  font-size: 14px;
}

.remember {
  display: inline-flex;
  align-items: center;
  gap: 12px;
  color: #4d4d55;
  white-space: nowrap;
}

.remember input {
  width: 21px;
  height: 21px;
  accent-color: #111111;
}

.form-options a,
.signup-copy a {
  color: #111111;
  font-weight: 850;
  text-decoration: none;
  white-space: nowrap;
}

.form-options a {
  color: #5f5f66;
  font-weight: 750;
}

.form-options a:hover,
.form-options a:focus-visible,
.signup-copy a:hover,
.signup-copy a:focus-visible {
  text-decoration: underline;
  text-underline-offset: 4px;
}

.form-options a:focus-visible,
.signup-copy a:focus-visible {
  outline: 3px solid #8431cf;
  outline-offset: 3px;
  border-radius: 6px;
}

.login-message {
  min-height: 44px;
  margin: 0 0 16px;
  padding: 12px 16px;
  border-radius: 14px;
  font-weight: 850;
}

.login-message.fail {
  color: #9b211d;
  background: #ffe8e6;
}

.login-message.success {
  color: #176d36;
  background: #e5f7eb;
}

.login-button,
.google-button {
  width: 100%;
  min-height: 56px;
  border-radius: 999px;
  font-size: 18px;
  font-weight: 900;
  cursor: pointer;
  transition:
    transform 260ms cubic-bezier(0.22, 1, 0.36, 1),
    box-shadow 260ms cubic-bezier(0.22, 1, 0.36, 1),
    background 220ms ease,
    border-color 220ms ease,
    opacity 220ms ease;
}

.login-button {
  border: 0;
  color: #ffffff;
  background: #181818;
}

.login-button:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}

.login-button:focus-visible,
.google-button:focus-visible,
.remember input:focus-visible {
  outline: 3px solid #8431cf;
  outline-offset: 3px;
}

.login-button:not(:disabled):hover,
.google-button:hover {
  transform: translateY(-3px);
  box-shadow: 0 14px 28px rgba(20, 20, 20, 0.11);
}

.google-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  margin-top: 22px;
  color: #111111;
  background: #ffffff;
  border: 2px solid #e6e6e6;
}

.signup-copy {
  margin: 26px 0 0;
  color: var(--muted);
  font-size: 16px;
  text-align: center;
}

@keyframes login-character-shake {
  0%,
  100% {
    transform: translateY(calc(var(--lean) + var(--lift))) rotate(var(--turn));
  }
  18% {
    transform: translate(-5px, calc(var(--lean) + var(--lift) - 1px)) rotate(calc(var(--turn) - 2.5deg));
  }
  42% {
    transform: translate(4px, calc(var(--lean) + var(--lift))) rotate(calc(var(--turn) + 2deg));
  }
  68% {
    transform: translate(-2px, calc(var(--lean) + var(--lift))) rotate(calc(var(--turn) - 1deg));
  }
}

@keyframes login-character-bounce {
  0%,
  100% {
    transform: translateY(calc(var(--lean) + var(--lift))) rotate(var(--turn));
  }
  34% {
    transform: translateY(calc(var(--lean) + var(--lift) - 18px)) rotate(var(--turn));
  }
  62% {
    transform: translateY(calc(var(--lean) + var(--lift) - 6px)) rotate(var(--turn));
  }
}

@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    scroll-behavior: auto !important;
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }

  .mood-fail .character,
  .mood-success .character {
    animation: none !important;
  }

  .login-button:not(:disabled):hover,
  .google-button:hover {
    transform: none;
    box-shadow: none;
  }
}

@media (max-width: 980px) {
  .login-page {
    grid-template-columns: minmax(0, 0.86fr) minmax(340px, 1.14fr);
  }

  .panel-copy {
    left: clamp(18px, 3vw, 30px);
    top: clamp(18px, 3vw, 30px);
    width: min(240px, 34vw);
    font-size: 13px;
  }

  .stage-line {
    bottom: clamp(24px, 4vh, 46px);
  }

  .characters {
    left: clamp(16px, 6vw, 56px);
    right: 0;
    bottom: clamp(24px, 4vh, 46px);
    height: min(38vw, 286px);
  }

  .orange {
    width: clamp(116px, 16vw, 160px);
    height: clamp(78px, 10.6vw, 108px);
  }

  .purple {
    left: clamp(96px, 13vw, 132px);
    width: clamp(70px, 9vw, 96px);
    height: clamp(176px, 24vw, 246px);
  }

  .black {
    left: clamp(160px, 22vw, 220px);
    width: clamp(54px, 7vw, 74px);
    height: clamp(128px, 17vw, 178px);
  }

  .yellow {
    left: clamp(210px, 28vw, 284px);
    width: clamp(62px, 8vw, 84px);
    height: clamp(124px, 17vw, 174px);
  }

  .form-panel {
    min-height: 0;
    padding: clamp(14px, 2vw, 22px);
  }

  .login-card {
    padding: clamp(20px, 2.5vw, 28px);
    border-radius: 24px;
  }

  .brand-mark {
    width: 46px;
    height: 46px;
  }

  .brand-mark span {
    width: 20px;
    height: 20px;
  }

  .title-block {
    margin: 22px 0 26px;
  }

  .title-block h1 {
    font-size: clamp(30px, 4vw, 38px);
  }

  .title-block p {
    margin-top: 8px;
    font-size: 17px;
  }

  .field {
    margin-top: 18px;
  }

  .field > span {
    margin-bottom: 8px;
    font-size: 15px;
  }

  .field input {
    min-height: 40px;
    font-size: 17px;
  }

  .form-options {
    margin: 16px 0;
  }

  .login-button,
  .google-button {
    min-height: 50px;
    font-size: 17px;
  }

  .google-button {
    margin-top: 16px;
  }

  .signup-copy {
    margin-top: 18px;
    font-size: 15px;
  }
}

@media (max-width: 620px) {
  .login-page {
    grid-template-columns: minmax(86px, 0.26fr) minmax(0, 1fr);
  }

  .panel-copy {
    display: none;
  }

  .stage-line {
    left: 14px;
    right: 0;
    bottom: 20px;
  }

  .characters {
    left: 10px;
    right: auto;
    bottom: 20px;
    width: 330px;
    height: 260px;
    transform: scale(0.34);
    transform-origin: left bottom;
  }

  .form-panel {
    padding: 10px;
  }

  .login-card {
    padding: 18px;
    border-radius: 20px;
  }

  .brand-mark {
    width: 40px;
    height: 40px;
  }

  .brand-mark span {
    width: 17px;
    height: 17px;
  }

  .title-block {
    margin: 16px 0 20px;
  }

  .title-block h1 {
    font-size: clamp(26px, 8vw, 32px);
    white-space: normal;
  }

  .title-block p {
    font-size: 15px;
  }

  .field {
    margin-top: 14px;
  }

  .field > span {
    margin-bottom: 6px;
    font-size: 14px;
  }

  .field input {
    min-height: 36px;
    font-size: 15px;
  }

  .eye-button {
    flex-basis: 38px;
    width: 38px;
    height: 38px;
  }

  .form-options {
    align-items: flex-start;
    flex-wrap: wrap;
    margin: 12px 0;
    font-size: 13px;
  }

  .remember,
  .form-options a {
    white-space: normal;
  }

  .remember {
    gap: 8px;
  }

  .remember input {
    width: 18px;
    height: 18px;
  }

  .login-message {
    min-height: 36px;
    margin-bottom: 10px;
    padding: 9px 12px;
    font-size: 13px;
  }

  .login-button,
  .google-button {
    min-height: 44px;
    font-size: 15px;
  }

  .google-button {
    gap: 10px;
    margin-top: 12px;
  }

  .signup-copy {
    margin-top: 12px;
    font-size: 13px;
  }
}

@media (min-width: 621px) and (max-width: 980px) and (max-height: 760px) {
  .stage-line {
    right: 6%;
  }

  .characters {
    left: clamp(10px, 4vw, 34px);
    right: auto;
    width: 290px;
    height: 228px;
    transform: scale(0.82);
    transform-origin: left bottom;
  }
}

@media (min-width: 981px) and (max-height: 760px) {
  .form-panel {
    align-items: stretch;
    padding: clamp(18px, 3vh, 28px) clamp(22px, 3vw, 34px);
  }

  .login-card {
    align-self: center;
    width: min(100%, 480px);
    padding: clamp(20px, 2.4vh, 28px) clamp(24px, 2.6vw, 32px);
    border-radius: 26px;
  }

  .brand-mark {
    width: 46px;
    height: 46px;
  }

  .brand-mark span {
    width: 19px;
    height: 19px;
  }

  .title-block {
    margin: 18px 0 22px;
  }

  .title-block h1 {
    font-size: clamp(30px, 2.8vw, 38px);
  }

  .title-block p {
    margin-top: 8px;
    font-size: 17px;
  }

  .field {
    margin-top: 16px;
  }

  .field > span {
    margin-bottom: 8px;
  }

  .field input {
    min-height: 40px;
    font-size: 17px;
  }

  .password-row {
    gap: 10px;
  }

  .eye-button {
    flex-basis: 40px;
    width: 40px;
    height: 40px;
  }

  .form-options {
    margin: 14px 0;
  }

  .login-message {
    min-height: 38px;
    margin-bottom: 12px;
    padding: 10px 14px;
  }

  .login-button,
  .google-button {
    min-height: 48px;
    font-size: 17px;
  }

  .google-button {
    margin-top: 16px;
  }

  .signup-copy {
    margin-top: 18px;
    font-size: 15px;
  }
}

@media (max-width: 760px) and (max-height: 760px) {
  .form-panel {
    padding: 8px;
  }

  .login-card {
    padding: 16px;
    border-radius: 18px;
  }

  .brand-mark {
    width: 36px;
    height: 36px;
  }

  .brand-mark span {
    width: 15px;
    height: 15px;
  }

  .title-block {
    margin: 12px 0 16px;
  }

  .title-block h1 {
    font-size: clamp(23px, 6.4vw, 28px);
    line-height: 1;
  }

  .title-block p {
    margin-top: 6px;
    font-size: 14px;
  }

  .field {
    margin-top: 11px;
  }

  .field > span {
    margin-bottom: 5px;
    font-size: 13px;
  }

  .field input {
    min-height: 34px;
    padding: 6px 0;
    font-size: 14px;
  }

  .password-row {
    gap: 10px;
  }

  .eye-button {
    flex-basis: 36px;
    width: 36px;
    height: 36px;
  }

  .form-options {
    margin: 10px 0;
    gap: 8px;
    font-size: 12px;
  }

  .remember {
    gap: 7px;
  }

  .remember input {
    width: 17px;
    height: 17px;
  }

  .login-message {
    min-height: 32px;
    margin-bottom: 8px;
    padding: 8px 10px;
    font-size: 12px;
  }

  .login-button,
  .google-button {
    min-height: 40px;
    font-size: 14px;
  }

  .google-button {
    gap: 8px;
    margin-top: 10px;
  }

  .signup-copy {
    margin-top: 10px;
    font-size: 12px;
  }
}

@media (max-width: 620px) and (max-height: 700px) {
  .login-page {
    grid-template-columns: minmax(78px, 0.24fr) minmax(0, 1fr);
  }

  .stage-line {
    left: 10px;
    bottom: 14px;
  }

  .characters {
    left: 6px;
    bottom: 14px;
    transform: scale(0.28);
  }

  .form-panel {
    padding: 7px;
  }

  .login-card {
    padding: 14px;
    border-radius: 18px;
  }
}

@media (max-width: 620px) and (max-height: 620px) {
  .login-page {
    grid-template-columns: minmax(72px, 0.22fr) minmax(0, 1fr);
  }

  .characters {
    left: 4px;
    bottom: 10px;
    transform: scale(0.24);
  }

  .title-block {
    margin: 10px 0 14px;
  }

  .field {
    margin-top: 9px;
  }

  .form-options {
    margin: 8px 0;
  }

  .signup-copy {
    margin-top: 8px;
  }
}

@media (max-width: 380px) {
  .login-page {
    grid-template-columns: 86px minmax(0, 1fr);
  }

  .stage-line {
    left: 8px;
    bottom: 16px;
  }

  .characters {
    left: 2px;
    bottom: 16px;
    width: 300px;
    height: 236px;
    transform: scale(0.24);
    transform-origin: left bottom;
  }

  .login-card {
    padding: 14px;
  }

  .title-block h1 {
    font-size: clamp(22px, 9vw, 27px);
  }

  .field input {
    font-size: 14px;
  }
}

@media (max-width: 380px) and (max-height: 700px) {
  .login-page {
    grid-template-columns: 80px minmax(0, 1fr);
  }

  .characters {
    left: 0;
    bottom: 12px;
    transform: scale(0.21);
  }

  .form-panel {
    padding: 6px;
  }

  .login-card {
    padding: 12px;
    border-radius: 16px;
  }

  .brand-mark {
    width: 34px;
    height: 34px;
  }

  .brand-mark span {
    width: 14px;
    height: 14px;
  }

  .title-block {
    margin: 8px 0 12px;
  }

  .title-block h1 {
    font-size: 21px;
  }

  .title-block p {
    margin-top: 4px;
    font-size: 13px;
  }

  .field > span {
    font-size: 12px;
  }

  .field input {
    min-height: 32px;
    padding: 5px 0;
    font-size: 13px;
  }

  .eye-button {
    flex-basis: 34px;
    width: 34px;
    height: 34px;
  }

  .login-button,
  .google-button {
    min-height: 38px;
    font-size: 13px;
  }

  .google-button {
    margin-top: 8px;
  }

  .signup-copy {
    font-size: 12px;
  }
}
</style>
