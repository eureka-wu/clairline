<template>
  <div class="map-explorer-wrapper">
    <!-- 悬浮在地图左上角的控制条 -->
    <div class="map-floating-bar">
      <select 
        class="custom-select-native"
        :value="origin"
        @change="$emit('update:origin', $event.target.value)"
      >
        <option value="全部">全部航网漫游</option>
        <option v-for="c in hubCities" :key="c" :value="c">
          {{ c }} ({{ CITY_METADATA[c]?.province }})
        </option>
      </select>
      <button type="button" class="btn-glass" @click="resetMapZoom">
        恢复全貌
      </button>
    </div>

    <!-- 图例 Legend -->
    <div class="map-legend-card">
      <div style="font-weight:700; font-size:0.75rem; color:#94a3b8; margin-bottom:6px;">航网放票热度图例</div>
      <div class="legend-item"><span class="legend-color" style="background:#38bdf8; box-shadow:0 0 6px #38bdf8;"></span> 可兑 20+ 天 (充裕)</div>
      <div class="legend-item"><span class="legend-color" style="background:#0284c7;"></span> 可兑 10~19 天 (常态)</div>
      <div class="legend-item"><span class="legend-color" style="background:#475569;"></span> 可兑 1~9 天 (紧俏)</div>
      <div class="legend-item"><span class="legend-color" style="background:#334155;"></span> 暂无直飞机位</div>
      <div class="legend-item" style="margin-top:4px;"><span class="legend-flow"></span> 7天内近期有票 (流动光效)</div>
    </div>

    <!-- ECharts 画布容器 -->
    <div ref="chartEl" class="map-canvas"></div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue';
import * as echarts from 'echarts';
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

const chartEl = ref(null);
let myChart = null;

const hubCities = ['杭州', '银川', '长春', '宁波', '温州', '广州', '成都', '武汉', '哈尔滨', '西安', '郑州', '深圳', '北京', '重庆', '阿勒泰', '喀什', '西双版纳', '三亚'];

// 组装 SVG 底图注册给 ECharts
function registerChinaMap() {
  const pathD = CHINA_PROVINCES.map(p => `<path id="${p.name}" d="${p.path}" fill="#0f172a" stroke="#1e293b" stroke-width="0.8" />`).join('\n');
  const svgStr = `
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 780" width="1000" height="780">
      ${pathD}
    </svg>
  `;
  echarts.registerMap('china_airlines', { svg: svgStr });
}

// 投影坐标转换函数
function projectCoords(lon, lat) {
  const minLon = 73.5, maxLon = 135.0;
  const minLat = 18.0, maxLat = 53.5;
  const mapWidth = 1000, mapHeight = 780;
  const x = ((lon - minLon) / (maxLon - minLon)) * (mapWidth - 140) + 70;
  const y = (1 - (lat - minLat) / (maxLat - minLat)) * (mapHeight - 140) + 70;
  return [x, y];
}

function initChart() {
  if (!chartEl.value) return;
  registerChinaMap();
  myChart = echarts.init(chartEl.value);

  myChart.on('click', (params) => {
    if (params.seriesType === 'scatter' || params.seriesType === 'effectScatter') {
      const cityName = params.name;
      if (cityName && cityName !== props.origin) {
        // 查找是否属于当前出发地的航线
        const matched = props.availableRoutes.find(r => r.from === props.origin && r.to === cityName);
        if (matched) {
          emit('open-drawer', matched);
        } else {
          // 切换为出发城市
          emit('update:origin', cityName);
        }
      }
    } else if (params.seriesType === 'lines') {
      const r = params.data.rawRoute;
      if (r) emit('open-drawer', r);
    }
  });

  renderChart();
}

