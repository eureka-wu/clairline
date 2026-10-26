<template>
  <Teleport to="body">
    <transition name="dialog-fade">
      <div v-if="visible" class="dialog-overlay" @click.self="handleOverlayClick">
        <div class="dialog-card" :class="`type-${type}`">
          <!-- 图标徽章 -->
          <div class="dialog-icon-wrap" :class="`icon-bg-${type}`">
            <span v-if="type === 'error'" v-html="ICONS.alertTriangle" class="dialog-icon icon-error"></span>
            <span v-else-if="type === 'warning'" v-html="ICONS.alertCircle" class="dialog-icon icon-warning"></span>
            <span v-else-if="type === 'success'" v-html="ICONS.checkCircle" class="dialog-icon icon-success"></span>
            <span v-else v-html="ICONS.radar" class="dialog-icon icon-info"></span>
          </div>

          <!-- 标题与内容 -->
          <div class="dialog-content">
            <h3 class="dialog-title">{{ title || defaultTitle }}</h3>
            <div class="dialog-message">{{ message }}</div>
          </div>

          <!-- 底部动作按钮 -->
          <div class="dialog-actions">
            <button 
              v-if="showCancel" 
              type="button" 
              class="dialog-btn btn-secondary" 
              @click="$emit('cancel'); $emit('close')"
            >
              {{ cancelText || '取消' }}
            </button>
            <button 
              type="button" 
              class="dialog-btn btn-primary-accent" 
              :class="`btn-${type}`"
              @click="$emit('confirm'); $emit('close')"
            >
              {{ confirmText || '我知道了' }}
            </button>
          </div>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<script setup>
import { computed } from 'vue';
import { ICONS } from '../data/icons.js';

const props = defineProps({
  visible: { type: Boolean, default: false },
  title: { type: String, default: '' },
  message: { type: String, default: '' },
  type: { type: String, default: 'error' }, // 'error' | 'warning' | 'success' | 'info'
  confirmText: { type: String, default: '我知道了' },
  cancelText: { type: String, default: '' },
  showCancel: { type: Boolean, default: false },
  closeOnOverlay: { type: Boolean, default: true }
});

const emit = defineEmits(['close', 'confirm', 'cancel']);

const defaultTitle = computed(() => {
  if (props.type === 'error') return '操作提示与异常诊断';
  if (props.type === 'warning') return '系统提醒';
  if (props.type === 'success') return '操作成功';
  return '系统通知';
});

function handleOverlayClick() {
  if (props.closeOnOverlay) {
    emit('close');
  }
}
</script>

<style scoped>
.dialog-overlay {
  position: fixed;
  inset: 0;
  z-index: 99999;
  background: rgba(15, 23, 42, 0.65);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.dialog-card {
  width: 100%;
  max-width: 440px;
  background: #ffffff;
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25), 0 0 0 1px rgba(226, 232, 240, 0.8);
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  animation: dialog-pop 0.22s cubic-bezier(0.16, 1, 0.3, 1);
}

.dialog-icon-wrap {
  width: 54px;
  height: 54px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 16px;
}

.icon-bg-error { background: #fee2e2; }
.icon-bg-warning { background: #fef3c7; }
.icon-bg-success { background: #dcfce7; }
.icon-bg-info { background: #e0f2fe; }

.dialog-icon {
  display: flex;
}
.icon-error { color: #dc2626; }
.icon-warning { color: #d97706; }
.icon-success { color: #16a34a; }
.icon-info { color: #0284c7; }

.dialog-title {
  margin: 0 0 8px;
  font-size: 1.1rem;
  font-weight: 800;
  color: #0f172a;
}

.dialog-message {
  font-size: 0.85rem;
  color: #475569;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
  margin-bottom: 24px;
  max-height: 240px;
  overflow-y: auto;
  padding: 0 4px;
}

.dialog-actions {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  width: 100%;
}

.dialog-btn {
  flex: 1;
  padding: 10px 18px;
  border-radius: 10px;
  font-size: 0.85rem;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.15s ease;
  border: none;
}

.btn-secondary {
  background: #f1f5f9;
  color: #475569;
}
.btn-secondary:hover {
  background: #e2e8f0;
}

.btn-primary-accent {
  background: #0284c7;
  color: #ffffff;
  box-shadow: 0 4px 12px rgba(2, 132, 199, 0.25);
}
.btn-primary-accent:hover {
  background: #0369a1;
  transform: translateY(-1px);
}

.btn-error {
  background: #dc2626;
  box-shadow: 0 4px 12px rgba(220, 38, 38, 0.25);
}
.btn-error:hover {
  background: #b91c1c;
}

.btn-warning {
  background: #d97706;
  box-shadow: 0 4px 12px rgba(217, 119, 6, 0.25);
}
.btn-warning:hover {
  background: #b45309;
}

.btn-success {
  background: #16a34a;
  box-shadow: 0 4px 12px rgba(22, 163, 74, 0.25);
}
.btn-success:hover {
  background: #15803d;
}

/* 动效 */
.dialog-fade-enter-active,
.dialog-fade-leave-active {
  transition: opacity 0.2s ease;
}

.dialog-fade-enter-from,
.dialog-fade-leave-to {
  opacity: 0;
}

@keyframes dialog-pop {
  0% { transform: scale(0.92); opacity: 0; }
  100% { transform: scale(1); opacity: 1; }
}
</style>
