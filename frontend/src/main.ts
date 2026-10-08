/** Vue 应用入口：Pinia、路由、Element Plus。 */
import { createApp } from 'vue' // 从 Vue 引入创建应用实例的工厂函数
import { createPinia } from 'pinia' // 引入 Pinia 状态管理工厂
import ElementPlus from 'element-plus' // 引入 Element Plus UI 组件库
import 'element-plus/dist/index.css' // 引入 Element Plus 默认样式
import './styles/index.scss' // 引入项目全局样式
import App from './App.vue' // 引入根组件
import router from './router' // 引入路由实例

createApp(App).use(createPinia()).use(router).use(ElementPlus).mount('#app') // 创建应用并挂载到 #app
