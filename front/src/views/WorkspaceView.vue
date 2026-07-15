<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import TripList from '@/components/TripList.vue'
import { deleteTrip, listTrips, logout } from '@/services'
import type { SavedTripListItem } from '@/types'

const router = useRouter()
const trips = ref<SavedTripListItem[]>([])
const isLoading = ref(false)
const error = ref('')

async function loadTrips() {
  error.value = ''
  isLoading.value = true
  try {
    trips.value = await listTrips()
  } catch (caughtError) {
    error.value = caughtError instanceof Error ? caughtError.message : '工作台加载失败，请稍后重试。'
  } finally {
    isLoading.value = false
  }
}

async function removeTrip(trip: SavedTripListItem) {
  if (!window.confirm(`删除 ${trip.destination} 的 ${trip.days} 天游程？`)) return

  try {
    await deleteTrip(trip.id)
    trips.value = trips.value.filter((item) => item.id !== trip.id)
  } catch (caughtError) {
    error.value = caughtError instanceof Error ? caughtError.message : '删除失败，请稍后重试。'
  }
}

async function logoutAndReturn() {
  await logout()
  await router.push('/login')
}

onMounted(loadTrips)
</script>

<template>
  <main class="min-h-screen bg-[#f6f5f4] text-[#1a1a1a] [font-family:Inter,-apple-system,BlinkMacSystemFont,'Segoe_UI','PingFang_SC','Microsoft_YaHei',sans-serif]">
    <header class="border-b border-[#e5e3df] bg-white">
      <div class="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-4 sm:px-6 lg:px-8">
        <RouterLink to="/home" class="text-sm font-semibold text-[#0a1530]">远行手稿</RouterLink>
        <button type="button" class="rounded-md border border-[#c8c4be] px-3 py-2 text-sm font-medium hover:bg-[#f6f5f4]" @click="logoutAndReturn">
          退出登录
        </button>
      </div>
    </header>

    <section class="mx-auto max-w-6xl px-4 py-8 sm:px-6 lg:px-8">
      <TripList :trips="trips" :is-loading="isLoading" :error="error" @retry="loadTrips" @delete="removeTrip" />
    </section>
  </main>
</template>
