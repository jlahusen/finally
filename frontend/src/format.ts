const usd = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' })

export const money = (n: number) => usd.format(n)

export const signedMoney = (n: number) => (n > 0 ? '+' : '') + usd.format(n)

export const percent = (n: number) => `${n > 0 ? '+' : ''}${n.toFixed(2)}%`

export const quantity = (n: number) => String(Number(n.toFixed(4)))

/** Tailwind text color class for a signed value. */
export const tone = (n: number) => (n > 0 ? 'text-up' : n < 0 ? 'text-down' : 'text-muted')

/** Direction bucket of a signed value, used for data attributes. */
export const sign = (n: number) => (n > 0 ? 'up' : n < 0 ? 'down' : 'flat')
