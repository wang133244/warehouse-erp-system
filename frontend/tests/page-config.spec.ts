/** 菜单与角色可见性。 */
import { describe, expect, it } from 'vitest' // import { describe, expec
import { // import {
  canAccessPath, // canAccessPath,
  canPerformAction, // canPerformAction,
  getBreadcrumbItems, // getBreadcrumbItems,
  menuGroups, // menuGroups,
  pageConfigs, // pageConfigs,
  visibleChildrenFor, // visibleChildrenFor,
  visibleMenuGroupsFor // visibleMenuGroupsFor
} from '../src/config/pages' // } from '../src/config/pa

describe('WMS 页面配置', () => { // describe('WMS 页面配置', () 
  it('覆盖库存、入库和 AI 工作台，并保留真实业务字段', () => { // it('覆盖库存、入库和 AI 工作台，并保留真
    expect(pageConfigs['/inventory']?.columns).toContain('系统 SKU') // expect(pageConfigs['/inv
    expect(pageConfigs['/inbounds']?.actions).toContain('新建入库单') // expect(pageConfigs['/inb
    expect(pageConfigs['/ai-workbench']?.title).toBe('AI 智能工作台') // expect(pageConfigs['/ai-
    expect(pageConfigs['/reports']?.title).toBe('仓储报表') // expect(pageConfigs['/rep
  }) // })

  it('为业务页面生成可点击的层级导航目标', () => { // it('为业务页面生成可点击的层级导航目标', 
    expect(getBreadcrumbItems('/inbounds')).toEqual([ // expect(getBreadcrumbItem
      { label: '智能 ERP', path: '/overview' }, // { label: '智能 ERP', path:
      { label: '入库管理', path: '/inbound-management' }, // { label: '入库管理', path: '
      { label: '待入库确认列表', path: undefined, current: true } // { label: '待入库确认列表', path
    ]) // ])
    expect(getBreadcrumbItems('/dashboard')).toEqual([ // expect(getBreadcrumbItem
      { label: '智能 ERP', path: '/overview' }, // { label: '智能 ERP', path:
      { label: '仓储运营看板', path: undefined, current: true } // { label: '仓储运营看板', path:
    ]) // ])
    expect(getBreadcrumbItems('/imports/12')).toEqual([ // expect(getBreadcrumbItem
      { label: '智能 ERP', path: '/overview' }, // { label: '智能 ERP', path:
      { label: '系统管理', path: '/system' }, // { label: '系统管理', path: '
      { label: '导入批次详情', path: undefined, current: true } // { label: '导入批次详情', path:
    ]) // ])
  }) // })

  it('一级菜单不再暴露重复的小字分组标题', () => { // it('一级菜单不再暴露重复的小字分组标题', 
    expect(menuGroups.every((group) => group.items.length === 1)).toBe(true) // expect(menuGroups.every(
  }) // })

  it('hides system management from non-admin menus', () => { // it('hides system managem
    expect(visibleMenuGroupsFor(['warehouse_operator']).some((group) => group.label === '系统管理')).toBe(false) // expect(visibleMenuGroups
    expect(visibleMenuGroupsFor(['admin']).some((group) => group.label === '系统管理')).toBe(true) // expect(visibleMenuGroups
    expect(canAccessPath('/users', ['warehouse_operator'])).toBe(false) // expect(canAccessPath('/u
    expect(canAccessPath('/imports/12', ['viewer'])).toBe(false) // expect(canAccessPath('/i
    expect(canAccessPath('/dashboard', ['warehouse_operator'])).toBe(true) // expect(canAccessPath('/d
    expect(canAccessPath('/users', ['admin'])).toBe(true) // expect(canAccessPath('/u
  }) // })

  it('hides write modules from viewer and keeps them for operators', () => { // it('hides write modules 
    const viewerMenus = visibleMenuGroupsFor(['viewer']).map((group) => group.label) // const viewerMenus = visi
    expect(viewerMenus).not.toContain('入库管理') // expect(viewerMenus).not.
    expect(viewerMenus).not.toContain('出库管理') // expect(viewerMenus).not.
    expect(viewerMenus).not.toContain('库存作业') // expect(viewerMenus).not.
    expect(viewerMenus).not.toContain('系统管理') // expect(viewerMenus).not.
    expect(viewerMenus).toContain('库存中心') // expect(viewerMenus).toCo
    expect(visibleMenuGroupsFor(['warehouse_operator']).map((group) => group.label)).toContain('入库管理') // expect(visibleMenuGroups
    expect(canAccessPath('/inbounds', ['viewer'])).toBe(false) // expect(canAccessPath('/i
    expect(canAccessPath('/counting', ['viewer'])).toBe(false) // expect(canAccessPath('/c
    expect(canAccessPath('/inbounds', ['warehouse_operator'])).toBe(true) // expect(canAccessPath('/i
    expect(canAccessPath('/receiving', ['warehouse_operator'])).toBe(true) // expect(canAccessPath('/r
    expect(canPerformAction('新建入库单', ['viewer'])).toBe(false) // expect(canPerformAction(
    expect(canPerformAction('导出库存', ['viewer'])).toBe(true) // expect(canPerformAction(
    expect(canPerformAction('新建入库单', ['warehouse_operator'])).toBe(true) // expect(canPerformAction(
    expect(visibleChildrenFor('/operations', ['viewer']).map((item) => item.path)).toEqual(['/alerts']) // expect(visibleChildrenFo
    expect(visibleChildrenFor('/inbound-management', ['warehouse_operator']).some((item) => item.path === '/receiving')).toBe(true) // expect(visibleChildrenFo
  }) // })
}) // })
