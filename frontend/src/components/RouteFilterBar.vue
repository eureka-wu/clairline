<template>
  <div class="filter-card">
    <div class="filter-left">
      <!-- 出发城市 -->
      <span class="filter-label">出发地:</span>
      <select 
        class="custom-select-native" 
        :value="origin" 
        @change="onOriginChange($event.target.value)"
      >
        <option value="全部">全部出发地 (全国 71 城)</option>
        <optgroup v-for="(group, gIdx) in groupedOrigins" :key="gIdx" :label="group.name">
          <option v-for="c in group.cities" :key="c" :value="c">
            {{ c }} ({{ CITY_METADATA[c]?.province || '' }})
          </option>
        </optgroup>
      </select>

      <!-- 城市互换按钮 -->
      <button 
        type="button" 
        class="btn-swap" 
        title="点击互换出发地与目的地"
        @click="swapCity"
      >
        ⇄
      </button>

      <!-- 目的地城市 (严格级联) -->
      <span class="filter-label">目的地:</span>
      <select 
        class="custom-select-native" 
        :value="destination" 
        @change="$emit('update:destination', $event.target.value)"
      >
        <option value="全部">全部直飞 ({{ availableDests.length }}城可飞)</option>
        <option v-for="c in availableDests" :key="c" :value="c">
          {{ c }} ({{ CITY_METADATA[c]?.province || '' }})
        </option>
      </select>

      <!-- 仅看有票航线开关 -->
      <label class="toggle-switch-wrap" title="点击切换查看有票航线或全部航线">
        <div class="switch-pill" :class="{ active: onlyAvailable }" @click="$emit('update:onlyAvailable', !onlyAvailable)">
          <div class="switch-dot"></div>
        </div>
        <span class="switch-text" @click="$emit('update:onlyAvailable', !onlyAvailable)">
          {{ onlyAvailable ? `查看有票航线 (${availableCount}条)` : `查看全部航线 (${totalCount}条)` }}
        </span>
      </label>
    </div>

    <!-- 排序工具栏 -->
    <div class="sort-group">
      <span class="sort-label">排序:</span>
      <button 
        type="button" 
        class="sort-btn" 
        :class="{ active: sortBy === 'recent-first' }"
        @click="$emit('update:sortBy', 'recent-first')"
      >
        最近可兑
      </button>
      <button 
        type="button" 
        class="sort-btn" 
        :class="{ active: sortBy === 'tickets-desc' }"
        @click="$emit('update:sortBy', 'tickets-desc')"
      >
        最多可兑
      </button>
      <button 
        type="button" 
        class="sort-btn" 
        :class="{ active: sortBy === 'time-asc' }"
        @click="$emit('update:sortBy', 'time-asc')"
      >
        起飞时间
      </button>
      <button 
        type="button" 
        class="sort-btn" 
        :class="{ active: sortBy === 'dist-desc' }"
        @click="$emit('update:sortBy', 'dist-desc')"
      >
        航距最长
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';
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
  'swap-failed'
]);

// 按枢纽层级分组的出发城市
const groupedOrigins = computed(() => {
  const hubs = {
    '核心超级大本营': ['杭州', '银川', '长春'],
    '重点基地与区域枢纽': ['宁波', '温州', '广州', '成都', '武汉', '哈尔滨', '西安', '郑州', '深圳', '北京', '重庆', '嘉兴'],
    '新疆与文旅航线': ['阿勒泰', '喀什', '西双版纳', '丽江', '三亚', '海口', '乌鲁木齐', '阿克苏', '海拉尔'],
    '其他通航城市': []
  };

  const used = new Set([...hubs['核心超级大本营'], ...hubs['重点基地与区域枢纽'], ...hubs['新疆与文旅航线']]);
  Object.keys(CITY_METADATA).forEach(city => {
    if (!used.has(city) && (DIRECT_MAP[city] || []).length > 0) {
      hubs['其他通航城市'].push(city);
    }
  });

  return Object.keys(hubs).map(name => ({
    name,
    cities: hubs[name]
  }));
});

// 当前出发地可直达的目的地列表 (严格级联)
const availableDests = computed(() => {
  if (props.origin === '全部') {
    return Object.keys(CITY_METADATA).filter(c => (DIRECT_MAP[c] || []).length > 0);
  }
  return DIRECT_MAP[props.origin] || [];
});

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
.custom-select-native {
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: 6px 12px;
  font-size: 0.84rem;
  font-weight: 700;
  color: var(--text-primary);
  background: #ffffff;
  outline: none;
  cursor: pointer;
  transition: border-color 0.2s ease;
}

.custom-select-native:focus {
  border-color: var(--accent-cyan);
}
</style>
