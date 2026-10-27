<template>
  <div class="map-explorer-wrapper" ref="wrapperEl">
    <!-- 悬浮在地图左上角的控制条 -->
    <div class="map-floating-bar">
      <el-select 
        :model-value="origin"
        filterable
        placeholder="搜索聚焦城市/枢纽..."
        style="width: 210px;"
        class="custom-map-el-select"
        @change="$emit('update:origin', $event)"
      >
        <el-option label="全部航网漫游" value="全部">
          <span style="font-weight:800; color:#0284c7;">全部航网漫游 ({{ totalRouteCount }}条)</span>
        </el-option>
        <el-option 
          v-for="c in hubCities" 
          :key="c" 
          :label="`${c} (${CITY_METADATA[c]?.province || '基地'})`"
          :value="c"
        >
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <span style="font-weight:700;">{{ c }}</span>
            <span style="font-size:0.75rem; color:#64748b;">{{ CITY_METADATA[c]?.province }}</span>
          </div>
        </el-option>
      </el-select>

      <button type="button" class="btn-map-reset" @click="resetMapZoom" title="重置地图镜头视野">
        恢复全貌
      </button>
    </div>

    <!-- 悬浮在地图右上角的全屏切换按钮 (仅图标切换，支持 Tooltip 提示) -->
    <button 
      type="button" 
      class="btn-map-fullscreen" 
      @click="toggleFullscreen" 
      :title="isFullscreen ? '退出全屏 (ESC)' : '进入全屏大屏沉浸模式'"
      :aria-label="isFullscreen ? '退出全屏' : '全屏展示'"
    >
      <svg v-if="!isFullscreen" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3" />
      </svg>
      <svg v-else viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M8 3v3a2 2 0 0 1-2 2H3m18 0h-3a2 2 0 0 1-2-2V3m0 18v-3a2 2 0 0 1 2-2h3M3 16h3a2 2 0 0 1 2 2v3" />
      </svg>
    </button>

    <!-- 图例 Legend (纯净两档，单一色彩绝不重叠) -->
    <div class="map-legend-card">
      <div class="legend-item">
        <span class="legend-color" style="background:#10b981; box-shadow:0 0 6px #10b981;"></span> 
        近7天有票 / 20+天 (充裕)
      </div>
      <div class="legend-item">
        <span class="legend-color" style="background:#64748b;"></span> 
        可兑 1~9 天 (散票)
      </div>
      <div class="legend-item legend-item-hint" style="font-size:0.7rem; color:#64748b;">
        🖱️ 滚轮缩放 · 拖拽漫游 · 点击航线查详情
      </div>
    </div>

    <!-- 悬浮微提示气泡 (Hover Tooltip) -->
    <div 
      v-if="hoverTooltip.visible" 
      class="map-hover-tooltip"
      :style="{ left: `${hoverTooltip.x}px`, top: `${hoverTooltip.y}px` }"
    >
      <div style="font-weight:800; font-size:0.82rem; color:#fff;">
        {{ hoverTooltip.title }}
      </div>
      <div style="font-size:0.72rem; color:#38bdf8; margin-top:2px;">
        {{ hoverTooltip.sub }}
      </div>
    </div>

    <!-- 原生响应式 SVG 航网矢量底图 (支持触摸手势拖动与双指缩放) -->
    <svg 
      ref="svgEl"
      class="china-flight-svg"
      :viewBox="`${vb.x} ${vb.y} ${vb.w} ${vb.h}`"
      preserveAspectRatio="xMidYMid meet"
      @wheel.prevent="handleWheel"
      @mousedown="handleMouseDown"
      @mousemove="handleMouseMove"
      @mouseup="handleMouseUp"
      @mouseleave="handleMouseUp"
      @touchstart="handleTouchStart"
      @touchmove.prevent="handleTouchMove"
      @touchend="handleTouchEnd"
    >


      <!-- 经纬度科技微网格底纹 -->
      <g class="map-bg-grid-group">
        <line v-for="gx in gridXList" :key="`gx-${gx}`" :x1="gx" y1="20" :x2="gx" y2="760" class="map-bg-grid" />
        <line v-for="gy in gridYList" :key="`gy-${gy}`" x1="30" :y1="gy" x2="970" :y2="gy" class="map-bg-grid" />
      </g>

      <!-- 中国各省份矢量地理轮廓 -->
      <g class="map-provinces-group">
        <path 
          v-for="prov in CHINA_PROVINCES" 
          :key="prov.name"
          :d="prov.path"
          class="province-contour"
        >
          <title>{{ prov.name }}</title>
        </path>
      </g>

      <!-- 航线飞线轨道 (贝塞尔曲线) -->
      <g class="map-flight-routes-group">
        <g 
          v-for="r in renderedRoutes" 
          :key="r.id"
          class="flight-route-item"
          @click="emit('open-drawer', r.raw)"
          @mouseenter="onRouteHover($event, r)"
          @mouseleave="onRouteLeave"
        >
          <!-- 底层透明点击与发光区域 -->
          <path :d="r.pathD" class="route-hit-area" />
          <!-- 航线彩色核心线条 (单一色彩，绝不重叠) -->
          <path 
            :d="r.pathD" 
            :stroke="r.color" 
            :stroke-width="r.width" 
            class="route-core-line" 
          />
        </g>
      </g>

      <!-- 通航城市节点与字形排版 -->
      <g class="map-cities-group">
        <g 
          v-for="c in renderedCities" 
          :key="c.name"
          class="city-node-item"
          @click="handleCityClick(c.name)"
        >
          <!-- 核心枢纽雷达波纹脉冲扩散光晕 -->
          <circle 
            v-if="c.isHub" 
            :cx="c.x" 
            :cy="c.y" 
            r="11" 
            class="hub-radar-pulse" 
          />
          <!-- 城市实心圆点 -->
          <circle 
            :cx="c.x" 
            :cy="c.y" 
            :r="c.isHub ? 4.2 : 3" 
            :class="['city-point', { 'is-hub': c.isHub, 'is-active': c.name === origin }]" 
          />
          <!-- 城市名称标签 -->
          <text 
            :x="c.x + c.dx" 
            :y="c.y + c.dy" 
            :text-anchor="c.anchor" 
            :class="['city-name-text', { 'is-hub': c.isHub, 'is-active': c.name === origin }]"
          >
            {{ c.name }}
          </text>
        </g>
      </g>
    </svg>
  </div>
