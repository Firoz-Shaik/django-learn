TAX_RATE = 12


def cart_totals(cart_items, coupon=None):
    total = sum(item.product.price * item.quantity for item in cart_items)
    discount = coupon.discount_for(total) if coupon else 0
    taxable = max(total - discount, 0)
    tax = round((TAX_RATE * taxable) / 100, 2)
    grand_total = round(taxable + tax, 2)
    return {
        'total': total,
        'discount': discount,
        'tax': tax,
        'grand_total': grand_total,
        'coupon': coupon,
    }