function renderChart() {
  if (!myChart) return;

  const currentOrigin = props.origin;
  const routes = (currentOrigin === '全部') 
    ? props.availableRoutes 
    : props.availableRoutes.filter(r => r.from === currentOrigin);

  // 1. 散点数据 (城市节点)
  const scatterData = [];
  const effectScatterData = [];

  Object.keys(CITY_METADATA).forEach(name => {
    const meta = CITY_METADATA[name];
    if (!meta.coords) return;
    const pt = projectCoords(meta.coords[0], meta.coords[1]);
    const isOrigin = name === currentOrigin;
    const isSuperHub = meta.hub === 'tier1';

    const item = {
      name,
      value: pt,
      meta,
      itemStyle: {
        color: isOrigin ? '#38bdf8' : (isSuperHub ? '#34d399' : '#94a3b8')
      }
    };

    if (isOrigin || isSuperHub) {
      effectScatterData.push(item);
    } else {
      scatterData.push(item);
    }
  });

  // 2. 航线飞线数据 (普通线与流动发光特效线)
  const normalLines = [];
  const flowLines = [];

  routes.forEach(r => {
    const fromMeta = CITY_METADATA[r.from];
    const toMeta = CITY_METADATA[r.to];
    if (!fromMeta?.coords || !toMeta?.coords) return;

    const pFrom = projectCoords(fromMeta.coords[0], fromMeta.coords[1]);
    const pTo = projectCoords(toMeta.coords[0], toMeta.coords[1]);

    const daysCount = r.availableDaysCount || (r.availableDates || []).length;
    let lineColor = '#475569';
    let lineWidth = 1;

    if (daysCount >= 20) {
      lineColor = '#38bdf8';
      lineWidth = 2.2;
    } else if (daysCount >= 10) {
      lineColor = '#0284c7';
      lineWidth = 1.6;
    } else if (daysCount > 0) {
      lineColor = '#64748b';
      lineWidth = 1.2;
    }

    const lineItem = {
      coords: [pFrom, pTo],
      rawRoute: r,
      lineStyle: {
        color: lineColor,
        width: lineWidth,
        opacity: 0.75,
        curveness: 0.25
      }
    };
    normalLines.push(lineItem);

    // 判断是否在近 7 天内有票 -> 挂载流动光粒子特效
    const now = new Date();
    const hasNext7Days = (r.availableDates || []).some(d => {
      const dt = new Date(d);
      const diff = (dt - now) / (1000 * 3600 * 24);
      return diff >= 0 && diff <= 7;
    });

    if (hasNext7Days) {
      flowLines.push({
        coords: [pFrom, pTo],
        rawRoute: r,
        lineStyle: {
          color: '#38bdf8',
          width: 2,
          opacity: 0.9,
          curveness: 0.25
        }
      });
    }
  });

  const option = {
    backgroundColor: '#090d16',
    tooltip: {
      trigger: 'item',
      backgroundColor: 'rgba(15, 23, 42, 0.92)',
      borderColor: '#38bdf8',
      textStyle: { color: '#f8fafc', fontSize: 12 },
      formatter: (params) => {
        if (params.seriesType === 'lines') {
          const r = params.data.rawRoute;
          if (!r) return '';
          return `
            <div style="font-weight:800; font-size:14px; margin-bottom:4px; color:#38bdf8;">
              ${r.from} ➔ ${r.to}
            </div>
            <div>可兑换出行日: <strong>${r.availableDaysCount || 0} 天</strong></div>
            <div style="color:#94a3b8; font-size:11px; margin-top:2px;">点击即可查看详细排班与各日余票</div>
          `;
        }
        if (params.seriesType === 'scatter' || params.seriesType === 'effectScatter') {
          const meta = params.data.meta || {};
          return `
            <div style="font-weight:800; color:#38bdf8; font-size:14px;">${params.name}</div>
            <div style="color:#94a3b8; font-size:12px;">${meta.airport || ''} (${meta.province || ''})</div>
            <div style="color:#64748b; font-size:11px; margin-top:2px;">点击设为出发城市</div>
          `;
        }
        return '';
      }
    },
    geo: {
      map: 'china_airlines',
      roam: true,
      zoom: 1.1,
      aspectScale: 1,
      itemStyle: {
        areaColor: '#0b1329',
        borderColor: '#1e293b',
        borderWidth: 0.8
      },
      emphasis: {
        itemStyle: {
          areaColor: '#1e293b'
        }
      }
    },
    series: [
      // 基础全量飞线
      {
        type: 'lines',
        coordinateSystem: 'geo',
        zlevel: 1,
        data: normalLines
      },
      // 7天内近期票流动光斑特效
      {
        type: 'lines',
        coordinateSystem: 'geo',
        zlevel: 2,
        effect: {
          show: true,
          period: 4,
          trailLength: 0.25,
          symbol: 'arrow',
          symbolSize: 6,
          color: '#38bdf8'
        },
        data: flowLines
      },
      // 普通城市节点
      {
        type: 'scatter',
        coordinateSystem: 'geo',
        zlevel: 3,
        symbolSize: 6,
        label: {
          show: true,
          position: 'right',
          formatter: '{b}',
          fontSize: 10,
          color: '#94a3b8'
        },
        data: scatterData
      },
      // 大本营与当前出发地动态涟漪光晕
      {
        type: 'effectScatter',
        coordinateSystem: 'geo',
        zlevel: 4,
        rippleEffect: {
          brushType: 'stroke',
          scale: 4
        },
        symbolSize: 10,
        label: {
          show: true,
          position: 'top',
          formatter: '{b}',
          fontWeight: 'bold',
          fontSize: 12,
          color: '#ffffff'
        },
        data: effectScatterData
      }
    ]
  };

  myChart.setOption(option, true);
}

function resetMapZoom() {
  if (myChart) {
    myChart.dispatchAction({
      type: 'geoRoam',
      zoom: 1,
      originX: 500,
      originY: 390
    });
    renderChart();
  }
}

watch(() => [props.origin, props.availableRoutes], () => {
  renderChart();
});

onMounted(() => {
  nextTick(() => {
    initChart();
    window.addEventListener('resize', () => myChart?.resize());
  });
});

onUnmounted(() => {
  myChart?.dispose();
  myChart = null;
});
</script>

<style scoped>
.map-explorer-wrapper {
  position: relative;
  width: 100%;
  height: 720px;
  background: #090d16;
  border-radius: var(--radius-lg);
  overflow: hidden;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.4);
}

.map-canvas {
  width: 100%;
  height: 100%;
}

.map-floating-bar {
  position: absolute;
  top: 16px;
  left: 20px;
  z-index: 10;
  display: flex;
  align-items: center;
  gap: 10px;
  background: rgba(15, 23, 42, 0.75);
  backdrop-filter: blur(8px);
  padding: 6px 10px;
  border-radius: var(--radius-md);
  border: 1px solid rgba(56, 189, 248, 0.25);
}

.map-legend-card {
  position: absolute;
  bottom: 20px;
  right: 20px;
  z-index: 10;
  background: rgba(15, 23, 42, 0.85);
  backdrop-filter: blur(8px);
  border: 1px solid rgba(56, 189, 248, 0.2);
  border-radius: var(--radius-md);
  padding: 10px 14px;
  font-size: 0.74rem;
  color: #cbd5e1;
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

.legend-flow {
  width: 14px;
  height: 3px;
  background: linear-gradient(90deg, transparent, #38bdf8, #fff);
  border-radius: 2px;
  animation: pulse 1.5s infinite;
}

@keyframes pulse {
  0% { opacity: 0.4; }
  50% { opacity: 1; }
  100% { opacity: 0.4; }
}
</style>
