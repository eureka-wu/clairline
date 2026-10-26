<template>
  <div v-if="visible" class="modal-overlay" @click.self="closeModal">
    <div class="modal-card" style="max-width: 480px;">
      <!-- 模态框头部 -->
      <div class="modal-header">
        <div style="font-weight:800; font-size:1.05rem; display:flex; align-items:center; gap:8px;">
          <span v-html="ICONS.phone" style="color:var(--accent-cyan);"></span>
          <span>长龙航空 · 手机验证码登录 (免抓包)</span>
        </div>
        <button type="button" class="btn-popover-close" style="font-size:1.3rem;" @click="closeModal">&times;</button>
      </div>

      <!-- 模态框主体 -->
      <div class="modal-body" style="padding:16px 20px;">
        
        <!-- 当前状态卡片 -->
        <div 
          style="padding:12px 14px; border-radius:8px; margin-bottom:14px;"
          :style="{ 
            background: effectiveAuth?.is_logged_in ? '#f0fdf4' : '#fffbeb',
            border: effectiveAuth?.is_logged_in ? '1px solid #bbf7d0' : '1px solid #fde68a'
          }"
        >
          <div style="display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:8px;">
            <div style="display:flex; align-items:center; gap:10px;">
              <span 
                style="width:10px; height:10px; border-radius:50%; display:inline-block;"
                :style="{ background: effectiveAuth?.is_logged_in ? '#10b981' : '#f59e0b' }"
              ></span>
              <div>
                <div style="font-size:0.85rem; font-weight:800; color:var(--text-primary); display:flex; align-items:center; gap:6px;">
                  <span>{{ effectiveAuth?.is_logged_in ? effectiveAuth.user_name : '尚未登录长龙会员' }}</span>
                  <span 
                    v-if="effectiveAuth?.is_logged_in && (effectiveAuth.is_verified || effectiveAuth.user_name !== '长龙会员')"
                    style="font-size:0.65rem; padding:1px 5px; border-radius:3px; background:#dcfce7; color:#15803d; font-weight:700;"
                  >
                    已实名
                  </span>
                </div>
                <div style="font-size:0.72rem; color:var(--text-muted); margin-top:2px;">
                  {{ effectiveAuth?.is_logged_in ? `手机: ${effectiveAuth.mobile || '已同步'} · 更新: ${effectiveAuth.update_time || '刚刚'}` : '登录后即可实时解锁航班剩余机位与全网航线放票日历' }}
                </div>
              </div>
            </div>
            <span 
              v-if="effectiveAuth?.is_logged_in"
              style="font-size:0.72rem; padding:3px 9px; border-radius:4px; background:#e0f2fe; color:#0284c7; font-weight:800; display:inline-flex; align-items:center; gap:4px;"
            >
              <span v-html="ICONS.crown" style="display:inline-flex;"></span>
              <span>{{ effectiveAuth.member_level || '乘云会员' }}</span>
            </span>
          </div>
        </div>

        <!-- 场景 1：已经登录且没有主动切换账号 -->
        <div 
          v-if="effectiveAuth?.is_logged_in && !showResyncFlow"
          style="background:#f0fdf4; border:1px solid #bbf7d0; border-radius:8px; padding:18px 14px; text-align:center;"
        >
          <div style="display:inline-flex; margin-bottom:6px; color:#10b981;" v-html="ICONS.checkCircle"></div>
          <div style="font-size:0.92rem; font-weight:800; color:#047857; margin-bottom:4px;">
            长龙会员凭证已生效
          </div>
          <div style="font-size:0.75rem; color:#065f46; line-height:1.5; margin-bottom:14px;">
            已绑定会员「{{ effectiveAuth.user_name }}」，畅飞卡（{{ effectiveAuth.card_name || '长龙畅飞卡' }}）剩余机位与普查功能处于就绪状态。
          </div>
          <button 
            type="button" 
            class="btn-glass" 
            style="font-size:0.75rem; color:#0284c7; border-color:#bae6fd; padding:5px 14px; background:#ffffff; display:inline-flex; align-items:center; gap:5px; margin:0 auto;"
            @click="showResyncFlow = true"
          >
            <span v-html="ICONS.refresh" style="display:inline-flex;"></span>
            <span>切换其他手机号登录</span>
          </button>
        </div>

        <!-- 场景 2：输入手机号与验证码 -->
        <div v-else style="background:#f8fafc; border:1px solid var(--border-subtle); border-radius:8px; padding:16px 14px;">
          <div style="font-size:0.82rem; font-weight:700; color:var(--text-primary); margin-bottom:12px; display:flex; align-items:center; gap:6px;">
            <span v-html="ICONS.phone" style="color:var(--accent-cyan);"></span>
            <span>长龙官方短信快捷登录</span>
            <span style="font-size:0.65rem; background:#dcfce7; color:#15803d; padding:1px 5px; border-radius:4px; font-weight:700;">免抓包 / 零代理</span>
          </div>

          <!-- 手机号输入 -->
          <div style="margin-bottom:12px;">
            <label style="display:block; font-size:0.72rem; color:var(--text-muted); margin-bottom:5px; font-weight:600;">会员手机号</label>
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
                class="sms-input"
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

          <!-- 登录按钮 -->
          <button 
            type="button" 
            class="btn-primary" 
            style="width:100%; padding:9px 0; font-size:0.85rem; justify-content:center; display:inline-flex; align-items:center; gap:6px; font-weight:700; border-radius:6px;"
            :disabled="!mobile || !smsCode || isSubmittingLogin"
            @click="handleSmsLogin"
          >
            <span v-html="ICONS.check" style="display:inline-flex;"></span>
            <span>{{ isSubmittingLogin ? '正在验证并同步会员...' : '立即登录并同步会员' }}</span>
          </button>

          <div style="margin-top:10px; font-size:0.7rem; color:#94a3b8; line-height:1.5;">
            💡 点击【获取验证码】将唤起长龙官方网易易盾安全验证。验证通过后长龙官方短信通道下发验证码，全程直连官方接口，无需安装证书或配置系统代理。
          </div>

          <!-- 挂载易盾组件的隐藏节点 -->
          <div id="yidun-captcha-box" style="display:none;"></div>
        </div>

      </div>

      <!-- 模态框底部 -->
      <div class="modal-footer" style="justify-content: space-between; align-items:center;">
        <button 
          type="button" 
          class="btn-glass" 
          style="font-size:0.7rem; color:#ef4444; border-color:#fecaca; padding:3px 8px;"
          title="清空数据库个人信息，还原为新用户状态"
          @click="handleResetAuth"
        >
          清空登录态 (重置)
        </button>
        <div style="display:flex; align-items:center; gap:12px;">
          <a 
            href="https://github.com/eureka-wu/clairline/tree/test-phone" 
            target="_blank" 
            rel="noopener noreferrer"
            style="font-size:0.7rem; color:var(--text-muted); text-decoration:none; display:inline-flex; align-items:center; gap:4px;"
            title="GitHub 开源仓库"
          >
            <span v-html="ICONS.github" style="display:inline-flex;"></span>
            <span>clairline (test-phone)</span>
          </a>
          <button type="button" class="btn-glass" style="font-size:0.78rem;" @click="closeModal">关闭</button>
        </div>
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
let captchaInstance = null;
const localAuth = ref(null);

