<template>
  <div v-if="visible" class="modal-overlay" @click.self="closeModal">
    <div class="modal-card" style="max-width: 480px;">
      <!-- 模态框头部 -->
      <div class="modal-header">
        <div style="font-weight:800; font-size:1.05rem; display:flex; align-items:center; gap:8px;">
          <span v-html="ICONS.phone" style="color:var(--accent-cyan);"></span>
          <span>长龙航空 · 手机验证码登录</span>
        </div>
        <button type="button" class="btn-popover-close" style="font-size:1.3rem;" @click="closeModal">&times;</button>
      </div>

      <!-- 模态框主体 -->
      <div class="modal-body" style="padding:16px 20px;">
        
        <!-- 会员身份简要信息卡片 (有历史记录时始终展示) -->
        <div 
          v-if="effectiveAuth?.user_name && effectiveAuth?.user_name !== '长龙会员' && effectiveAuth?.mobile"
          style="padding:12px 14px; border-radius:8px; margin-bottom:14px;"
          :style="effectiveAuth?.is_expired 
            ? 'background:#fffbeb; border:1px solid #fde68a;' 
            : 'background:#f0fdf4; border:1px solid #bbf7d0;'"
        >
          <div style="display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:8px;">
            <div style="display:flex; align-items:center; gap:10px;">
              <span 
                style="width:10px; height:10px; border-radius:50%; display:inline-block;"
                :style="effectiveAuth?.is_expired ? 'background:#f59e0b;' : 'background:#10b981;'"
              ></span>
              <div>
                <div style="font-size:0.85rem; font-weight:800; color:var(--text-primary); display:flex; align-items:center; gap:6px;">
                  <span>{{ effectiveAuth.user_name }}</span>
                  <span 
                    v-if="effectiveAuth.is_expired"
                    style="font-size:0.65rem; padding:1px 5px; border-radius:3px; background:#fef3c7; color:#b45309; font-weight:700;"
                  >
                    凭据已到期
                  </span>
                  <span 
                    v-else-if="effectiveAuth.is_verified"
                    style="font-size:0.65rem; padding:1px 5px; border-radius:3px; background:#dcfce7; color:#15803d; font-weight:700;"
                  >
                    已实名
                  </span>
                </div>
                <div style="font-size:0.72rem; color:var(--text-muted); margin-top:2px;">
                  手机: {{ effectiveAuth.mobile || '已同步' }} · 上次更新: {{ effectiveAuth.update_time || '刚刚' }}
                </div>
              </div>
            </div>
            <span 
              style="font-size:0.72rem; padding:3px 9px; border-radius:4px; font-weight:800; display:inline-flex; align-items:center; gap:4px;"
              :style="effectiveAuth?.is_expired 
                ? 'background:#fef3c7; color:#b45309;' 
                : 'background:#e0f2fe; color:#0284c7;'"
            >
              <span v-html="ICONS.crown" style="display:inline-flex;"></span>
              <span>{{ effectiveAuth.member_level || '乘云会员' }}</span>
            </span>
          </div>
        </div>

        <!-- 场景 1：凭据有效在线且未过期 -->
        <div 
          v-if="effectiveAuth?.is_logged_in && !effectiveAuth?.is_expired && !showResyncFlow"
          style="background:#f0fdf4; border:1px solid #bbf7d0; border-radius:8px; padding:18px 14px; text-align:center;"
        >
          <div style="display:inline-flex; margin-bottom:6px; color:#10b981;" v-html="ICONS.checkCircle"></div>
          <div style="font-size:0.92rem; font-weight:800; color:#047857; margin-bottom:4px;">
            长龙会员凭证已生效
          </div>
          <div style="font-size:0.75rem; color:#065f46; line-height:1.5; margin-bottom:14px;">
            已绑定会员「{{ effectiveAuth.user_name }}」，畅飞卡（{{ effectiveAuth.card_name || '长龙畅飞卡' }}）剩余机位与普查功能处于就绪状态。
          </div>
          <div style="display:flex; justify-content:center; gap:8px;">
            <button 
              type="button" 
              class="btn-glass" 
              style="font-size:0.75rem; color:#0284c7; border-color:#bae6fd; padding:5px 14px; background:#ffffff; display:inline-flex; align-items:center; gap:5px;"
              @click="handleRenewClick"
            >
              <span v-html="ICONS.refresh" style="display:inline-flex;"></span>
              <span>重新验证续期</span>
            </button>
            <button 
              type="button" 
              class="btn-glass" 
              style="font-size:0.75rem; color:var(--text-muted); border-color:#e2e8f0; padding:5px 12px; background:#ffffff; display:inline-flex; align-items:center; gap:5px;"
              @click="handleSwitchAccountClick"
            >
              <span>换其他手机号</span>
            </button>
          </div>
        </div>

        <!-- 场景 2：输入手机号与验证码 (过期一键续期或首次登录) -->
        <div v-else style="padding: 4px 0 2px;">
          <!-- 若处于过期续期状态，给出清晰提示条 -->
          <div 
            v-if="effectiveAuth?.is_expired || props.autoStart" 
            style="background:#fffbeb; border:1px solid #fde68a; border-radius:6px; padding:9px 12px; margin-bottom:12px; display:flex; align-items:flex-start; gap:8px; font-size:0.75rem; color:#b45309; line-height:1.4;"
          >
            <span style="font-size:1rem; line-height:1;">⚠️</span>
            <div>
              <div style="font-weight:700;">会员凭据已到期 (长龙短效凭据单次有效约24h)</div>
              <div style="color:#92400e; margin-top:2px;">已自动预填您的绑定手机号，获取验证码后即可一键快速续期！</div>
            </div>
          </div>

          <!-- 手机号输入 -->
          <div style="margin-bottom:14px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
              <label style="font-size:0.75rem; color:var(--text-muted); font-weight:600;">会员手机号</label>
              <span v-if="isPreFilledMobile" style="font-size:0.7rem; color:#0284c7; font-weight:600;">已自动填入当前账号</span>
            </div>
            <input 
              type="tel" 
              v-model="mobile" 
              maxlength="11" 
              placeholder="请输入长龙会员绑定的11位手机号" 
              class="sms-input"
              @keyup.enter="handleTriggerCaptcha"
            />
          </div>

          <!-- 短信验证码与获取按钮 -->
          <div style="margin-bottom:14px;">
            <label style="display:block; font-size:0.72rem; color:var(--text-muted); margin-bottom:5px; font-weight:600;">短信验证码</label>
            <div style="display:flex; gap:8px;">
              <input 
                type="text" 
                v-model="smsCode" 
                maxlength="6" 
                placeholder="6位短信验证码" 
                class="sms-input sms-code-input"
                style="flex:1;"
                @keyup.enter="handleSmsLogin"
              />
              <button 
                type="button" 
                class="btn-sms-code"
                :disabled="countdown > 0 || isVerifyingCaptcha"
                @click="handleTriggerCaptcha"
              >
                <span v-if="isVerifyingCaptcha">安全验证中...</span>
                <span v-else-if="countdown > 0">{{ countdown }}s 后重试</span>
                <span v-else>获取验证码</span>
              </button>
            </div>
          </div>

          <!-- 登录/续期按钮 -->
          <button 
            type="button" 
            class="btn-primary" 
            style="width:100%; padding:9px 0; font-size:0.85rem; justify-content:center; display:inline-flex; align-items:center; gap:6px; font-weight:700; border-radius:6px;"
            :disabled="!mobile || !smsCode || isSubmittingLogin"
            @click="handleSmsLogin"
          >
            <span v-html="ICONS.check" style="display:inline-flex;"></span>
            <span>
              {{ isSubmittingLogin 
                ? '正在验证并同步会员...' 
                : (effectiveAuth?.is_expired ? '立即验证并完成续期' : '立即登录并同步会员') 
              }}
            </span>
          </button>

          <!-- 挂载易盾组件的隐藏节点 -->
          <div id="yidun-captcha-box" style="display:none;"></div>
        </div>

      </div>

      <!-- 模态框底部 -->
      <div class="modal-footer" style="justify-content: space-between; align-items:center;">
        <button 
          v-if="effectiveAuth?.mobile || effectiveAuth?.is_logged_in"
          type="button" 
          class="btn-reset-auth" 
          :disabled="isResettingAuth"
          title="清空本地会员凭证与卡包缓存，还原为初始状态"
          @click="handleResetAuth"
        >
          <span v-if="!isResettingAuth" v-html="ICONS.trash" class="reset-icon"></span>
          <span v-else class="reset-spinner"></span>
          <span>{{ isResettingAuth ? '正在清空...' : '清空登录凭据' }}</span>
        </button>
        <span v-else style="font-size:0.72rem; color:var(--text-muted); display:inline-flex; align-items:center; gap:4px;">
          <span style="width:6px; height:6px; border-radius:50%; background:#94a3b8;"></span>
          <span>未登录</span>
        </span>
        <button type="button" class="btn-glass" style="font-size:0.78rem;" @click="closeModal">关闭</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onUnmounted } from 'vue';
