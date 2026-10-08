<!-- 仓储助手会话页（微信气泡）。 -->
<!-- 页面脚本 -->
<script setup lang="ts">
// 引入页头组件。
import PageHeader from '../components/common/PageHeader.vue' // import PageHeader fr
// 引入空状态组件。
import EmptyDataState from '../components/common/EmptyDataState.vue' // import EmptyDataStat
// 引入助手页控制器。
import { useAssistantController } from '../controllers/assistantController' // import { useAssistan
// 把消息正文解析成文本块或表格块。
import { parseMessageBlocks } from '../controllers/messageContent' // import { parseMessag
// 助手草稿类型，用于「带入单据」。
import type { OperationDraft } from '../stores/app' // import type { Operat

// 从控制器取出会话、消息与发送动作。
const { // const {
  // 页面文案配置。
  config, // config,
  // 路由实例。
  router, // router,
  // 全局应用状态。
  app, // app,
  // 会话列表。
  sessions, // sessions,
  // 当前会话消息。
  messages, // messages,
  // 当前会话 ID。
  activeId, // activeId,
  // 输入框问题。
  question, // question,
  // 发送中。
  sending, // sending,
  // 错误文案。
  errorMessage, // errorMessage,
  // LLM 提供方。
  llmProvider, // llmProvider,
  // 引擎标签，如 LangGraph。
  engineLabel, // engineLabel,
  // 当前会话对象。
  activeSession, // activeSession,
  // 本轮引用的数据源名。
  citations, // citations,
  // 用户头像首字母。
  userInitial, // userInitial,
  // 聊天滚动容器引用。
  wechatBody, // wechatBody,
  // 加载会话列表。
  loadSessions, // loadSessions,
  // 加载当前会话消息。
  loadMessages, // loadMessages,
  // 新建会话。
  createSession, // createSession,
  // 清空当前会话消息。
  clearSession, // clearSession,
  // 正在删除的会话 ID。
  deletingId, // deletingId,
  // 从列表移除会话。
  removeSessionFromList, // removeSessionFromLis
  // 删除会话。
  deleteSession, // deleteSession,
  // 发送问题。
  send, // send,
  // 把草稿带入作业弹窗。
  applyDraft // applyDraft
} = useAssistantController() // } = useAssistantCont

</script> <!-- 结束 script -->

