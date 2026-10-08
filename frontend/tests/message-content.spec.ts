/** Markdown 表解析。 */
import { describe, expect, it } from 'vitest' // import { describe, expec
import { parseMessageBlocks } from '../src/controllers/messageContent' // import { parseMessageBlo

describe('parseMessageBlocks', () => { // describe('parseMessageBl
  it('splits markdown tables from surrounding text', () => { // it('splits markdown tabl
    const blocks = parseMessageBlocks('ABC 分类如下：\n| SKU | 分类 |\n| --- | --- |\n| SKU-1 | A |\n请人工确认。') // const blocks = parseMess
    expect(blocks).toEqual([ // expect(blocks).toEqual([
      { type: 'text', text: 'ABC 分类如下：' }, // { type: 'text', text: 'A
      { type: 'table', headers: ['SKU', '分类'], rows: [['SKU-1', 'A']] }, // { type: 'table', headers
      { type: 'text', text: '请人工确认。' } // { type: 'text', text: '请
    ]) // ])
  }) // })

  it('returns a single text block when there is no table', () => { // it('returns a single tex
    expect(parseMessageBlocks('查询到库存')).toEqual([{ type: 'text', text: '查询到库存' }]) // expect(parseMessageBlock
  }) // })
}) // })