import { ICONS } from '../data/icons.js';
import { sendSmsCode, loginWithSmsCode, resetAuth } from '../api/auth.js';

const props = defineProps({
  visible: Boolean,
  authStatus: Object,
  autoStart: Boolean
});

const emit = defineEmits(['close', 'synced', 'refresh-auth']);

const showResyncFlow = ref(false);
const mobile = ref('');
const smsCode = ref('');
const verifyId = ref('');
const countdown = ref(0);
let countdownTimer = null;
const isVerifyingCaptcha = ref(false);
const isSubmittingLogin = ref(false);
const isResettingAuth = ref(false);
let captchaInstance = null;
const localAuth = ref(null);

const effectiveAuth = computed(() => {
  return localAuth.value || props.authStatus || {};
});

const isPreFilledMobile = computed(() => {
  const target = props.authStatus?.raw_mobile || localStorage.getItem('clairline_last_mobile') || '';
  return target && mobile.value === target;
});

function handleRenewClick() {
  showResyncFlow.value = true;
  const target = props.authStatus?.raw_mobile || localStorage.getItem('clairline_last_mobile') || '';
  if (target) {
    mobile.value = target;
  }
}

function handleSwitchAccountClick() {
  showResyncFlow.value = true;
  mobile.value = '';
  smsCode.value = '';
}

