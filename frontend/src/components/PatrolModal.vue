<template>
  <div v-if="visible" class="modal-overlay" @click.self="$emit('close')">
    <div class="modal-card">
      <!-- 模态框头部 -->
      <div class="modal-header">
        <div style="font-weight:800; font-size:1.05rem; display:flex; align-items:center; gap:8px;">
          <span v-html="ICONS.radar" style="color:var(--accent-cyan);"></span>
          <span>核心巡检航线配置 (最多 30 条)</span>
        </div>
        <button type="button" class="btn-popover-close" style="font-size:1.3rem;" @click="$emit('close')">&times;</button>
      </div>

      <!-- 状态条与开关 -->
      <div style="padding:10px 20px; background:#f0fdf4; border-bottom:1px solid #dcfce7; display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:8px;">
        <div style="display:flex; align-items:center; gap:8px;">
          <span style="font-size:0.78rem; font-weight:800; padding:2px 8px; border-radius:4px; background:#059669; color:#fff;">
            席位: {{ routes.length }} / 30 {{ routes.length >= 30 ? '满载' : '空闲' }}
          </span>
          <span style="font-size:0.75rem; color:#15803d;">
            {{ routes.length >= 30 ? '(已达上限，删一个方可添加一个)' : `(还可以添加 ${30 - routes.length} 条)` }}
          </span>
        </div>
        <!-- 自动轮巡总开关 -->
        <label style="display:inline-flex; align-items:center; gap:6px; cursor:pointer; font-size:0.75rem; font-weight:700; color:#334155;">
          <input 
            type="checkbox" 
            :checked="switches.hot_enabled" 
            @change="onSwitchChange('hot_enabled', $event.target.checked)"
            style="accent-color:#0284c7;"
          >
          <span>30条后台轮巡: {{ switches.hot_enabled ? '已启用 (每25分钟)' : '已停用' }}</span>
        </label>
      </div>

      <!-- 模态框主体 -->
      <div class="modal-body">
        <!-- 已选航线 Tag 网格 -->
        <div style="margin-bottom:14px;">
          <div style="font-size:0.82rem; font-weight:700; color:var(--text-primary); margin-bottom:6px;">
            已选巡检航线 (点击右侧 × 可移除释放槽位):
          </div>
          <div style="display:flex; flex-wrap:wrap; gap:6px; max-height:160px; overflow-y:auto; padding:4px 0;">
            <span 
              v-for="(r, idx) in routes" 
              :key="idx"
              style="display:inline-flex; align-items:center; gap:6px; background:#f1f5f9; border:1px solid #cbd5e1; padding:3px 8px; border-radius:4px; font-size:0.75rem; font-weight:700; color:#334155;"
            >
              <span>{{ r[0] }} ➔ {{ r[1] }}</span>
              <button 
                type="button" 
                @click="removeRoute(idx)"
                style="border:none; background:transparent; color:#94a3b8; font-weight:bold; cursor:pointer; font-size:0.85rem;"
                title="移除"
              >&times;</button>
            </span>
          </div>
        </div>

        <!-- 添加新航线 -->
        <div style="background:#f8fafc; border:1px solid var(--border-subtle); border-radius:var(--radius-md); padding:10px 14px; margin-bottom:14px;">
          <div style="font-size:0.82rem; font-weight:700; color:var(--text-primary); margin-bottom:8px; display:flex; align-items:center; justify-content:space-between;">
            <span>添加新巡检航线</span>
            <span v-if="routes.length >= 30" style="font-size:0.72rem; color:#ef4444; font-weight:normal;">
              席位已满，请先点击上方已有航线的 × 移除一条
            </span>
          </div>
          <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
            <select v-model="newFrom" :disabled="routes.length >= 30" class="custom-select-native" style="padding:4px 8px; font-size:0.8rem;">
              <option v-for="c in availableOrigins" :key="c" :value="c">{{ c }}</option>
            </select>
            <span style="color:#94a3b8;">➔</span>
            <select v-model="newTo" :disabled="routes.length >= 30" class="custom-select-native" style="padding:4px 8px; font-size:0.8rem;">
              <option v-for="c in availableDestsForNew" :key="c" :value="c">{{ c }}</option>
            </select>
            <button 
              type="button" 
              class="btn-primary" 
              style="padding:5px 12px; font-size:0.78rem;" 
              :disabled="routes.length >= 30 || !newFrom || !newTo"
              @click="addRoute"
            >
              加入巡检
            </button>
          </div>
        </div>

        <!-- 全量定时点配置 -->
        <div style="background:#ffffff; border:1px solid var(--border-subtle); border-radius:var(--radius-md); padding:10px 14px; margin-bottom:14px;">
          <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:8px;">
            <div style="font-size:0.82rem; font-weight:700; display:flex; align-items:center; gap:6px;">
              <span v-html="ICONS.clock" style="color:var(--accent-cyan);"></span>
              <span>全量普查定时 (至多 3 个时间点):</span>
              <span style="font-size:0.72rem; color:var(--accent-cyan);">已设 {{ patrolTimes.length }}/3 个</span>
            </div>
            <label style="display:inline-flex; align-items:center; gap:6px; cursor:pointer; font-size:0.75rem; font-weight:700; color:#334155;">
              <input 
                type="checkbox" 
                :checked="switches.all_enabled" 
                @change="onSwitchChange('all_enabled', $event.target.checked)"
                style="accent-color:#059669;"
              >
              <span>定时普查: {{ switches.all_enabled ? '已启用' : '已停用' }}</span>
            </label>
          </div>

          <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
            <span 
              v-for="(t, idx) in patrolTimes" 
              :key="idx"
              style="display:inline-flex; align-items:center; gap:4px; background:#ecfdf5; border:1px solid #a7f3d0; color:#047857; font-weight:800; font-size:0.78rem; padding:2px 6px; border-radius:4px;"
            >
              <span>{{ t }}</span>
              <button 
                type="button" 
                @click="removeTime(idx)"
                style="border:none; background:transparent; color:#059669; cursor:pointer;"
              >&times;</button>
            </span>

            <div v-if="patrolTimes.length < 3" style="display:inline-flex; align-items:center; gap:6px;">
              <input type="time" v-model="newTime" style="padding:2px 6px; font-size:0.78rem; border:1px solid #cbd5e1; border-radius:4px;">
              <button type="button" class="btn-glass" style="padding:3px 8px; font-size:0.75rem;" @click="addTime">+ 添加</button>
            </div>
          </div>
        </div>

        <!-- 手动触发与实时进度监控条 -->
        <div style="background:#f8fafc; border:1px solid var(--border-subtle); border-radius:var(--radius-md); padding:10px 14px;">
          <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:8px; flex-wrap:wrap; gap:8px;">
            <div style="font-size:0.82rem; font-weight:700;">
              <span>手动执行巡检</span>
              <span style="font-size:0.72rem; margin-left:6px; color:var(--text-muted);">
                {{ patrolState.running ? '正在巡检中...' : '待命状态' }}
              </span>
            </div>
            <div style="display:flex; gap:8px;">
              <button 
                type="button" 
                class="btn-primary" 
                style="padding:5px 12px; font-size:0.78rem;" 
                :disabled="patrolState.running"
                @click="triggerManual('hot')"
              >
                热门巡检 (30条)
              </button>
              <button 
                type="button" 
                class="btn-primary" 
                style="padding:5px 12px; font-size:0.78rem; background:linear-gradient(135deg, #059669, #047857);"
                :disabled="patrolState.running"
                @click="triggerManual('all')"
              >
                全量普查 (397条)
              </button>
            </div>
          </div>

          <!-- 进度条 -->
          <div v-if="patrolState.running || patrolState.percent > 0" style="background:#ffffff; border:1px solid #bbf7d0; border-radius:6px; padding:8px 10px; margin-top:8px;">
            <div style="display:flex; justify-content:space-between; font-size:0.75rem; margin-bottom:4px; font-weight:700; color:#047857;">
              <span>{{ patrolState.current_route || '正在巡检...' }}</span>
              <span>{{ patrolState.percent }}%</span>
            </div>
            <div style="width:100%; height:6px; background:#e2e8f0; border-radius:3px; overflow:hidden;">
              <div 
                style="height:100%; background:linear-gradient(90deg, #10b981, #059669); transition:width 0.3s ease;"
                :style="{ width: `${patrolState.percent}%` }"
              ></div>
            </div>
          </div>
        </div>
      </div>

      <!-- 模态框底部 -->
      <div class="modal-footer">
        <button type="button" class="btn-glass" style="font-size:0.78rem;" @click="resetDefault">恢复默认 30 条</button>
        <div style="display:flex; gap:8px;">
          <button type="button" class="btn-glass" style="font-size:0.78rem;" @click="$emit('close')">取消</button>
          <button type="button" class="btn-primary" style="font-size:0.78rem;" @click="saveAll">保存配置</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue';
