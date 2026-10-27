<template>
  <div class="filter-card">
    <!-- 主航线选择区 (桌面单行，移动端顶行平分) -->
    <div class="filter-main-row">
      <div class="filter-cities-pair">
        <span class="filter-label hide-on-mobile">出发地:</span>
        <el-select
          :model-value="origin"
          filterable
          :filter-method="filterOriginMethod"
          placeholder="搜索出发地..."
          class="custom-el-select city-select-el"
          @change="onOriginChange"
        >
          <el-option label="全部出发地 (全国 71 城)" value="全部">
            <span style="font-weight:800; color:#0284c7;">全部出发地 (全国 71 城)</span>
          </el-option>
          <el-option
            v-for="c in filteredOrigins"
            :key="c"
            :label="`${c} (${CITY_METADATA[c]?.province || ''})`"
            :value="c"
          >
            <div style="display:flex; justify-content:space-between; align-items:center; width:100%;">
              <span style="font-weight:700;">{{ c }}</span>
              <span style="font-size:0.75rem; color:#64748b;">{{ CITY_METADATA[c]?.province || '' }}</span>
            </div>
          </el-option>
        </el-select>

        <!-- 城市互换按钮 -->
        <button 
          type="button" 
          class="btn-swap" 
          title="点击互换出发地与目的地"
          @click="swapCity"
        >
          ⇄
        </button>

        <span class="filter-label hide-on-mobile">目的地:</span>
        <el-select
          :model-value="destination"
          filterable
          :filter-method="filterDestMethod"
          :placeholder="`全部直飞 (${availableDests.length}城可飞)`"
          class="custom-el-select city-select-el"
          @change="$emit('update:destination', $event)"
        >
          <el-option :label="`全部直飞 (${availableDests.length}城可飞)`" value="全部">
            <span style="font-weight:800; color:#0284c7;">全部直飞 ({{ availableDests.length }}城可飞)</span>
          </el-option>
          <el-option
            v-for="c in filteredDests"
            :key="c"
            :label="`${c} (${CITY_METADATA[c]?.province || ''})`"
            :value="c"
          >
            <div style="display:flex; justify-content:space-between; align-items:center; width:100%;">
              <span style="font-weight:700;">{{ c }}</span>
              <span style="font-size:0.75rem; color:#64748b;">{{ CITY_METADATA[c]?.province || '' }}</span>
            </div>
          </el-option>
        </el-select>
      </div>
    </div>

    <!-- 辅助控制区 (有票开关 + 排序药丸) -->
    <div class="filter-controls-row">
      <!-- 仅看有票航线开关 -->
      <label class="toggle-switch-wrap" title="点击切换查看有票航线或全部航线">
        <div class="switch-pill" :class="{ active: onlyAvailable }" @click="$emit('update:onlyAvailable', !onlyAvailable)">
          <div class="switch-dot"></div>
        </div>
        <span class="switch-text" @click="$emit('update:onlyAvailable', !onlyAvailable)">
          {{ onlyAvailable ? `有票 (${availableCount})` : `全部 (${totalCount})` }}
        </span>
      </label>

      <!-- 排序工具栏 -->
      <div class="sort-group">
        <span class="sort-label hide-on-mobile">排序:</span>
        <button 
          type="button" 
          class="sort-btn" 
          :class="{ active: sortBy === 'recent-first' }"
          @click="setSort('recent-first')"
        >
          最近可兑
        </button>
        <button 
          type="button" 
          class="sort-btn" 
          :class="{ active: sortBy === 'time-asc' }"
          @click="setSort('time-asc')"
        >
          起飞时间
        </button>
        <button 
          type="button" 
          class="sort-btn" 
          :class="{ active: sortBy === 'dist-desc' }"
          @click="setSort('dist-desc')"
        >
          航距最长
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import { CITY_METADATA } from '../data/city-meta.js';
import { DIRECT_MAP } from '../data/routes-network.js';

const props = defineProps({
  origin: {
    type: String,
    default: '杭州'
  },
  destination: {
    type: String,
    default: '全部'
  },
  onlyAvailable: {
    type: Boolean,
    default: true
  },
  sortBy: {
    type: String,
    default: 'time-asc'
  },
  availableCount: {
    type: Number,
    default: 0
  },
  totalCount: {
    type: Number,
    default: 0
  }
});

const emit = defineEmits([
  'update:origin', 
  'update:destination', 
  'update:onlyAvailable', 
  'update:sortBy',
  'update:sort-by',
  'swap-failed'
]);

function setSort(type) {
  emit('update:sortBy', type);
  emit('update:sort-by', type);
}

// 拼音/文字搜索状态
const originQuery = ref('');
const destQuery = ref('');

// 所有可出发城市列表 (按直达航线数量由多到少排序，常用城市居前)
const allOriginCities = computed(() => {
  return Object.keys(CITY_METADATA)
    .filter(c => (DIRECT_MAP[c] || []).length > 0)
    .sort((a, b) => (DIRECT_MAP[b] || []).length - (DIRECT_MAP[a] || []).length);
});

// 支持拼音/中文/省份搜索的出发城市
const filteredOrigins = computed(() => {
  const q = originQuery.value.trim().toLowerCase();
  if (!q) return allOriginCities.value;
  return allOriginCities.value.filter(c => {
    const meta = CITY_METADATA[c] || {};
    const pinyin = meta.pinyin || '';
    const prov = meta.province || '';
    return c.includes(q) || pinyin.toLowerCase().includes(q) || prov.includes(q) || (meta.code || '').toLowerCase().includes(q);
  });
});

// 当前出发地可直达的目的地列表 (严格级联)
const availableDests = computed(() => {
  if (props.origin === '全部') {
    return Object.keys(CITY_METADATA).filter(c => (DIRECT_MAP[c] || []).length > 0);
  }
  return DIRECT_MAP[props.origin] || [];
});

// 支持拼音搜索的目的地
const filteredDests = computed(() => {
  const q = destQuery.value.trim().toLowerCase();
  if (!q) return availableDests.value;
  return availableDests.value.filter(c => {
    const meta = CITY_METADATA[c] || {};
    const pinyin = meta.pinyin || '';
    const prov = meta.province || '';
    return c.includes(q) || pinyin.toLowerCase().includes(q) || prov.includes(q) || (meta.code || '').toLowerCase().includes(q);
  });
});

function filterOriginMethod(query) {
  originQuery.value = query;
}

function filterDestMethod(query) {
  destQuery.value = query;
}

function onOriginChange(newOrigin) {
  emit('update:origin', newOrigin);
  const nextDests = (newOrigin === '全部') ? Object.keys(CITY_METADATA) : (DIRECT_MAP[newOrigin] || []);
  if (!nextDests.includes(props.destination)) {
    emit('update:destination', '全部');
  }
}

function swapCity() {
  if (props.destination === '全部') {
    emit('swap-failed', '请先选择一个具体目的地再进行互换');
    return;
  }
  const oldOrigin = props.origin;
  const oldDest = props.destination;

  // 互换
  emit('update:origin', oldDest);
  const canFlyBack = (DIRECT_MAP[oldDest] || []).includes(oldOrigin);
  emit('update:destination', canFlyBack ? oldOrigin : '全部');
}
</script>

<style scoped>
:deep(.custom-el-select .el-select__wrapper) {
  border-radius: var(--radius-md) !important;
  font-weight: 700;
  box-shadow: 0 0 0 1px var(--border-subtle) inset !important;
}

:deep(.custom-el-select .el-select__wrapper.is-focused) {
  box-shadow: 0 0 0 1.5px var(--accent-cyan) inset !important;
}
</style>