<template> <!-- 页面模板 -->
  <!-- 助手页主容器。 -->
  <main class="workspace-page" data-testid="assistant-page"> <!-- <main class="workspa -->
    <!-- 页头。 -->
    <PageHeader :title="config.title" :subtitle="config.subtitle" :section="config.section" /> <!-- <PageHeader :title=" -->
    <!-- 左会话、中聊天、右引用 三栏。 -->
    <section class="ai-grid"> <!-- <section class="ai-g -->
      <!-- 会话列表卡片。 -->
      <el-card class="session-card" shadow="never"> <!-- <el-card class="sess -->
        <!-- 会话列表标题与操作。 -->
        <template #header> <!-- 页面模板 -->
          <!-- 标题行：清空 / 新建。 -->
          <div class="card-title"> <!-- <div class="card-tit -->
            <!-- 区块标题。 -->
            <span>会话列表</span> <!-- <span>会话列表</span> -->
            <!-- 会话操作按钮组。 -->
            <div> <!-- <div> -->
              <!-- 清空当前会话消息。 -->
              <el-button plain size="small" data-testid="clear-session" @click="clearSession">清空会话</el-button> <!-- <el-button plain siz -->
              <!-- 新建空会话。 -->
              <el-button type="primary" plain size="small" data-testid="new-session" @click="createSession">新建会话</el-button> <!-- <el-button type="pri -->
            </div> <!-- 结束 div -->
          </div> <!-- 结束 div -->
        </template> <!-- 结束 template -->
        <!-- 每个会话一行：标题 + 删除。 -->
        <div
          v-for="session in sessions"
          :key="session.session_id"
          class="session-item"
          :class="{ active: session.session_id === activeId }"
          :data-testid="`session-${session.session_id}`"
          @click="activeId = session.session_id"
        > <!-- > -->
          <!-- 会话标题，过长省略。 -->
          <span class="session-select">{{ session.title }}</span> <!-- <span class="session -->
          <!-- 删除该会话，阻止冒泡以免切到被删会话。 -->
          <el-button
            text
            type="danger"
            size="small"
            :disabled="deletingId === session.session_id"
            :data-testid="`delete-session-${session.session_id}`"
            @click.stop="deleteSession(session)"
          >删除</el-button> <!-- >删除</el-button> -->
        </div> <!-- 结束 div -->
        <!-- 无会话时的占位。 -->
        <EmptyDataState v-if="!sessions.length" title="暂无会话" description="可以新建会话后查询库存、预警和草稿建议。" /> <!-- <EmptyDataState v-if -->
      </el-card> <!-- 结束 el-card -->
      <!-- 对话卡片。 -->
      <el-card class="conversation-card" shadow="never"> <!-- <el-card class="conv -->
        <!-- 对话标题与引擎标签。 -->
        <template #header> <!-- 页面模板 -->
          <!-- 标题行。 -->
          <div class="card-title"> <!-- <div class="card-tit -->
            <!-- 区块标题。 -->
            <span>智能分析</span> <!-- <span>智能分析</span> -->
            <!-- 当前编排引擎。 -->
            <el-tag type="success" effect="plain" data-testid="graph-engine-tag">{{ engineLabel }}</el-tag> <!-- <el-tag type="succes -->
          </div> <!-- 结束 div -->
        </template> <!-- 结束 template -->
        <!-- 微信风格聊天面板。 -->
        <div class="wechat-panel"> <!-- <div class="wechat-p -->
          <!-- 消息滚动区。 -->
          <div ref="wechatBody" class="wechat-body"> <!-- <div ref="wechatBody -->
            <!-- 无消息时的引导。 -->
            <EmptyDataState v-if="!messages.length" title="开始提问" description="例如：查询 SKU-1 的可用库存，或把 ABC 分类制成表格。助手只查询和生成草稿，不会直接改库存。" /> <!-- <EmptyDataState v-if -->
            <!-- 每条消息一行气泡。 -->
            <div
              v-for="message in messages"
              :key="message.message_id"
              class="wechat-row"
              :class="message.role === 'user' ? 'wechat-row--mine' : 'wechat-row--theirs'"
            > <!-- > -->
              <!-- 头像：用户首字母或「助」。 -->
              <div class="wechat-avatar" :class="message.role === 'user' ? 'wechat-avatar--mine' : 'wechat-avatar--theirs'"> <!-- <div class="wechat-a -->
                {{ message.role === 'user' ? userInitial : '助' }} <!-- {{ message.role ===  -->
              </div> <!-- 结束 div -->
              <!-- 气泡内容：文本、表格、草稿按钮。 -->
              <div class="wechat-bubble"> <!-- <div class="wechat-b -->
                <!-- 把正文拆成多个块渲染。 -->
                <template v-for="(block, index) in parseMessageBlocks(message.content)" :key="`${message.message_id}-${index}`"> <!-- 页面模板 -->
                  <!-- 普通文本块。 -->
                  <p v-if="block.type === 'text'" class="wechat-text">{{ block.text }}</p> <!-- <p v-if="block.type  -->
                  <!-- Markdown 表格块。 -->
                  <div v-else class="wechat-table-wrap" data-testid="chat-table"> <!-- <div v-else class="w -->
                    <!-- 简易 HTML 表。 -->
                    <table> <!-- <table> -->
                      <!-- 表头。 -->
                      <thead> <!-- <thead> -->
                        <!-- 表头行。 -->
                        <tr> <!-- <tr> -->
                          <!-- 每个表头单元格。 -->
                          <th v-for="header in block.headers" :key="header">{{ header }}</th> <!-- <th v-for="header in -->
                        </tr> <!-- 结束 tr -->
                      </thead> <!-- 结束 thead -->
                      <!-- 表体。 -->
                      <tbody> <!-- <tbody> -->
                        <!-- 数据行。 -->
                        <tr v-for="(row, rowIndex) in block.rows" :key="rowIndex"> <!-- <tr v-for="(row, row -->
                          <!-- 单元格。 -->
                          <td v-for="(cell, cellIndex) in row" :key="cellIndex">{{ cell }}</td> <!-- <td v-for="(cell, ce -->
                        </tr> <!-- 结束 tr -->
                      </tbody> <!-- 结束 tbody -->
                    </table> <!-- 结束 table -->
                  </div> <!-- 结束 div -->
                </template> <!-- 结束 template -->
                <!-- 入出库/盘点草稿可带入单据。 -->
                <el-button
                  v-if="message.draft && ['inbound', 'outbound', 'counting'].includes(String(message.draft.type))"
                  type="primary"
                  link
                  data-testid="apply-draft"
                  @click="applyDraft(message.draft as unknown as OperationDraft)"
                >带入单据</el-button> <!-- >带入单据</el-button> -->
              </div> <!-- 结束 div -->
            </div> <!-- 结束 div -->
          </div> <!-- 结束 div -->
          <!-- 底部输入条。 -->
          <div class="wechat-composer"> <!-- <div class="wechat-c -->
            <!-- 问题输入，Enter 发送。 -->
            <el-input
              v-model="question"
              type="textarea"
              :autosize="{ minRows: 1, maxRows: 4 }"
              placeholder="发消息…"
              @keydown.enter.exact.prevent="send"
            /> <!-- /> -->
            <!-- 发送按钮。 -->
            <el-button class="wechat-send" :loading="sending" data-testid="send-question" @click="send">发送</el-button> <!-- <el-button class="we -->
          </div> <!-- 结束 div -->
        </div> <!-- 结束 div -->
      </el-card> <!-- 结束 el-card -->
      <!-- 数据引用卡片。 -->
      <el-card class="source-card" shadow="never"> <!-- <el-card class="sour -->
        <!-- 引用标题。 -->
        <template #header><div class="card-title">数据引用</div></template> <!-- 页面模板 -->
        <!-- 有引用时展示标签。 -->
        <div v-if="citations.length" class="citations"> <!-- <div v-if="citations -->
          <!-- 每个数据源一个标签。 -->
          <el-tag v-for="name in citations" :key="name" effect="plain">{{ name }}</el-tag> <!-- <el-tag v-for="name  -->
        </div> <!-- 结束 div -->
        <!-- 无引用时的说明。 -->
        <EmptyDataState v-else title="暂无引用" description="助手由 LangGraph 编排白名单工具，不会执行原始 SQL。" /> <!-- <EmptyDataState v-el -->
        <!-- 错误文案。 -->
        <p v-if="errorMessage" class="hint">{{ errorMessage }}</p> <!-- <p v-if="errorMessag -->
        <!-- 当前会话名。 -->
        <p v-if="activeSession" class="hint">当前会话：{{ activeSession.title }}</p> <!-- <p v-if="activeSessi -->
      </el-card> <!-- 结束 el-card -->
    </section> <!-- 结束 section -->
  </main> <!-- 结束 main -->
</template> <!-- 结束 template -->

<!-- 页面样式 -->
<style scoped>
/* 工作台页边距与最大宽度。 */
.workspace-page { padding: 26px 30px 35px; max-width: 1680px; margin: 0 auto; } /* .workspace-page { pa */
/* 三栏网格：会话、对话、引用。 */
.ai-grid { display: grid; grid-template-columns: 255px minmax(430px, 1fr) 280px; gap: 16px; } /* .ai-grid { display:  */
/* 卡片标题左右排布。 */
.card-title { display: flex; align-items: center; justify-content: space-between; font-weight: 700; } /* .card-title { displa */
/* 会话行：标题弹性、删除按钮靠右。 */
.session-item { width: 100%; display: flex; align-items: center; gap: 8px; border: 0; background: transparent; text-align: left; padding: 6px 8px 6px 12px; border-radius: 8px; cursor: pointer; color: #334155; } /* .session-item { widt */
/* 会话标题过长省略。 */
.session-select { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; } /* .session-select { fl */
/* 当前/悬停会话浅蓝底。 */
.session-item.active, .session-item:hover { background: #edf4ff; } /* .session-item.active */
/* 对话卡片去掉默认内边距，让聊天区铺满。 */
.conversation-card :deep(.el-card__body) { padding: 0; } /* .conversation-card : */
/* 聊天面板纵向：消息区 + 输入条。 */
.wechat-panel { display: flex; flex-direction: column; min-height: 420px; background: #ededed; } /* .wechat-panel { disp */
/* 消息区可滚动。 */
.wechat-body { flex: 1; min-height: 280px; max-height: 520px; overflow: auto; padding: 16px 12px 8px; display: flex; flex-direction: column; gap: 14px; } /* .wechat-body { flex: */
/* 消息行：头像 + 气泡。 */
.wechat-row { display: flex; align-items: flex-start; gap: 8px; max-width: 100%; } /* .wechat-row { displa */
/* 自己的消息左右对调。 */
.wechat-row--mine { flex-direction: row-reverse; } /* .wechat-row--mine {  */
/* 方形头像。 */
.wechat-avatar { width: 36px; height: 36px; border-radius: 4px; color: #fff; font-size: 14px; font-weight: 700; display: grid; place-items: center; flex: none; } /* .wechat-avatar { wid */
/* 助手头像蓝。 */
.wechat-avatar--theirs { background: #5078f0; } /* .wechat-avatar--thei */
/* 用户头像绿。 */
.wechat-avatar--mine { background: #2ba245; } /* .wechat-avatar--mine */
/* 气泡最大宽度与阴影。 */
.wechat-bubble { max-width: min(78%, 460px); padding: 8px 10px; border-radius: 4px; line-height: 1.55; font-size: 14px; word-break: break-word; box-shadow: 0 1px 1px rgba(0, 0, 0, 0.04); } /* .wechat-bubble { max */
/* 助手气泡白底。 */
.wechat-row--theirs .wechat-bubble { background: #fff; color: #111; } /* .wechat-row--theirs  */
/* 用户气泡微信绿。 */
.wechat-row--mine .wechat-bubble { background: #95ec69; color: #111; } /* .wechat-row--mine .w */
/* 文本块保留换行。 */
.wechat-text { margin: 0; white-space: pre-wrap; } /* .wechat-text { margi */
/* 文本与表格相邻时留白。 */
.wechat-text + .wechat-table-wrap, .wechat-table-wrap + .wechat-text { margin-top: 8px; } /* .wechat-text + .wech */
/* 表格横向滚动。 */
.wechat-table-wrap { overflow-x: auto; background: #fff; border-radius: 4px; } /* .wechat-table-wrap { */
/* 用户气泡内表格半透明白底。 */
.wechat-row--mine .wechat-table-wrap { background: rgba(255, 255, 255, 0.55); } /* .wechat-row--mine .w */
/* 表格边框合并。 */
.wechat-table-wrap table { border-collapse: collapse; min-width: 100%; font-size: 12px; } /* .wechat-table-wrap t */
/* 单元格细边框与不换行。 */
.wechat-table-wrap th, .wechat-table-wrap td { border: 1px solid #d8d8d8; padding: 4px 8px; text-align: left; white-space: nowrap; } /* .wechat-table-wrap t */
/* 表头浅灰加粗。 */
.wechat-table-wrap th { background: #f7f7f7; font-weight: 700; } /* .wechat-table-wrap t */
/* 底部输入条。 */
.wechat-composer { display: flex; align-items: flex-end; gap: 8px; padding: 10px 12px; background: #f7f7f7; border-top: 1px solid #e5e5e5; } /* .wechat-composer { d */
/* 输入框占满剩余宽度。 */
.wechat-composer :deep(.el-textarea) { flex: 1; } /* .wechat-composer :de */
/* 去掉输入框默认阴影。 */
.wechat-composer :deep(.el-textarea__inner) { box-shadow: none; background: #fff; } /* .wechat-composer :de */
/* 发送按钮微信绿。 */
.wechat-send { background: #07c160; border-color: #07c160; color: #fff; } /* .wechat-send { backg */
/* 发送按钮悬停加深。 */
.wechat-send:hover { background: #06ad56; border-color: #06ad56; color: #fff; } /* .wechat-send:hover { */
/* 引用标签折行。 */
.citations { display: flex; flex-wrap: wrap; gap: 8px; } /* .citations { display */
/* 提示文字小号灰色。 */
.hint { color: var(--muted); font-size: 12px; } /* .hint { color: var(- */
/* 窄屏三栏改单列。 */
@media (max-width: 1100px) { .ai-grid { grid-template-columns: 1fr; } } /* @media (max-width: 1 */
</style> <!-- 结束 style -->
