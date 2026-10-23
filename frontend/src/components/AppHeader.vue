<template>
  <header class="app-header">
    <div class="header-inner">
      <div class="brand-area">
        <div class="brand-icon" v-html="ICONS.plane"></div>
        <div class="brand-title">长龙航线</div>

        <!-- Tab Segmented 切换 -->
        <nav class="tab-segmented">
          <button 
            type="button"
            class="tab-btn" 
            :class="{ active: currentTab === 'routes' }"
            @click="$emit('update:currentTab', 'routes')"
          >
            <span v-html="ICONS.plane"></span>
            <span>航线探索</span>
          </button>
          <button 
            type="button"
            class="tab-btn" 
            :class="{ active: currentTab === 'map' }"
            @click="$emit('update:currentTab', 'map')"
          >
            <span v-html="ICONS.compass"></span>
            <span>地图探索</span>
          </button>
        </nav>
      </div>

      <div class="header-actions">
        <button 
          type="button" 
          class="btn-glass" 
          @click="$emit('open-patrol')"
          title="管理 30 条后台自动与定时巡检航线"
        >
          <span v-html="ICONS.radar"></span>
          <span>巡检航线: {{ patrolCount }}/30</span>
        </button>
      </div>
    </div>
  </header>
</template>

<script setup>
import { ICONS } from '../data/icons.js';

defineProps({
  currentTab: {
    type: String,
    default: 'routes'
  },
  patrolCount: {
    type: Number,
    default: 30
  }
});

defineEmits(['update:currentTab', 'open-patrol']);
</script>
