import { createApp } from 'vue';
import ElementPlus from 'element-plus';
import 'element-plus/dist/index.css';
import App from './App.vue';
import './assets/main.css';

// 自动清洗历史遗留或误输入的子路径（如 /login），保持地址栏纯净为根域名
if (window.location.pathname !== '/' && !window.location.pathname.startsWith('/api')) {
  window.history.replaceState(null, '', '/' + window.location.search + window.location.hash);
}

const app = createApp(App);
app.use(ElementPlus);
app.mount('#app');