watch(() => props.visible, (val) => {
  if (val) {
    localAuth.value = null;
    emit('refresh-auth');

    const isExpired = Boolean(props.authStatus?.is_expired || props.autoStart);
    const isLoggedIn = Boolean(props.authStatus?.is_logged_in);

    // 如果过期或未登录，直接显示手机号验证码输入表单
    if (isExpired || !isLoggedIn) {
      showResyncFlow.value = true;
    } else {
      showResyncFlow.value = false;
    }

    // 自动预填手机号
    const targetMobile = props.authStatus?.raw_mobile || localStorage.getItem('clairline_last_mobile') || '';
    if (targetMobile && (!mobile.value || mobile.value.length !== 11)) {
      mobile.value = targetMobile;
    }
  }
});

function notify(title, message, type = 'info') {
  if (typeof window !== 'undefined' && window.$dialog) {
    window.$dialog(title, message, type);
  } else {
    alert(`${title}: ${message}`);
  }
}

function startCountdown() {
  countdown.value = 60;
  if (countdownTimer) clearInterval(countdownTimer);
  countdownTimer = setInterval(() => {
    countdown.value--;
    if (countdown.value <= 0) {
      clearInterval(countdownTimer);
      countdownTimer = null;
    }
  }, 1000);
}

function handleTriggerCaptcha() {
  const m = mobile.value.trim();
  if (!m || !/^1[3-9]\d{9}$/.test(m)) {
    notify('手机号格式错误', '请输入正确的11位中国大陆手机号', 'warning');
    return;
  }

  if (typeof initNECaptcha === 'undefined') {
    notify('安全验证组件加载中', '网易易盾 SDK 正在加载，请检查网络或稍等 2 秒后重试', 'warning');
    return;
  }

  isVerifyingCaptcha.value = true;
  try {
    initNECaptcha({
      captchaId: 'd574bdc4ef2f474f9d21fe3c59291491',
      element: '#yidun-captcha-box',
      mode: 'popup',
      width: 320,
      onVerify: async function (err, data) {
        if (err) {
          return;
        }
        const validate = data?.validate || '';
        if (!validate) {
          return;
        }
        try {
          const res = await sendSmsCode(m, validate);
          if (res.ok) {
            verifyId.value = res.verifyId || '';
            startCountdown();
            if (typeof window !== 'undefined' && window.$toast) {
              window.$toast('短信验证码已下发，请查收');
            }
            setTimeout(() => {
              const codeInput = document.querySelector('.sms-code-input');
              if (codeInput) codeInput.focus();
            }, 60);
          } else {
            notify('发送失败', res.error || '验证码下发异常', 'error');
          }
        } catch (e) {
          notify('发送验证码失败', e.message || '长龙官方接口下发失败', 'error');
        } finally {
          isVerifyingCaptcha.value = false;
        }
      },
      onClose: function () {
        isVerifyingCaptcha.value = false;
      }
    }, function (instance) {
      captchaInstance = instance;
      captchaInstance.popUp();
    }, function (err) {
      isVerifyingCaptcha.value = false;
      notify('安全组件初始化失败', err?.message || '请检查网络连接', 'error');
    });
  } catch (err) {
    isVerifyingCaptcha.value = false;
    notify('初始化异常', err.message || '安全组件异常', 'error');
  }
}

