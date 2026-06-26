# Login Page Visual Refinement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refine the existing login page so the character group sits higher and smaller, the PC form feels less oversized, the center panel transition is softer, and motion feels more natural while preserving the no-scroll single-screen layout.

**Architecture:** This is a focused visual refinement inside the existing single-file Vue component. Only scoped CSS in `front/src/views/LoginView.vue` should change; the template and Vue interaction logic already support the required behavior. Verification is build-based plus a visual/manual check at `/login`.

**Tech Stack:** Vue 3 single-file component, scoped CSS, Vite, TypeScript, pnpm.

---

## File Structure

- Modify: `front/src/views/LoginView.vue`
  - Keep the `<script setup>` and `<template>` unchanged.
  - Update only the `<style scoped>` section.
  - Preserve the existing one-screen layout: `.login-page` must keep `height: 100vh`, `height: 100svh`, and `overflow: hidden`.

---

### Task 1: Soften the two-panel background transition

**Files:**
- Modify: `front/src/views/LoginView.vue:281-314`
- Verify: `corepack pnpm --dir front build`

- [ ] **Step 1: Confirm the current hard split**

Inspect `front/src/views/LoginView.vue` and verify these current declarations exist in the scoped CSS:

```css
.login-page {
  --panel: #ededed;
  --panel-soft: #f7f7f7;
  background: var(--panel);
}

.character-panel {
  background: var(--panel);
}

.form-panel {
  background: var(--panel-soft);
}
```

Expected: The left panel and right panel use separate solid backgrounds, so the center seam reads as a hard transition.

- [ ] **Step 2: Add shared softness tokens and page gradient**

In `.login-page`, add new shadow/transition tokens and replace the flat `background` value with a soft layered background:

```css
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
```

- [ ] **Step 3: Make child panels transparent enough to reveal the transition**

Update panel backgrounds:

```css
.character-panel {
  position: sticky;
  top: 0;
  align-self: start;
  min-height: 100vh;
  height: 100vh;
  background: transparent;
  overflow: hidden;
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
```

- [ ] **Step 4: Run the build**

Run:

```bash
corepack pnpm --dir front build
```

Expected: `vue-tsc -b && vite build` completes with exit code `0`.

---

### Task 2: Raise and scale down the character stage on PC

**Files:**
- Modify: `front/src/views/LoginView.vue:328-398`
- Verify: `corepack pnpm --dir front build`

- [ ] **Step 1: Move the stage line and character group off the bottom edge**

Replace the base `.stage-line` and `.characters` blocks with:

```css
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
```

Expected visual effect: The characters rest on a raised platform instead of touching the viewport bottom.

- [ ] **Step 2: Reduce the base character sizes**

Replace the four base character size blocks with:

```css
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
```

- [ ] **Step 3: Run the build**

Run:

```bash
corepack pnpm --dir front build
```

Expected: Build exits `0`.

---

### Task 3: Make the PC form lighter and less full

**Files:**
- Modify: `front/src/views/LoginView.vue:653-903`
- Verify: `corepack pnpm --dir front build`

- [ ] **Step 1: Reduce card width, padding, and add a soft float**

Replace `.login-card` with:

```css
.login-card {
  width: min(100%, 510px);
  padding: clamp(26px, 3.1vw, 40px);
  background: rgba(255, 255, 255, 0.94);
  border: 1px solid rgba(238, 238, 238, 0.86);
  border-radius: 30px;
  box-shadow: var(--soft-shadow);
  backdrop-filter: blur(8px);
}
```

- [ ] **Step 2: Reduce the main visual rhythm on PC**

Update these base declarations:

```css
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
```

- [ ] **Step 3: Tighten options, buttons, and signup copy**

Update these base declarations:

```css
.form-options {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin: 20px 0;
  font-size: 14px;
}

.remember input {
  width: 21px;
  height: 21px;
  accent-color: #111111;
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
```

- [ ] **Step 4: Run the build**

Run:

```bash
corepack pnpm --dir front build
```

Expected: Build exits `0`.

---

### Task 4: Upgrade motion easing and feedback animations

**Files:**
- Modify: `front/src/views/LoginView.vue:345-626` and `front/src/views/LoginView.vue:905-932`
- Verify: `corepack pnpm --dir front build`

- [ ] **Step 1: Smooth character body and facial transitions**

Update these transition declarations:

```css
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
```

- [ ] **Step 2: Reduce forced fast transition durations during focus moods**

Replace these blocks:

```css
.mood-email .character {
  transition-duration: 180ms;
}

.mood-password .character,
.mood-peek .character {
  transition-duration: 180ms;
}
```

with:

```css
.mood-email .character,
.mood-password .character,
.mood-peek .character {
  transition-duration: 300ms;
}
```

- [ ] **Step 3: Replace shake and bounce keyframes with subtler motion**

Replace `@keyframes shake` and `@keyframes bounce` with:

```css
@keyframes shake {
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

@keyframes bounce {
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
```

- [ ] **Step 4: Improve button hover feedback**

Replace the existing hover block:

```css
.login-button:not(:disabled):hover,
.google-button:hover {
  transform: translateY(-2px);
}
```

with:

```css
.login-button:not(:disabled):hover,
.google-button:hover {
  transform: translateY(-3px);
  box-shadow: 0 14px 28px rgba(20, 20, 20, 0.11);
}
```

- [ ] **Step 5: Run the build**

Run:

```bash
corepack pnpm --dir front build
```

Expected: Build exits `0`.

---

### Task 5: Reconcile responsive overrides and final verification

**Files:**
- Modify: `front/src/views/LoginView.vue:945-1160`
- Verify: `corepack pnpm --dir front build`

- [ ] **Step 1: Keep tablet/mobile overrides compatible with the new base stage position**

In the `@media (max-width: 980px)` block, ensure `.stage-line` and `.characters` retain raised bottoms:

```css
.stage-line {
  bottom: clamp(24px, 4vh, 46px);
}

.characters {
  left: clamp(16px, 6vw, 56px);
  right: 0;
  bottom: clamp(24px, 4vh, 46px);
  height: min(38vw, 286px);
}
```

- [ ] **Step 2: Keep mobile one-screen layout intact**

In the `@media (max-width: 620px)` block, ensure the compact character group also sits above the bottom edge:

```css
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
```

- [ ] **Step 3: Run final build verification**

Run:

```bash
corepack pnpm --dir front build
```

Expected: `vue-tsc -b && vite build` exits `0`.

- [ ] **Step 4: Manual browser verification**

With the dev server running, open:

```text
http://localhost:5173/login
```

Check these items visually:

- The four characters are no longer touching the bottom of the viewport.
- The four characters look smaller than before but still recognizable.
- The login card feels lighter on PC and does not fill the right side too aggressively.
- The center transition between the gray character area and pale form area is soft rather than a hard seam.
- Input focus, password reveal, failed login, successful login, and button hover animations feel smoother and less abrupt.
- There is still no vertical page scrolling.

- [ ] **Step 5: Review the diff**

Run:

```bash
git diff -- front/src/views/LoginView.vue
```

Expected: The diff only changes scoped CSS in `front/src/views/LoginView.vue`. No backend files, route files, or template logic should change.

---

## Self-Review

- Spec coverage: The plan covers character position/scale, PC form scale, center transition detail, motion easing, responsive compatibility, and build/manual verification.
- Placeholder scan: No TBD/TODO/fill-in placeholders remain.
- Type consistency: No TypeScript or Vue API changes are introduced; all changes are scoped CSS declarations in the existing component.
