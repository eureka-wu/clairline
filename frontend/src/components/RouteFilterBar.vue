<template>
  <div class="filter-card">
    <div class="filter-left">
      <!-- 出发城市 (Element Plus 现代可搜索组件) -->
      <span class="filter-label">出发地:</span>
      <el-select
        :model-value="origin"
        filterable
        :filter-method="filterOriginMethod"
        placeholder="搜索出发地 (支持拼音/城市)..."
        style="width: 205px;"
        class="custom-el-select"
        @change="onOriginChange"
      >
        <el-option label="全部出发地 (全国 71 城)" value="全部">
          <span style="font-weight:800; color:#0284c7;">全部出发地 (全国 71 城)</span>
        </el-option>
        <el-option-group v-for="g in displayGroupedOrigins" :key="g.name" :label="g.name">
          <el-option
            v-for="c in g.cities"
            :key="c"
            :label="`${c} (${CITY_METADATA[c]?.province || ''})`"
            :value="c"
          >
            <div style="display:flex; justify-content:space-between; align-items:center; width:100%;">
              <span style="font-weight:700;">{{ c }}</span>
              <span style="font-size:0.75rem; color:#64748b;">{{ CITY_METADATA[c]?.province }} · {{ CITY_METADATA[c]?.region }}</span>
            </div>
          </el-option>
        </el-option-group>
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

      <!-- 目的地城市 (严格级联 + Element Plus 可搜索组件) -->
      <span class="filter-label">目的地:</span>
      <el-select
        :model-value="destination"
        filterable
        :filter-method="filterDestMethod"
        :placeholder="`全部直飞 (${availableDests.length}城可飞)`"
        style="width: 205px;"
        class="custom-el-select"
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
            <span style="font-size:0.75rem; color:#64748b;">{{ CITY_METADATA[c]?.province }} · {{ CITY_METADATA[c]?.region }}</span>
          </div>
        </el-option>
      </el-select>

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

// 支持搜索拼音与中文过滤的出发城市
const displayGroupedOrigins = computed(() => {
  const q = originQuery.value.trim().toLowerCase();
  if (!q) return groupedOrigins.value;

  return groupedOrigins.value.map(g => {
    const matched = g.cities.filter(c => {
      const meta = CITY_METADATA[c] || {};
      const pinyin = meta.pinyin || '';
      const prov = meta.province || '';
      return c.includes(q) || pinyin.toLowerCase().includes(q) || prov.includes(q) || (meta.code || '').toLowerCase().includes(q);
    });
    return { name: g.name, cities: matched };
  }).filter(g => g.cities.length > 0);
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
