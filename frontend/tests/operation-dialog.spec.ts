import { describe, expect, it } from 'vitest'
import { nextTick } from 'vue'
import { mount } from '@vue/test-utils'
import ElementPlus from 'element-plus'
import OperationDialog from '../src/components/business/OperationDialog.vue'

const products = [
  {
    product_id: 3,
    sku_code: 'SKU-003',
    source_product_code: 'P-003',
    brand: 'Mega',
    product_name: '测试商品',
    category: '分类',
    size: '标准',
    function_feature: '通用',
    color: '蓝色',
    pallet_spec: '120x100',
    pallet_capacity: 10
  }
]

const locations = [
  {
    location_id: 7,
    warehouse_id: 1,
    location_code: 'A-01-01-01',
    zone_code: 'A',
    aisle_code: '01',
    rack_code: '01',
    position_code: '01'
  }
]

const mountDialog = (action: string) =>
  mount(OperationDialog, {
    props: {
      modelValue: true,
      action,
      pageTitle: '业务页面',
      products,
      locations
    },
    global: { plugins: [ElementPlus] }
  })

async function fillCommonForm(wrapper: ReturnType<typeof mountDialog>) {
  await nextTick()
  await wrapper.find('input').setValue('UI-ORDER-001')
  const selects = wrapper.findAllComponents({ name: 'ElSelect' })
  await selects[0].vm.$emit('update:modelValue', 3)
  if (selects.length > 1) await selects[1].vm.$emit('update:modelValue', 7)
  const numberInputs = wrapper.findAllComponents({ name: 'ElInputNumber' })
  await numberInputs[numberInputs.length - 1].vm.$emit('update:modelValue', 5)
}

describe('业务操作弹窗', () => {
  it('submits a valid inbound order payload', async () => {
    const wrapper = mountDialog('新建入库单')
    await fillCommonForm(wrapper)

    const submitButton = wrapper.findAll('button').find((button) => button.text().includes('提交'))
    expect(submitButton).toBeDefined()
    await submitButton!.trigger('click')

    expect(wrapper.emitted('submit')?.[0]?.[0]).toEqual({
      type: 'inbound',
      payload: {
        order_no: 'UI-ORDER-001',
        note: null,
        items: [{ product_id: 3, location_id: 7, quantity: 5 }]
      }
    })
  })

  it('submits a valid outbound order payload', async () => {
  const wrapper = mountDialog('新建出库单')
  await nextTick()
  await wrapper.find('input').setValue('UI-OUT-001')
    const selects = wrapper.findAllComponents({ name: 'ElSelect' })
    await selects[0].vm.$emit('update:modelValue', 3)
    const numberInputs = wrapper.findAllComponents({ name: 'ElInputNumber' })
    await numberInputs[numberInputs.length - 1].vm.$emit('update:modelValue', 4)

    const submitButton = wrapper.findAll('button').find((button) => button.text().includes('提交'))
    await submitButton!.trigger('click')

    expect(wrapper.emitted('submit')?.[0]?.[0]).toEqual({
      type: 'outbound',
      payload: {
        order_no: 'UI-OUT-001',
        customer_id: null,
        note: null,
        items: [{ product_id: 3, quantity: 4 }]
      }
    })
  })
})
