/** 把助手回复里的 Markdown 表拆成可渲染块。 */
export type MessageBlock = // 消息块联合类型
  | { type: 'text'; text: string } // 纯文本块
  | { type: 'table'; headers: string[]; rows: string[][] } // 表格块

function splitRow(line: string): string[] { // 把 Markdown 表格行拆成单元格
  return line // 从原始行开始处理
    .trim() // 去掉首尾空白
    .replace(/^\|/, '') // 去掉开头竖线
    .replace(/\|$/, '') // 去掉结尾竖线
    .split('|') // 按竖线切分
    .map((cell) => cell.trim()) // 每个单元格去空白
} // 结束 splitRow

function isTableRow(line: string): boolean { // 判断是否为表格数据行
  const trimmed = line.trim() // 去掉空白后再判断
  return trimmed.startsWith('|') && trimmed.endsWith('|') && trimmed.length > 1 // 需以竖线包裹且有内容
} // 结束 isTableRow

function isDivider(line: string): boolean { // 判断是否为表头分隔行
  const cells = splitRow(line) // 先拆成单元格
  return cells.length > 0 && cells.every((cell) => /^:?-{3,}:?$/.test(cell.replace(/\s/g, ''))) // 每个单元格都是 --- 对齐标记
} // 结束 isDivider

export function parseMessageBlocks(content: string): MessageBlock[] { // 把整段回复解析成文本/表格块
  const lines = (content || '').split(/\r?\n/) // 按行拆分，兼容空内容
  const blocks: MessageBlock[] = [] // 输出块列表
  let buffer: string[] = [] // 累积普通文本行
  let index = 0 // 当前行下标

  const flushText = () => { // 把缓冲文本刷成文本块
    const text = buffer.join('\n').trim() // 合并并去掉首尾空白
    buffer = [] // 清空缓冲
    if (text) blocks.push({ type: 'text', text }) // 有内容才推入文本块
  } // 结束 flushText

  while (index < lines.length) { // 逐行扫描
    if (isTableRow(lines[index]) && index + 1 < lines.length && isDivider(lines[index + 1])) { // 表头行后紧跟分隔行
      flushText() // 先刷出表格前的文本
      const headers = splitRow(lines[index]) // 解析表头
      index += 2 // 跳过表头和分隔行
      const rows: string[][] = [] // 表格数据行
      while (index < lines.length && isTableRow(lines[index]) && !isDivider(lines[index])) { // 后续仍是数据行
        rows.push(splitRow(lines[index])) // 解析并加入一行
        index += 1 // 前进一行
      } // 结束数据行循环
      blocks.push({ type: 'table', headers, rows }) // 推入表格块
      continue // 继续扫描后续内容
    } // 结束表格识别分支
    buffer.push(lines[index]) // 普通行进入文本缓冲
    index += 1 // 前进一行
  } // 结束 while
  flushText() // 刷出末尾文本
  return blocks.length ? blocks : [{ type: 'text', text: content || '' }] // 无块时退回整段文本
} // 结束 parseMessageBlocks
