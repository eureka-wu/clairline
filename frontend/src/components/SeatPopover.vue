<template>
  <Teleport to="body">
    <div 
      v-if="visible" 
      ref="popoverRef"
      class="seat-popover"
      :style="popoverStyle"
      @mouseenter="$emit('popover-enter')"
      @mouseleave="$emit('popover-leave')"
    >
      <!-- 箭头 -->
      <div 
        class="popover-arrow" 
        :class="arrowPosition === 'down' ? 'arrow-down' : 'arrow-up'"
        :style="{ left: `${arrowLeft}px` }"
      ></div>

      <!-- 气泡头部 -->
      <div class="popover-header">
        <div class="popover-title">
          <strong>{{ fromCity }} ➔ {{ toCity }}</strong>
          <span style="font-size:0.75rem; color:var(--accent-cyan); margin-left:6px; font-weight:700;">
            {{ dateLabel }}
          </span>
        </div>
        <div class="popover-actions">
          <button 
            type="button" 
            class="btn-popover-refresh" 
            :disabled="loading"
            @click="$emit('refresh', { fromCity, toCity, flightDate, targetEl })"
            title="重新联网查验长龙官方最新票况"
          >
            {{ loading ? '查票中...' : '刷新' }}
          </button>
          <button 
            type="button" 
            class="btn-popover-close" 
            @click="$emit('close')"
          >
            &times;
          </button>
        </div>
      </div>

      <!-- 气泡主体内容 -->
      <div class="popover-body">
        <!-- 加载中 -->
        <div v-if="loading" style="padding:16px 10px; text-align:center;">
          <div style="font-weight:700; font-size:0.86rem; color:var(--text-primary);">正在连接长龙官方系统...</div>
          <div style="font-size:0.74rem; color:var(--text-muted); margin-top:2px;">实时探测当日各航班畅飞卡剩余机位</div>
        </div>

        <!-- 航班列表 -->
        <template v-else-if="flights && flights.length > 0">
          <div 
            v-for="(f, idx) in flights" 
            :key="idx" 
            class="popover-flight-item"
          >
            <div>
              <div class="flight-no-row">
                <span class="flight-no">{{ f.flightNo }}</span>
                <span class="flight-aircraft">{{ f.aircraft || 'A320' }}</span>
                <span class="flight-stopover" :class="{ direct: f.stopover === '直飞' }">
                  {{ f.stopover || '直飞' }}
                </span>
              </div>
              <div class="flight-time-row">
                <span>{{ f.depTime }} ➔ {{ f.arrTime }}</span>
              </div>
            </div>
            <div class="flight-price-col">
              <span 
                class="left-badge" 
                :class="f.secCardLeft > 0 ? 'avail' : 'empty'"
              >
                {{ f.secCardLeft > 0 ? `余 ${f.secCardLeft} 张` : '已兑完' }}
              </span>
              <div class="flight-price">¥{{ f.redeemPrice }}</div>
            </div>
          </div>
        </template>

        <!-- 暂无可兑机位 -->
        <div v-else style="padding:14px 10px; text-align:center;">
          <div style="font-weight:700; font-size:0.85rem; color:var(--text-primary);">官方大盘显示有票 · 暂无可兑机位</div>
          <div style="font-size:0.74rem; color:var(--text-muted); margin-top:3px; line-height:1.4;">
            该日免费机位可能已被抢兑完，建议关注临近日期！
          </div>
        </div>
      </div>

      <!-- 气泡底部：纯净时间戳，无任何冗余文字与 emoji -->
      <div v-if="timeFormatted" class="popover-footer">
        <span>{{ timeFormatted.replace('2026-', '') }}</span>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue';

const props = defineProps({
  visible: Boolean,
  fromCity: String,
  toCity: String,
  flightDate: String,
  targetEl: Object,
  flights: Array,
  loading: Boolean,
  timeFormatted: String
});

const emit = defineEmits(['close', 'refresh', 'popover-enter', 'popover-leave']);

const popoverRef = ref(null);
const top = ref(0);
const left = ref(0);
const arrowLeft = ref(20);
const arrowPosition = ref('down');

const dateLabel = computed(() => {
  if (!props.flightDate) return '';
  const dt = new Date(props.flightDate);
  const m = dt.getMonth() + 1;
  const d = dt.getDate();
  const week = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'][dt.getDay()];
  return `${m}月${d}日 ${week}`;
});

const popoverStyle = computed(() => ({
  top: `${top.value}px`,
  left: `${left.value}px`
}));

// 计算定位坐标 (采用纯 Viewport 视口坐标，搭配 position: fixed + Teleport 完美杜绝漂移)
function updatePosition() {
  if (!props.visible || !props.targetEl) return;
  nextTick(() => {
    const el = props.targetEl;
    const pop = popoverRef.value;
    if (!el || !pop) return;

    const rect = el.getBoundingClientRect();
    const popoverWidth = pop.offsetWidth || 320;
    const popoverHeight = pop.offsetHeight || 220;

    // 水平居中对齐胶囊
    let calcLeft = rect.left + (rect.width / 2) - (popoverWidth / 2);
    calcLeft = Math.max(10, Math.min(calcLeft, window.innerWidth - popoverWidth - 10));

    // 计算箭头偏移
    const targetCenterX = rect.left + (rect.width / 2);
    arrowLeft.value = Math.max(16, Math.min(targetCenterX - calcLeft, popoverWidth - 24));

    // 垂直方向：优先放在胶囊正上方
    const spaceAbove = rect.top;
    if (spaceAbove >= popoverHeight + 14) {
      top.value = rect.top - popoverHeight - 9;
      arrowPosition.value = 'down';
    } else {
      top.value = rect.bottom + 9;
      arrowPosition.value = 'up';
    }
    left.value = calcLeft;
  });
}

watch(() => [props.visible, props.targetEl, props.flights, props.loading], () => {
  updatePosition();
});

// 点击外部自动关闭气泡
function onGlobalClick(e) {
  if (!props.visible) return;
  const pop = popoverRef.value;
  if (pop && !pop.contains(e.target) && (!props.targetEl || !props.targetEl.contains(e.target))) {
    emit('close');
  }
}

onMounted(() => {
  window.addEventListener('resize', updatePosition);
  window.addEventListener('scroll', updatePosition, true);
  document.addEventListener('mousedown', onGlobalClick);
});

onUnmounted(() => {
  window.removeEventListener('resize', updatePosition);
  window.removeEventListener('scroll', updatePosition, true);
  document.removeEventListener('mousedown', onGlobalClick);
});
</script>
