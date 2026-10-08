<!-- 根组件，只挂路由出口。 -->
<!-- 页面脚本 -->
<script setup lang="ts">
// 引入路由出口组件，按当前路径渲染对应页面。
import { RouterView } from 'vue-router' // import { RouterView 
</script> <!-- 结束 script -->
<template> <!-- 页面模板 -->
  <!-- 根据路由表挂载当前匹配的视图。 -->
  <RouterView /> <!-- <RouterView /> -->
</template> <!-- 结束 template -->
