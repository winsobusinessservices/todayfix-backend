# Finance API Plan

## 1. Billing (`/api/billing/`)
- `POST /api/billing/preview/`: Preview billing calculations (fees, taxes, coin discount) without saving.
- `POST /api/billing/create/`: Create a draft `BillingRecord` for a Booking/InstantBooking.
- `GET /api/billing/{uuid}/`: Retrieve a specific billing record.
- `POST /api/billing/{uuid}/confirm/`: Finalize the billing record and lock in the snapshot.
- `POST /api/billing/{uuid}/adjustment/`: Create a new billing version for extended services/materials.
- `GET /api/billing/{uuid}/history/`: View billing versions/adjustments history.

## 2. Payments (`/api/payments/`)
- `POST /api/payments/order/`: Generate a `PaymentOrder` and Razorpay Order ID for a finalized billing record.
- `POST /api/payments/verify/`: Verify Razorpay signature from frontend callback.
- `GET /api/payments/{uuid}/`: Retrieve a specific payment order/transaction.
- `GET /api/payments/history/`: Retrieve payment history for the authenticated user.
- `POST /api/payments/{uuid}/refund/`: Initiate a full or partial refund.
- `POST /api/payments/webhooks/razorpay/`: Endpoint for Razorpay server-to-server webhooks (idempotent).

## 3. Business Payouts (`/api/payouts/`)
- `GET /api/payouts/balance/`: Get business pending, available, and lifetime balances.
- `GET /api/payouts/eligibility/`: Check max eligible payout (70% rule) and emergency quotas.
- `POST /api/payouts/request/`: Request a standard weekly payout.
- `POST /api/payouts/emergency/request/`: Request an emergency payout (max 2/month).
- `GET /api/payouts/`: List payout history for the business.
- `GET /api/payouts/{uuid}/`: Retrieve specific payout details.

## 4. Payout Accounts (`/api/payouts/accounts/`)
- `POST /api/payouts/accounts/`: Create/add a business bank account.
- `GET /api/payouts/accounts/`: List business bank accounts.
- `POST /api/payouts/accounts/{uuid}/verify/`: Initiate verification of the bank account (Admin/System).
- `PATCH /api/payouts/accounts/{uuid}/`: Update bank account details.

## 5. Invoices (`/api/invoices/`)
- `GET /api/invoices/`: List customer invoices.
- `GET /api/invoices/{uuid}/`: Retrieve invoice metadata.
- `GET /api/invoices/{uuid}/pdf/`: Download the invoice as a PDF.

## 6. Settlements (`/api/settlements/`)
- `GET /api/settlements/`: List settlement statements for the business.
- `GET /api/settlements/{uuid}/`: Retrieve settlement statement metadata.
- `GET /api/settlements/{uuid}/pdf/`: Download the settlement statement as a PDF.

## Permissions
- **Customers**: Read-only access to their own billing, payments, and invoices. Can request refunds if policy allows.
- **Businesses**: Read-only access to their own earnings, balances, and settlement statements. Can request payouts and manage their payout accounts.
- **Admins**: Full access to finance dashboard, all transactions, manual adjustments, and manual verifications.