import { ICONS } from '../data/icons.js';
import { DIRECT_MAP } from '../data/routes-network.js';
import { 
  fetchPatrolConfig, 
  savePatrolConfig, 
  fetchPatrolTimes, 
  savePatrolTimes, 
  fetchPatrolSwitches, 
  savePatrolSwitches, 
  triggerPatrol, 
  fetchPatrolStatus 
} from '../api/patrol.js';

const props = defineProps({
  visible: Boolean
});

const emit = defineEmits(['close', 'saved']);

const routes = ref([]);
const patrolTimes = ref(['08:30', '20:00']);
const switches = ref({ hot_enabled: false, all_enabled: false });
const patrolState = ref({ running: false, percent: 0, current_route: '' });

const newFrom = ref('杭州');
const newTo = ref('阿勒泰');
const newTime = ref('12:00');
let pollTimer = null;

const availableOrigins = computed(() => Object.keys(DIRECT_MAP).filter(c => (DIRECT_MAP[c] || []).length > 0));
const availableDestsForNew = computed(() => DIRECT_MAP[newFrom.value] || []);

watch(newFrom, (val) => {
  const dests = DIRECT_MAP[val] || [];
  if (!dests.includes(newTo.value)) {
    newTo.value = dests[0] || '';
  }
});

async function loadData() {
  try {
    const [cfgRes, timesRes, swRes] = await Promise.all([
      fetchPatrolConfig(),
      fetchPatrolTimes(),
      fetchPatrolSwitches()
    ]);
    if (cfgRes?.config) routes.value = cfgRes.config;
    if (timesRes?.times) patrolTimes.value = timesRes.times;
    if (swRes?.switches) switches.value = swRes.switches;
  } catch (e) {
    console.warn('加载巡检配置失败:', e);
  }
}

