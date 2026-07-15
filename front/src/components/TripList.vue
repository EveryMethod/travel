<script setup lang="ts">
import { RouterLink } from 'vue-router'
import type { SavedTripListItem } from '@/types'

defineProps<{
  trips: SavedTripListItem[]
  isLoading: boolean
  error: string
}>()

const emit = defineEmits<{
  retry: []
  delete: [trip: SavedTripListItem]
}>()

function formatDate(value: string): string {
  return new Intl.DateTimeFormat('zh-CN', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value))
}
</script>

<template>
  <div class="rounded-xl border border-[#e5e3df] bg-white p-5">
    <div class="mb-5 flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
      <div>
        <p class="text-xs font-semibold uppercase text-[#5645d4]">Workspace</p>
        <h2 class="mt-2 text-2xl font-semibold">我的行程</h2>
      </div>
      <RouterLink to="/home" class="inline-flex min-h-10 items-center justify-center rounded-md bg-[#5645d4] px-4 py-2 text-sm font-medium text-white hover:bg-[#4534b3]">
        新建规划
      </RouterLink>
    </div>

    <p v-if="error" class="rounded-md border border-[#e03131]/30 bg-[#fde0ec] px-3 py-2 text-sm font-medium text-[#a02e6d]" role="alert">
      {{ error }}
      <button type="button" class="ml-2 underline" @click="emit('retry')">重试</button>
    </p>

    <p v-else-if="isLoading" class="rounded-md bg-[#fafaf9] px-3 py-8 text-center text-sm text-[#5d5b54]">
      正在加载行程...
    </p>

    <p v-else-if="trips.length === 0" class="rounded-md bg-[#fafaf9] px-3 py-8 text-center text-sm text-[#5d5b54]">
      还没有保存的行程。先新建一次规划。
    </p>

    <div v-else class="grid gap-3">
      <article v-for="trip in trips" :key="trip.id" class="grid gap-3 rounded-xl border border-[#e5e3df] p-4 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center">
        <div>
          <div class="flex flex-wrap items-center gap-2">
            <h3 class="text-lg font-semibold">{{ trip.destination }}</h3>
            <span class="rounded bg-[#d9f3e1] px-2 py-1 text-xs font-semibold text-[#1a1a1a]">{{ trip.status === 'completed' ? '已完成' : trip.status }}</span>
          </div>
          <p class="mt-2 text-sm text-[#5d5b54]">{{ trip.days }} 天 · {{ formatDate(trip.created_at) }}</p>
        </div>
        <div class="flex flex-wrap gap-2">
          <RouterLink :to="`/trips/${trip.id}`" class="rounded-md bg-[#0a1530] px-3 py-2 text-sm font-medium text-white hover:bg-[#1a2a52]">
            查看详情
          </RouterLink>
          <button type="button" class="rounded-md border border-[#c8c4be] px-3 py-2 text-sm font-medium hover:bg-[#f6f5f4]" @click="emit('delete', trip)">
            删除
          </button>
        </div>
      </article>
    </div>
  </div>
</template>