</template>

<script setup>
import { ref, computed, reactive, onMounted, onUnmounted } from 'vue';
import { CITY_METADATA } from '../data/city-meta.js';
import { CHINA_PROVINCES } from '../data/china-geo.js';

const props = defineProps({
  origin: {
    type: String,
    default: '杭州'
  },
  availableRoutes: {
    type: Array,
    default: () => []
  }
});

const emit = defineEmits(['update:origin', 'open-drawer']);

const wrapperEl = ref(null);
const svgEl = ref(null);

const hubCities = ['杭州', '银川', '长春', '宁波', '温州', '广州', '成都', '武汉', '哈尔滨', '西安', '郑州', '深圳', '北京', '重庆', '阿勒泰', '喀什', '西双版纳', '三亚'];

// 视口 ViewBox 基准视口
const DEFAULT_VB_DESKTOP = { x: 25, y: 15, w: 950, h: 740 };
// 手机竖屏专用视角：聚焦核心通航区，左右与上下撑满竖屏视觉
const DEFAULT_VB_MOBILE = { x: 130, y: 30, w: 780, h: 720 };

function getInitialViewBox() {
  if (typeof window !== 'undefined' && window.innerWidth < 768) {
    return { ...DEFAULT_VB_MOBILE };
  }
  return { ...DEFAULT_VB_DESKTOP };
}

const vb = reactive(getInitialViewBox());

// 经纬度微网格坐标列表
const gridXList = [80, 170, 260, 350, 440, 530, 620, 710, 800, 890];
const gridYList = [60, 135, 210, 285, 360, 435, 510, 585, 660, 735];

// 地理坐标投影函数 (精确对齐 CHINA_PROVINCES 矢量画板)
function projectMapX(lng) {
  return 40 + ((lng - 73.0) / (135.0 - 73.0)) * 920.0;
}
function projectMapY(lat) {
  return 40 + ((53.5 - lat) / (53.5 - 18.0)) * 700.0;
}