watch(() => props.visible, (val) => {
  if (val) {
    loadData();
    startPolling();
  } else {
    stopPolling();
  }
});

function removeRoute(idx) {
  routes.value.splice(idx, 1);
}

function addRoute() {
  if (routes.value.length >= 30) return;
  if (!newFrom.value || !newTo.value) return;
  const exists = routes.value.some(r => r[0] === newFrom.value && r[1] === newTo.value);
  if (exists) return;
  routes.value.push([newFrom.value, newTo.value]);
}

function removeTime(idx) {
  patrolTimes.value.splice(idx, 1);
}

function addTime() {
  if (patrolTimes.value.length >= 3) return;
  if (!newTime.value || patrolTimes.value.includes(newTime.value)) return;
  patrolTimes.value.push(newTime.value);
  patrolTimes.value.sort();
}

async function onSwitchChange(key, checked) {
  switches.value[key] = checked;
  try {
    await savePatrolSwitches(switches.value.hot_enabled, switches.value.all_enabled);
  } catch (e) {
    console.warn('更新开关失败:', e);
  }
}

async function triggerManual(mode) {
  try {
    await triggerPatrol(mode);
    patrolState.value.running = true;
    startPolling();
  } catch (e) {
    console.warn('触发巡检失败:', e);
  }
}

function startPolling() {
  if (pollTimer) return;
  pollTimer = setInterval(async () => {
    try {
      const res = await fetchPatrolStatus();
      if (res && res.state) {
        patrolState.value = res.state;
      }
    } catch (e) {}
  }, 1000);
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
}

function resetDefault() {
  routes.value = [
    ["杭州", "阿勒泰"], ["杭州", "喀什"], ["杭州", "克拉玛依"], ["杭州", "西双版纳"],
    ["杭州", "丽江"], ["杭州", "三亚"], ["杭州", "海口"], ["杭州", "哈尔滨"],
    ["杭州", "长春"], ["杭州", "成都"], ["杭州", "重庆"], ["杭州", "广州"],
    ["杭州", "深圳"], ["杭州", "珠海"], ["杭州", "贵阳"], ["杭州", "昆明"],
    ["杭州", "乌鲁木齐"], ["杭州", "西宁"], ["杭州", "银川"], ["杭州", "大连"],
    ["杭州", "沈阳"], ["杭州", "海拉尔"], ["银川", "杭州"], ["银川", "乌鲁木齐"],
    ["银川", "喀什"], ["银川", "三亚"], ["银川", "广州"], ["长春", "杭州"],
    ["长春", "三亚"], ["长春", "成都"]
  ];
}

async function saveAll() {
  try {
    await Promise.all([
      savePatrolConfig(routes.value),
      savePatrolTimes(patrolTimes.value)
    ]);
    emit('saved', routes.value.length);
    emit('close');
  } catch (e) {
    alert('保存失败，请检查服务状态');
  }
}

onMounted(() => {
  if (props.visible) loadData();
});

onUnmounted(() => {
  stopPolling();
});
</script>