const effectiveAuth = computed(() => {
  return localAuth.value || props.authStatus || {};
});

watch(() => props.visible, (val) => {
  if (val) {
    localAuth.value = null;
    showResyncFlow.value = false;
    emit('refresh-auth');
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
          isVerifyingCaptcha.value = false;
          notify('验证出错', err.message || '请重新完成安全验证', 'error');
          return;
        }
        const validate = data?.validate || '';
        if (!validate) {
          isVerifyingCaptcha.value = false;
          notify('验证未完成', '未获取到安全验证凭证', 'warning');
          return;
        }
        try {
          const res = await sendSmsCode(m, validate);
          verifyId.value = res.verifyId || '';
          notify('短信验证码已下发', res.message || '长龙官方已发送验证码，请查收短信！', 'success');
          startCountdown();
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
      notify('登录成功', res.message || '已成功绑定长龙会员！', 'success');
      showResyncFlow.value = false;
      smsCode.value = '';
      if (res.user) {
        localAuth.value = {
          is_logged_in: true,
          ...res.user
        };
      }
      emit('refresh-auth', localAuth.value);
      emit('synced');
      setTimeout(() => {
        closeModal();
      }, 600);
    } else {
      notify('登录失败', res.error || '验证码错误或已过期', 'error');
    }
  } catch (e) {
    notify('登录异常', e.message || '网络连接超时', 'error');
  } finally {
    isSubmittingLogin.value = false;
  }
}

async function handleResetAuth() {
  if (!confirm('确定清空本地登录凭据与会员信息？将还原为未登录状态。')) return;
  try {
    const res = await resetAuth();
    if (res.ok) {
      notify('重置成功', '已清空本地会员凭证，已恢复未登录状态！', 'success');
      showResyncFlow.value = false;
      localAuth.value = { is_logged_in: false, user_name: '尚未登录长龙会员' };
      emit('refresh-auth');
      emit('synced');
    }
  } catch (e) {
    notify('重置失败', e.message || '重置异常', 'error');
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
</style>
