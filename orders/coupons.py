from orders.models import Coupon


def coupon_from_session(request, subtotal=None):
    coupon_id = request.session.get('coupon_id')
    if not coupon_id:
        return None
    coupon = Coupon.objects.filter(pk=coupon_id).first()
    if coupon is None or not coupon.is_valid(subtotal):
        request.session.pop('coupon_id', None)
        return None
    return coupon