// 密集区域字形防重叠偏移布局
const CITY_LABEL_LAYOUT = {
  // 长三角密集机场群
  '杭州': { dx: -10, dy: 5, anchor: 'end' },
  '宁波': { dx: 9, dy: 4, anchor: 'start' },
  '上海': { dx: 9, dy: -2, anchor: 'start' },
  '嘉兴': { dx: -8, dy: -3, anchor: 'end' },
  '温州': { dx: 9, dy: 4, anchor: 'start' },
  // 粤港澳大湾区
  '广州': { dx: -9, dy: -2, anchor: 'end' },
  '深圳': { dx: 9, dy: 4, anchor: 'start' },
  '珠海': { dx: -9, dy: 6, anchor: 'end' },
  // 成渝与西南
  '成都': { dx: -9, dy: 4, anchor: 'end' },
  '重庆': { dx: 9, dy: 4, anchor: 'start' },
  '遵义': { dx: 9, dy: 4, anchor: 'start' },
  // 京津冀
  '北京': { dx: -9, dy: -2, anchor: 'end' },
  // 山东群
  '青岛': { dx: 9, dy: 4, anchor: 'start' },
  '烟台': { dx: 9, dy: -2, anchor: 'start' },
  '威海': { dx: 9, dy: 4, anchor: 'start' },
  '济南': { dx: -9, dy: -3, anchor: 'end' },
  '潍坊': { dx: 0, dy: 12, anchor: 'middle' }
};

// 今天基准日期 (用于检测 7 天内近期放票流动光效)
const todayStr = new Date().toISOString().slice(0, 10);
const sevenDaysLater = new Date(Date.now() + 7 * 86400000).toISOString().slice(0, 10);

const totalRouteCount = computed(() => props.availableRoutes.length);

const filteredRoutes = computed(() => {
  if (props.origin === '全部') {
    return props.availableRoutes;
  }
  // 用户需求：双向全通——既显示从该城市出发的航线，也显示飞抵该城市的返程/到达航线
  return props.availableRoutes.filter(r => r.from === props.origin || r.to === props.origin);
});

// 计算渲染航线及贝塞尔曲线
const renderedRoutes = computed(() => {
  return filteredRoutes.value.map(r => {
    const metaFrom = CITY_METADATA[r.from];
    const metaTo = CITY_METADATA[r.to];
    if (!metaFrom?.coords || !metaTo?.coords) return null;

    const x1 = projectMapX(metaFrom.coords[0]);
    const y1 = projectMapY(metaFrom.coords[1]);
    const x2 = projectMapX(metaTo.coords[0]);
    const y2 = projectMapY(metaTo.coords[1]);

    const dx = x2 - x1;
    const dy = y2 - y1;
    const dist = Math.hypot(dx, dy);
    // 贝塞尔弧形曲线控制点 (去程与返程反向隆起，形成双向航路走廊)
    const cx = (x1 + x2) / 2 - (dy / dist) * Math.min(dist * 0.22, 60);
    const cy = (y1 + y2) / 2 + (dx / dist) * Math.min(dist * 0.22, 60) - 20;

    const count = r.availableDaysCount || (r.availableDates ? r.availableDates.length : 0);

    // 判断是否在未来 7 天内有票
    let isRecent = false;
    if (r.availableDates && r.availableDates.length > 0) {
      isRecent = r.availableDates.some(d => d >= todayStr && d <= sevenDaysLater);
    }

    // 纯粹两档互斥色彩：近7天有票 / 20+天充裕统一赋予极光翠绿；其余紧俏散票统一赋予冷灰
    let color = '#64748b'; // 紧俏 / 1~9天 (冷灰)
    let width = 1.1;

    if (isRecent || count >= 20) {
      color = '#10b981'; // 近7天有票 / 20+天 (极光翠绿)
      width = 2.0;
    } else if (count === 0) {
      color = '#334155'; // 暂无直飞机位
      width = 0.8;
    }

    return {
      id: `${r.from}-${r.to}`,
      from: r.from,
      to: r.to,
      count,
      color,
      width,
      isRecent,
      pathD: `M ${x1.toFixed(1)} ${y1.toFixed(1)} Q ${cx.toFixed(1)} ${cy.toFixed(1)} ${x2.toFixed(1)} ${y2.toFixed(1)}`,
      raw: r
    };
  }).filter(Boolean);
});

