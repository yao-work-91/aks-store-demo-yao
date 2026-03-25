'use strict'

const { test } = require('tap')
const { build } = require('../helper')

const validOrder = {
  storeId: 'store-1',
  customerOrderId: 'order-abc',
  items: [
    { productId: 1, quantity: 2 }
  ]
}

test('POST / accepts a valid order and returns 201', async (t) => {
  const app = await build(t)

  const res = await app.inject({
    method: 'POST',
    url: '/',
    payload: validOrder
  })
  t.equal(res.statusCode, 201)
})

test('POST / returns 400 when storeId is missing', async (t) => {
  const app = await build(t)

  const res = await app.inject({
    method: 'POST',
    url: '/',
    payload: { customerOrderId: 'order-abc', items: [{ productId: 1, quantity: 1 }] }
  })
  t.equal(res.statusCode, 400)
})

test('POST / returns 400 when customerOrderId is missing', async (t) => {
  const app = await build(t)

  const res = await app.inject({
    method: 'POST',
    url: '/',
    payload: { storeId: 'store-1', items: [{ productId: 1, quantity: 1 }] }
  })
  t.equal(res.statusCode, 400)
})

test('POST / returns 400 when items is missing', async (t) => {
  const app = await build(t)

  const res = await app.inject({
    method: 'POST',
    url: '/',
    payload: { storeId: 'store-1', customerOrderId: 'order-abc' }
  })
  t.equal(res.statusCode, 400)
})

test('POST / returns 400 when items array is empty', async (t) => {
  const app = await build(t)

  const res = await app.inject({
    method: 'POST',
    url: '/',
    payload: { storeId: 'store-1', customerOrderId: 'order-abc', items: [] }
  })
  t.equal(res.statusCode, 400)
})

test('POST / returns 400 when item is missing productId', async (t) => {
  const app = await build(t)

  const res = await app.inject({
    method: 'POST',
    url: '/',
    payload: { storeId: 'store-1', customerOrderId: 'order-abc', items: [{ quantity: 1 }] }
  })
  t.equal(res.statusCode, 400)
})

test('POST / returns 400 when item is missing quantity', async (t) => {
  const app = await build(t)

  const res = await app.inject({
    method: 'POST',
    url: '/',
    payload: { storeId: 'store-1', customerOrderId: 'order-abc', items: [{ productId: 1 }] }
  })
  t.equal(res.statusCode, 400)
})

test('POST / returns 400 when item quantity is zero', async (t) => {
  const app = await build(t)

  const res = await app.inject({
    method: 'POST',
    url: '/',
    payload: { storeId: 'store-1', customerOrderId: 'order-abc', items: [{ productId: 1, quantity: 0 }] }
  })
  t.equal(res.statusCode, 400)
})

test('GET /health returns ok', async (t) => {
  const app = await build(t)

  const res = await app.inject({ url: '/health' })
  t.equal(res.statusCode, 200)
  t.same(JSON.parse(res.payload), { status: 'ok', version: '0.1.0' })
})
