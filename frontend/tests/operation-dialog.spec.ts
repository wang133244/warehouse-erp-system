/** 作业弹窗。 */
import { describe, expect, it } from 'vitest' // import { describe, expec
import { nextTick } from 'vue' // import { nextTick } from
import { mount } from '@vue/test-utils' // import { mount } from '@
import ElementPlus from 'element-plus' // import ElementPlus from 
import OperationDialog from '../src/components/business/OperationDialog.vue' // import OperationDialog f

const products = [ // const products = [
  { // {
    product_id: 3, // product_id: 3,
    sku_code: 'SKU-003', // sku_code: 'SKU-003',
    source_product_code: 'P-003', // source_product_code: 'P-
    brand: 'Mega', // brand: 'Mega',
    product_name: '测试商品', // product_name: '测试商品',
    category: '分类', // category: '分类',
    size: '标准', // size: '标准',
    function_feature: '通用', // function_feature: '通用',
    color: '蓝色', // color: '蓝色',
    pallet_spec: '120x100', // pallet_spec: '120x100',
    pallet_capacity: 10 // pallet_capacity: 10
  } // }
] // ]

const locations = [ // const locations = [
  { // {
    location_id: 7, // location_id: 7,
    warehouse_id: 1, // warehouse_id: 1,
    location_code: 'A-01-01-01', // location_code: 'A-01-01-
    zone_code: 'A', // zone_code: 'A',
    aisle_code: '01', // aisle_code: '01',
    rack_code: '01', // rack_code: '01',
    position_code: '01' // position_code: '01'
  } // }
] // ]

const mountDialog = (action: string) => // const mountDialog = (act
  mount(OperationDialog, { // mount(OperationDialog, {
    props: { // props: {
      modelValue: true, // modelValue: true,
      action, // action,
      pageTitle: '业务页面', // pageTitle: '业务页面',
      products, // products,
      locations // locations
    }, // },
    global: { plugins: [ElementPlus] } // global: { plugins: [Elem
  }) // })

async function fillCommonForm(wrapper: ReturnType<typeof mountDialog>) { // async function fillCommo
  await nextTick() // await nextTick()
  await wrapper.find('input').setValue('UI-ORDER-001') // await wrapper.find('inpu
  const selects = wrapper.findAllComponents({ name: 'ElSelect' }) // const selects = wrapper.
  await selects[0].vm.$emit('update:modelValue', 3) // await selects[0].vm.$emi
  if (selects.length > 1) await selects[1].vm.$emit('update:modelValue', 7) // if (selects.length > 1) 
  const numberInputs = wrapper.findAllComponents({ name: 'ElInputNumber' }) // const numberInputs = wra
  await numberInputs[numberInputs.length - 1].vm.$emit('update:modelValue', 5) // await numberInputs[numbe
} // }

describe('业务操作弹窗', () => { // describe('业务操作弹窗', () =>
  it('submits a valid inbound order payload', async () => { // it('submits a valid inbo
    const wrapper = mountDialog('新建入库单') // const wrapper = mountDia
    await fillCommonForm(wrapper) // await fillCommonForm(wra

    const submitButton = wrapper.findAll('button').find((button) => button.text().includes('提交')) // const submitButton = wra
    expect(submitButton).toBeDefined() // expect(submitButton).toB
    await submitButton!.trigger('click') // await submitButton!.trig

    expect(wrapper.emitted('submit')?.[0]?.[0]).toEqual({ // expect(wrapper.emitted('
      type: 'inbound', // type: 'inbound',
      payload: { // payload: {
        order_no: 'UI-ORDER-001', // order_no: 'UI-ORDER-001'
        note: null, // note: null,
        items: [{ product_id: 3, location_id: 7, quantity: 5 }] // items: [{ product_id: 3,
      } // }
    }) // })
  }) // })

  it('submits a valid outbound order payload', async () => { // it('submits a valid outb
  const wrapper = mountDialog('新建出库单') // const wrapper = mountDia
  await nextTick() // await nextTick()
  await wrapper.find('input').setValue('UI-OUT-001') // await wrapper.find('inpu
    const selects = wrapper.findAllComponents({ name: 'ElSelect' }) // const selects = wrapper.
    await selects[0].vm.$emit('update:modelValue', 3) // await selects[0].vm.$emi
    const numberInputs = wrapper.findAllComponents({ name: 'ElInputNumber' }) // const numberInputs = wra
    await numberInputs[numberInputs.length - 1].vm.$emit('update:modelValue', 4) // await numberInputs[numbe

    const submitButton = wrapper.findAll('button').find((button) => button.text().includes('提交')) // const submitButton = wra
    await submitButton!.trigger('click') // await submitButton!.trig

    expect(wrapper.emitted('submit')?.[0]?.[0]).toEqual({ // expect(wrapper.emitted('
      type: 'outbound', // type: 'outbound',
      payload: { // payload: {
        order_no: 'UI-OUT-001', // order_no: 'UI-OUT-001',
        customer_id: null, // customer_id: null,
        note: null, // note: null,
        items: [{ product_id: 3, quantity: 4 }] // items: [{ product_id: 3,
      } // }
    }) // })
  }) // })

  it('prefills inbound form from an assistant draft', async () => { // it('prefills inbound for
    const wrapper = mount(OperationDialog, { // const wrapper = mount(Op
      props: { // props: {
        modelValue: true, // modelValue: true,
        action: '新建入库单', // action: '新建入库单',
        pageTitle: '入库单', // pageTitle: '入库单',
        products, // products,
        locations, // locations,
        draft: { // draft: {
          type: 'inbound', // type: 'inbound',
          items: [{ sku_code: 'SKU-003', location_code: 'A-01-01-01', quantity: 2 }] // items: [{ sku_code: 'SKU
        } // }
      }, // },
      global: { plugins: [ElementPlus] } // global: { plugins: [Elem
    }) // })
    await nextTick() // await nextTick()
    const submitButton = wrapper.findAll('button').find((button) => button.text().includes('提交')) // const submitButton = wra
    await submitButton!.trigger('click') // await submitButton!.trig
    expect(wrapper.emitted('submit')?.[0]?.[0]).toEqual({ // expect(wrapper.emitted('
      type: 'inbound', // type: 'inbound',
      payload: { // payload: {
        order_no: expect.stringMatching(/^IN-/), // order_no: expect.stringM
        note: '来自智能助手草稿，请人工确认后保存。', // note: '来自智能助手草稿，请人工确认后保存
        items: [{ product_id: 3, location_id: 7, quantity: 2 }] // items: [{ product_id: 3,
      } // }
    }) // })
  }) // })
}) // })
