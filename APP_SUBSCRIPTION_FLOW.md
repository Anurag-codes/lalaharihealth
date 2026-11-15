# App: yearly subscription (unlimited general consultations)

All requests need a patient access token: `Authorization: Bearer <access>`. Payment uses the same Razorpay React Native SDK as appointment checkout.

**What it covers:** unlimited **general physician** consultations for the **subscriber themself**, for 365 days.
Specialist bookings and bookings for family members are still paid normally.

## 1. Show the plan

`GET /api/v1/payments/subscription/?country_code=IN` (`country_code` is optional; use the one from pricing step 1)

```json
{"available": true, "country_code": "IN", "amount": 999, "currency": "INR", "amount_display": "₹999", "valid_days": 365,
 "is_active": false, "active_until": null, "can_purchase": true}
```

- `available: false`: staff haven't set a price, so hide the plan.
- `is_active: true`: show "Plan active until `active_until`".
- Show **Buy / Renew** only when `can_purchase` is `true`. Renewal opens in the last 30 days, and the renewal starts when the current plan ends.
- The same price is also returned as `subscription_fee` / `subscription_fee_display` in `GET /api/v1/pricing/`.

## 2. Buy

1. **Create order:** `POST /api/v1/payments/subscription/orders/` with body `{"country_code": "IN", "method": "upi"}` (or `"card"`).
   ```json
   {"subscription_id": 1, "gateway_order_id": "order_PJ9sB2yZaR3cD4", "key_id": "rzp_live_…", "amount": 99900, "currency": "INR", "status": "pending"}
   ```
   `amount` is in paise. The app never sends a price.
2. **Open Razorpay checkout** with `key_id`, `order_id = gateway_order_id`, `amount` and `currency`.
3. **On SDK success:** `POST /api/v1/payments/subscription/verify/`
   ```json
   {"subscription_id": 1, "razorpay_payment_id": "pay_…", "razorpay_signature": "<64 hex chars>"}
   ```
   The response has `status: "active"`, `starts_at` and `ends_at`. It is safe to retry.
   If the app closes before verifying, the Razorpay webhook activates the plan anyway. Re-read step 1.

## 3. Book while subscribed

There is no change in the booking calls; don't send a coupon.

- Case preview `GET /api/v1/consultations/{id}/preview/?starts_at=…` returns `fee: 0` when the plan covers that booking.
- `POST /api/v1/appointments/` returns `amount: 0`, `payment_required: false`, `payment_status: "not_required"` and `status: "finding_doctor"`.
  - **Skip checkout** whenever `payment_required` is `false`.
- The plan must be active at the chosen `starts_at`. Specialist and family-member bookings still return `payment_required: true`. Pay those as usual.

## Errors

- `400`: plan not offered, plan still has more than 30 days left, bad signature, or amount not captured (`detail` explains).
- `401`: not signed in.
- `403`: not a patient account.
- `404`: not your subscription.
- `503`: Razorpay is not configured on the server.
