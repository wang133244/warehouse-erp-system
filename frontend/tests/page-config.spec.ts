import { describe, expect, it } from 'vitest'
import { getBreadcrumbItems, menuGroups, pageConfigs } from '../src/config/pages'

describe('WMS 页面配置', () => {
  it('覆盖库存、入库和 AI 工作台，并保留真实业务字段', () => {
    expect(pageConfigs['/inventory']?.columns).toContain('系统 SKU')
    expect(pageConfigs['/inbounds']?.actions).toContain('新建入库单')
    expect(pageConfigs['/ai-workbench']?.title).toBe('AI 智能工作台')
  })

  it('为业务页面生成可点击的层级导航目标', () => {
    expect(getBreadcrumbItems('/inbounds')).toEqual([
      { label: '智能 ERP', path: '/overview' },
      { label: '入库管理', path: '/inbound-management' },
      { label: '入库单', path: undefined, current: true }
    ])
    expect(getBreadcrumbItems('/dashboard')).toEqual([
      { label: '智能 ERP', path: '/overview' },
      { label: '仓储运营看板', path: undefined, current: true }
    ])
  })

  it('一级菜单不再暴露重复的小字分组标题', () => {
    expect(menuGroups.every((group) => group.items.length === 1)).toBe(true)
  })
})