// 计算所有关联可见的城市列表 (双向全通)
const renderedCities = computed(() => {
  const visibleCityNames = new Set();

  if (props.origin === '全部') {
    hubCities.forEach(c => visibleCityNames.add(c));
    filteredRoutes.value.forEach(r => {
      visibleCityNames.add(r.from);
      visibleCityNames.add(r.to);
    });
  } else {
    visibleCityNames.add(props.origin);
    filteredRoutes.value.forEach(r => {
      visibleCityNames.add(r.from);
      visibleCityNames.add(r.to);
    });
  }

  const list = [];
  visibleCityNames.forEach(name => {
    const meta = CITY_METADATA[name];
    if (!meta?.coords) return;
    const x = projectMapX(meta.coords[0]);
    const y = projectMapY(meta.coords[1]);
    const isHub = hubCities.includes(name);
    const layout = CITY_LABEL_LAYOUT[name] || { dx: 0, dy: -7, anchor: 'middle' };

    list.push({
      name,
      x: Number(x.toFixed(1)),
      y: Number(y.toFixed(1)),
      isHub,
      dx: layout.dx,
      dy: layout.dy,
      anchor: layout.anchor
    });
  });

  return list;
});

// ----------------------------- 缩放与漫游交互
let isDragging = false;
let dragStartX = 0;
let dragStartY = 0;
let dragStartVb = { x: 0, y: 0, w: 1000, h: 780 };

function handleWheel(e) {
  if (!svgEl.value) return;
  const rect = svgEl.value.getBoundingClientRect();
  const mousePctX = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
  const mousePctY = Math.max(0, Math.min(1, (e.clientY - rect.top) / rect.height));

  const mouseSvgX = vb.x + mousePctX * vb.w;
  const mouseSvgY = vb.y + mousePctY * vb.h;

  const factor = e.deltaY < 0 ? 0.85 : 1.18;
  let newW = vb.w * factor;
  newW = Math.max(160, Math.min(1300, newW));
  let newH = newW * (780 / 1000);

  let newX = mouseSvgX - mousePctX * newW;
  let newY = mouseSvgY - mousePctY * newH;

  vb.x = Math.max(-200, Math.min(1200 - newW, newX));
  vb.y = Math.max(-150, Math.min(930 - newH, newY));
  vb.w = newW;
  vb.h = newH;
}

function handleMouseDown(e) {
  if (e.button !== 0) return;
  isDragging = true;
  dragStartX = e.clientX;
  dragStartY = e.clientY;
  dragStartVb = { ...vb };
}

function handleMouseMove(e) {
  if (!isDragging) return;
  const dx = e.clientX - dragStartX;
  const dy = e.clientY - dragStartY;

  // 比例换算
  const rect = svgEl.value.getBoundingClientRect();
  const scale = vb.w / rect.width;

  vb.x = dragStartVb.x - dx * scale;
  vb.y = dragStartVb.y - dy * scale;
}

function handleMouseUp() {
  isDragging = false;
}

// ----------------------------- 移动端 Touch 触摸手势 (单指平移拖拽 + 双指自然缩放)
let touchStartX = 0;
let touchStartY = 0;
let touchStartDistance = 0;
let touchStartVb = { ...vb };

function handleTouchStart(e) {
  if (e.touches.length === 1) {
    isDragging = true;
    touchStartX = e.touches[0].clientX;
    touchStartY = e.touches[0].clientY;
    touchStartVb = { ...vb };
  } else if (e.touches.length === 2) {
    isDragging = false;
    const dx = e.touches[0].clientX - e.touches[1].clientX;
    const dy = e.touches[0].clientY - e.touches[1].clientY;
    touchStartDistance = Math.hypot(dx, dy);
    touchStartVb = { ...vb };
  }
}

