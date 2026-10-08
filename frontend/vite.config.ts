/** Vite 开发服务器、Vue 插件与 Vitest。 */
// 从 Vitest 配置入口引入 Vite 的 defineConfig，便于同时配置测试。
import { defineConfig } from 'vitest/config'
// 引入官方 Vue 单文件组件插件。
import vue from '@vitejs/plugin-vue'

// 导出 Vite / Vitest 的合并配置。
export default defineConfig({
  // 启用 Vue SFC 编译。
  plugins: [vue()],
  // 固定本机开发地址与端口，避免占用冲突。
  server: { host: '127.0.0.1', port: 5173 },
  // 生产构建相关选项。
  build: {
    // 交给 Rollup 的额外打包选项。
    rollupOptions: {
      // 控制产物如何拆包。
      output: {
        // 把框架与 UI 库拆成独立 chunk，减小主包体积。
        manualChunks: {
          // Vue 生态打成 vue chunk。
          vue: ['vue', 'vue-router', 'pinia'],
          // Element Plus 及其图标打成独立 chunk。
          'element-plus': ['element-plus', '@element-plus/icons-vue']
        }
      }
    }
  },
  // Vitest 单元测试配置。
  test: {
    // 使用 jsdom 模拟浏览器 DOM。
    environment: 'jsdom',
    // 允许测试文件使用全局 describe / it，无需手动导入。
    globals: true,
    // 只收集 tests 目录下的 spec 文件。
    include: ['tests/**/*.spec.ts'],
    // 排除依赖、产物和嵌套前端目录。
    exclude: ['**/node_modules/**', '**/dist/**', '**/frontend/frontend/**']
  }
})
