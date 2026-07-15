# Login Maintenance Design

Date: 2026-07-14

## Scope

Do the smallest maintenance pass that makes the existing login flow safer and less fragile. Do not redesign authentication, add new account features, or introduce a frontend auth store.

Included:

1. Route guard for login/home access.
2. Automatic `Authorization: Bearer ...` header for service requests when an access token exists.
3. Logout that always clears local tokens, even if the backend request fails.
4. Explicit OAuth callback provider validation for `qq` and `wechat`.
5. Frontend build verification.

Excluded for now:

- Refresh-token retry flow.
- `/api/auth/me` profile endpoint.
- Forgot-password and password-reset flows.
- Pinia auth store.
- Account settings/profile page.

## Current Context

Frontend login state already exists in `front/src/services/index.ts` through `getAuthTokens`, `saveAuthTokens`, `clearAuthTokens`, and `isAuthRemembered`.

Routes are defined in `front/src/router/index.ts`, but there is no navigation guard. `/home` can be opened without local auth tokens, and `/login` stays reachable after login.

Most API calls go through the shared `request()` helper in `front/src/services/index.ts`. That is the right place to attach an access token once, instead of adding headers at each call site.

OAuth callback currently infers the provider by treating every non-`qq` query value as `wechat`. That should fail closed instead.

## Design

### 1. Route guard

Add `router.beforeEach` in `front/src/router/index.ts`.

Rules:

- If target route is `/home` and `getAuthTokens()` returns `null`, redirect to `/login`.
- If target route is `/login` or `/` and tokens exist, redirect to `/home`.
- Allow `/auth/callback` without auth because OAuth needs it.

Implementation should reuse existing `getAuthTokens()` from `@/services`.

No Pinia store is needed for this pass. Local token presence is the existing source of truth.

### 2. Shared Authorization header

Update `request()` in `front/src/services/index.ts`.

Rules:

- Read tokens with `getAuthTokens()`.
- If an access token exists, add `Authorization: Bearer <access_token>`.
- Preserve caller-provided headers, with caller headers taking precedence.
- Keep current JSON body behavior.

This keeps the change centralized and avoids touching each service function.

### 3. Logout local-token fallback

Update `logout()` in `front/src/services/index.ts`.

Rules:

- If tokens exist, attempt backend logout as today.
- Always call `clearAuthTokens()` in `finally`.
- Do not block UI logout on backend/network failure.

This matches user intent: clicking logout should make the frontend logged out immediately.

### 4. OAuth callback provider validation

Update `front/src/views/AuthCallbackView.vue`.

Rules:

- Read `route.query.provider`.
- Accept only `qq` or `wechat`.
- If missing/invalid, notify opener with an OAuth error and show an error message.
- Do not call `completeOAuthLogin()` with an inferred fallback provider.

### 5. Verification

Run:

```bash
corepack pnpm --dir front build
```

If the build fails because dependencies are missing, report that directly and do not claim verification passed.

## Success Criteria

- Direct `/home` visit without local auth token redirects to `/login`.
- Existing login/register/OAuth success still stores tokens and navigates to `/home`.
- Shared API requests include the access token when present.
- Logout clears local tokens even if backend logout fails.
- OAuth callback with an invalid provider reports an error instead of defaulting to WeChat.
- Frontend build passes or any failure is reported with the relevant output.