function handleTouchMove(e) {
  if (!svgEl.value) return;
  const rect = svgEl.value.getBoundingClientRect();
  const scale = vb.w / rect.width;

  if (e.touches.length === 1 && isDragging) {
    const dx = e.touches[0].clientX - touchStartX;
    const dy = e.touches[0].clientY - touchStartY;
    vb.x = touchStartVb.x - dx * scale;
    vb.y = touchStartVb.y - dy * scale;
  } else if (e.touches.length === 2 && touchStartDistance > 0) {
    const dx = e.touches[0].clientX - e.touches[1].clientX;
    const dy = e.touches[0].clientY - e.touches[1].clientY;
    const currentDist = Math.hypot(dx, dy);
    const pinchRatio = touchStartDistance / currentDist;

    const newW = touchStartVb.w * pinchRatio;
    const newH = touchStartVb.h * pinchRatio;
    if (newW > 180 && newW < 2400) {
      const midX = (e.touches[0].clientX + e.touches[1].clientX) / 2;
      const midY = (e.touches[0].clientY + e.touches[1].clientY) / 2;
      const relX = (midX - rect.left) / rect.width;
      const relY = (midY - rect.top) / rect.height;

      vb.x = touchStartVb.x + (touchStartVb.w - newW) * relX;
      vb.y = touchStartVb.y + (touchStartVb.h - newH) * relY;
      vb.w = newW;
      vb.h = newH;
    }
  }
}

function handleTouchEnd(e) {
  if (e.touches.length === 0) {
    isDragging = false;
    touchStartDistance = 0;
  } else if (e.touches.length === 1) {
    isDragging = true;
    touchStartX = e.touches[0].clientX;
    touchStartY = e.touches[0].clientY;
    touchStartVb = { ...vb };
  }
}

function resetMapZoom() {
  const target = getInitialViewBox();
  vb.x = target.x;
  vb.y = target.y;
  vb.w = target.w;
  vb.h = target.h;
}

function handleCityClick(cityName) {
  if (cityName === props.origin) return;
  // 优先匹配从当前城市出发的直飞，若无则匹配返回当前城市的直飞，均可直接打开抽屉
  const directRoute = props.availableRoutes.find(r => r.from === props.origin && r.to === cityName)
    || props.availableRoutes.find(r => r.from === cityName && r.to === props.origin);
  if (directRoute) {
    emit('open-drawer', directRoute);
  } else {
    emit('update:origin', cityName);
  }
}

// ----------------------------- Hover Tooltip
const hoverTooltip = reactive({
  visible: false,
  x: 0,
  y: 0,
  title: '',
  sub: ''
});

function onRouteHover(e, r) {
  if (!wrapperEl.value) return;
  const rect = wrapperEl.value.getBoundingClientRect();
  hoverTooltip.visible = true;
  hoverTooltip.x = e.clientX - rect.left + 12;
  hoverTooltip.y = e.clientY - rect.top - 36;
  const dirTag = r.from === props.origin ? '【出发直飞】' : (r.to === props.origin ? '【到达/返程】' : '');
  hoverTooltip.title = `${r.from} ➔ ${r.to} ${dirTag}`;
  hoverTooltip.sub = `可兑出行日: ${r.count} 天 ${r.isRecent ? '· 7天内近期有票' : ''}`;
}

function onRouteLeave() {
  hoverTooltip.visible = false;
}

// ----------------------------- 全屏大屏沉浸模式
const isFullscreen = ref(false);

async function toggleFullscreen() {
  if (!document.fullscreenElement) {
    try {
      const root = document.documentElement;
      if (root.requestFullscreen) {
        await root.requestFullscreen();
      } else if (root.webkitRequestFullscreen) {
        await root.webkitRequestFullscreen();
      }
    } catch (e) {
      console.warn('全屏请求失败:', e);
    }
  } else {
    try {
      if (document.exitFullscreen) {
        await document.exitFullscreen();
      } else if (document.webkitExitFullscreen) {
        await document.webkitExitFullscreen();
      }
    } catch (e) {
      console.warn('退出全屏失败:', e);
    }
  }
}