async function handleSmsLogin() {
  const m = mobile.value.trim();
  const c = smsCode.value.trim();
  if (!m || !c) {
    notify('输入提示', '请完整输入手机号与6位短信验证码', 'warning');
    return;
  }
  isSubmittingLogin.value = true;
  try {
    const res = await loginWithSmsCode(m, c, verifyId.value);
    if (res.ok) {
      if (typeof window !== 'undefined' && window.$toast) {
        window.$toast(res.message || '长龙会员凭证续期成功！');
      }
      showResyncFlow.value = false;
      smsCode.value = '';
      if (typeof localStorage !== 'undefined') {
        localStorage.setItem('clairline_last_mobile', m);
      }
      if (res.user) {
        localAuth.value = {
          is_logged_in: true,
          is_expired: false,
          ...res.user
        };
      }
      emit('refresh-auth', localAuth.value);
      emit('synced');
      closeModal();
    } else {
      notify('验证失败', res.error || '验证码错误或已过期', 'error');
    }
  } catch (e) {
    notify('验证异常', e.message || '网络连接超时', 'error');
  } finally {
    isSubmittingLogin.value = false;
  }
}

async function handleResetAuth() {
  let confirmed = false;
  if (typeof window !== 'undefined' && window.$confirm) {
    confirmed = await window.$confirm({
      title: '确定清空会员登录凭据？',
      message: '此操作将彻底清除本地保存的会员身份、畅飞卡授权与登录 Token。\n\n清空后应用将还原为初始未登录状态，需要重新输入手机号登录。',
      type: 'error',
      confirmText: '确定清空',
      cancelText: '取消'
    });
  } else {
    confirmed = confirm('确定清空本地登录凭据与会员信息？将还原为未登录状态。');
  }

  if (!confirmed) return;

  isResettingAuth.value = true;
  try {
    const res = await resetAuth();
    if (res.ok) {
      if (typeof window !== 'undefined' && window.$toast) {
        window.$toast('已清空本地登录凭据，已恢复未登录状态');
      }
      showResyncFlow.value = false;
      mobile.value = '';
      smsCode.value = '';
      localAuth.value = { is_logged_in: false, is_expired: false, user_name: '尚未登录长龙会员' };
      emit('refresh-auth', localAuth.value);
    } else {
      notify('重置提示', res.error || '清空失败', 'error');
    }
  } catch (e) {
    notify('重置失败', e.message || '重置异常', 'error');
  } finally {
    isResettingAuth.value = false;
  }
}

function closeModal() {
  emit('close');
}

onUnmounted(() => {
  if (countdownTimer) {
    clearInterval(countdownTimer);
    countdownTimer = null;
  }
});
</script>

<style scoped>
.sms-input {
  width: 100%;
  padding: 8px 12px;
  font-size: 0.82rem;
  border: 1px solid var(--border-subtle, #cbd5e1);
  border-radius: 6px;
  background: #ffffff;
  color: #1e293b;
  box-sizing: border-box;
  outline: none;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.sms-input:focus {
  border-color: var(--accent-cyan, #0ea5e9);
  box-shadow: 0 0 0 2px rgba(14, 165, 233, 0.15);
}

.btn-sms-code {
  font-size: 0.75rem;
  padding: 0 14px;
  white-space: nowrap;
  background: #f0f9ff;
  border: 1px solid #bae6fd;
  color: #0284c7;
  border-radius: 6px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-sms-code:hover:not(:disabled) {
  background: #e0f2fe;
}

.btn-sms-code:disabled {
  background: #f1f5f9;
  border-color: #e2e8f0;
  color: #94a3b8;
  cursor: not-allowed;
}

/* 清空登录凭据按钮 (危险操作精致幽灵样式) */
.btn-reset-auth {
  font-size: 0.72rem;
  color: #ef4444;
  background: #fef2f2;
  border: 1px solid #fee2e2;
  border-radius: 6px;
  padding: 4px 10px;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.18s cubic-bezier(0.16, 1, 0.3, 1);
}

.btn-reset-auth:hover:not(:disabled) {
  background: #fee2e2;
  border-color: #fca5a5;
  color: #dc2626;
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(239, 68, 68, 0.15);
}

.btn-reset-auth:active:not(:disabled) {
  transform: translateY(0);
}

.btn-reset-auth:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.reset-icon {
  display: inline-flex;
  color: #ef4444;
}

.reset-spinner {
  width: 12px;
  height: 12px;
  border: 2px solid #fca5a5;
  border-top-color: #dc2626;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  display: inline-block;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@media (max-width: 768px) {
  .sms-input {
    font-size: 16px !important;
    padding: 10px 12px;
  }
  .btn-sms-code {
    padding: 0 12px;
    font-size: 0.8rem;
  }
}
</style>
