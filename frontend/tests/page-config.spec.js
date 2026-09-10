import { describe, expect, it } from 'vitest';
import { pageConfigs } from '../src/config/pages';
describe('WMS 页面配置', () => {
    it('覆盖库存、入库和 AI 工作台，并保留真实业务字段', () => {
        expect(pageConfigs['/inventory']?.columns).toContain('系统 SKU');
        expect(pageConfigs['/inbounds']?.actions).toContain('新建入库单');
        expect(pageConfigs['/ai-workbench']?.title).toBe('AI 智能工作台');
    });
});