function onFullscreenChange() {
  isFullscreen.value = Boolean(document.fullscreenElement);
  if (isFullscreen.value) {
    document.body.classList.add('is-map-fullscreen');
  } else {
    document.body.classList.remove('is-map-fullscreen');
  }
}

onMounted(() => {
  document.addEventListener('fullscreenchange', onFullscreenChange);
  document.addEventListener('webkitfullscreenchange', onFullscreenChange);
});

onUnmounted(() => {
  document.removeEventListener('fullscreenchange', onFullscreenChange);
  document.removeEventListener('webkitfullscreenchange', onFullscreenChange);
  document.body.classList.remove('is-map-fullscreen');
});
</script>

<style scoped>
.map-explorer-wrapper {
  position: relative;
  width: 100%;
  height: calc(100vh - 82px);
  min-height: 560px;
  max-height: 100vh;
  background: radial-gradient(circle at 60% 40%, #0d1629 0%, #050811 100%);
  border-radius: var(--radius-lg);
  overflow: hidden;
  box-shadow: 0 16px 40px rgba(0, 0, 0, 0.5);
  user-select: none;
}

/* 全屏大屏沉浸模式 */
.map-explorer-wrapper:fullscreen {
  width: 100vw !important;
  height: 100vh !important;
  max-height: 100vh !important;
  border-radius: 0 !important;
}

.china-flight-svg {
  width: 100%;
  height: 100%;
  cursor: grab;
}

.china-flight-svg:active {
  cursor: grabbing;
}

/* 微网格线 */
.map-bg-grid {
  stroke: rgba(255, 255, 255, 0.035);
  stroke-width: 0.8;
  stroke-dasharray: 2 4;
}

/* 省份轮廓与地理边界 */
.province-contour {
  fill: #111c2e;
  stroke: rgba(56, 189, 248, 0.45);
  stroke-width: 0.95px;
  stroke-linejoin: round;
  stroke-linecap: round;
  transition: fill 0.25s ease, stroke 0.25s ease, stroke-width 0.25s ease;
}

.province-contour:hover {
  fill: #19273f;
  stroke: #38bdf8;
  stroke-width: 1.5px;
  filter: drop-shadow(0 0 6px rgba(56, 189, 248, 0.6));
}

/* 航线飞线 */
.flight-route-item {
  cursor: pointer;
}

.route-hit-area {
  fill: none;
  stroke: transparent;
  stroke-width: 12;
}

.route-core-line {
  fill: none;
  opacity: 0.82;
  transition: opacity 0.2s ease, stroke-width 0.2s ease;
}

.flight-route-item:hover .route-core-line {
  opacity: 1;
  stroke-width: 2.8;
  filter: drop-shadow(0 0 6px #38bdf8);
}



/* 城市节点 */
.city-node-item {
  cursor: pointer;
}

.city-point {
  fill: #94a3b8;
  stroke: #0f172a;
  stroke-width: 1;
  transition: r 0.2s ease, fill 0.2s ease;
}

.city-point.is-hub {
  fill: #38bdf8;
  filter: drop-shadow(0 0 4px #38bdf8);
}

.city-point.is-active {
  fill: #f59e0b;
  stroke: #ffffff;
  stroke-width: 1.5;
  r: 5.5;
  filter: drop-shadow(0 0 8px #f59e0b);
}

.city-name-text {
  font-size: 8.5px;
  font-family: inherit;
  font-weight: 500;
  fill: #cbd5e1;
  filter: drop-shadow(0 1px 2px rgba(0, 0, 0, 0.9));
  pointer-events: none;
}

.city-name-text.is-hub {
  font-weight: 700;
  fill: #f8fafc;
}

.city-name-text.is-active {
  font-weight: 800;
  fill: #fbbf24;
  font-size: 10px;
}

.city-node-item:hover .city-point {
  fill: #ffffff;
  r: 6;
}

/* 核心枢纽脉冲波纹 */
.hub-radar-pulse {
  fill: none;
  stroke: #38bdf8;
  stroke-width: 1;
  opacity: 0.7;
  animation: radarWave 2.4s ease-out infinite;
  pointer-events: none;
}

@keyframes radarWave {
  0% {
    r: 4;
    opacity: 0.9;
  }
  100% {
    r: 16;
    opacity: 0;
  }
}

/* 浮动控制栏与信息 */
.map-floating-bar {
  position: absolute;
  top: 16px;
  left: 20px;
  z-index: 10;
  display: flex;
  align-items: center;
  gap: 10px;
  background: rgba(15, 23, 42, 0.8);
  backdrop-filter: blur(10px);
  padding: 8px 12px;
  border-radius: var(--radius-md);
  border: 1px solid rgba(56, 189, 248, 0.3);
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.35);
}

:deep(.custom-map-el-select .el-select__wrapper) {
  height: 34px !important;
  min-height: 34px !important;
  font-size: 0.88rem !important;
  font-weight: 600;
  border-radius: 6px;
}

.btn-map-reset {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 34px;
  padding: 0 16px;
  font-size: 0.88rem;
  font-weight: 600;
  color: #38bdf8;
  background: rgba(14, 165, 233, 0.12);
  border: 1px solid rgba(56, 189, 248, 0.4);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
  white-space: nowrap;
}

.btn-map-reset:hover {
  background: rgba(14, 165, 233, 0.28);
  border-color: #38bdf8;
  color: #ffffff;
  box-shadow: 0 0 10px rgba(56, 189, 248, 0.35);
}

.btn-map-reset:active {
  transform: scale(0.97);
}

/* 悬浮在地图右上角的全屏切换按钮 (右侧、仅图标、高质感半透明毛玻璃) */
.btn-map-fullscreen {
  position: absolute;
  top: 16px;
  right: 20px;
  z-index: 10;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  background: rgba(15, 23, 42, 0.82);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(56, 189, 248, 0.35);
  border-radius: var(--radius-md);
  color: #38bdf8;
  cursor: pointer;
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.35);
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.btn-map-fullscreen:hover {
  background: rgba(14, 165, 233, 0.28);
  border-color: #38bdf8;
  color: #ffffff;
  box-shadow: 0 0 12px rgba(56, 189, 248, 0.45);
  transform: translateY(-1px);
}

.btn-map-fullscreen:active {
  transform: scale(0.94);
}

.map-legend-card {
  position: absolute;
  bottom: 20px;
  right: 20px;
  z-index: 10;
  background: rgba(15, 23, 42, 0.88);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(56, 189, 248, 0.25);
  border-radius: var(--radius-md);
  padding: 10px 14px;
  font-size: 0.74rem;
  color: #cbd5e1;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.legend-color {
  width: 14px;
  height: 3px;
  border-radius: 2px;
}



.map-hover-tooltip {
  position: absolute;
  z-index: 20;
  pointer-events: none;
  background: rgba(15, 23, 42, 0.95);
  border: 1px solid #38bdf8;
  border-radius: 6px;
  padding: 6px 10px;
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.5);
  white-space: nowrap;
  backdrop-filter: blur(6px);
}

@media (max-width: 768px) {
  .map-explorer-wrapper {
    height: calc(100vh - 60px) !important;
    min-height: calc(100vh - 60px) !important;
    border-radius: 0 !important;
    margin: -10px -12px;
  }

  .map-floating-bar {
    top: 10px;
    left: 10px;
    right: 56px;
    padding: 4px 6px;
    gap: 6px;
  }

  .custom-map-el-select {
    width: auto !important;
    flex: 1;
    min-width: 0;
  }

  :deep(.custom-map-el-select .el-select__wrapper) {
    height: 32px !important;
    min-height: 32px !important;
    font-size: 0.8rem !important;
    padding: 2px 6px !important;
  }

  .btn-map-reset {
    height: 32px;
    padding: 0 8px;
    font-size: 0.76rem;
    white-space: nowrap;
  }

  .btn-map-fullscreen {
    top: 10px;
    right: 10px;
    width: 36px;
    height: 36px;
  }

  .map-legend-card {
    bottom: calc(12px + env(safe-area-inset-bottom));
    left: 12px;
    right: 12px;
    padding: 6px 10px;
    font-size: 0.68rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 4px;
    background: rgba(15, 23, 42, 0.92);
  }

  .legend-item {
    margin-bottom: 0;
  }

  .legend-item-hint {
    display: none !important;
  }
}
</style>
