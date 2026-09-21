# Finance Architecture

This document describes the additive and modular finance architecture for the TodayFix backend. It ensures the existing modules (`bookings`, `instant_bookings`, `fix_coins`, etc.) remain intact while providing a robust, production-grade financial ledger and payment system.

## 1. Django Apps

The finance system will be split into the following highly cohesive applications:

- **billing**: Single source of truth for pricing calculations, platform fees, taxes, and final payable amounts.
- **payments**: Handles interactions with the Razorpay payment gateway, webhooks, and payment attempts.
- **finance**: The core ledger and financial accounts for the platform, customers, and businesses.
- **payouts**: Manages business payouts, bank accounts, and withdrawal logic (weekly & emergency).
- **invoices**: Generates immutable PDF invoices for customers and settlement statements for businesses.
- **reconciliation**: Background tasks to compare database records with provider (Razorpay) reports.

## 2. Models per App

### `billing`
- **BillingRecord**: Links to either a `Booking` or `InstantBooking` (XOR). Stores snapshots of subtotal, tax, fees, fix_coin discount, and final payable amounts.
- **BillingItem**: Extensible line items (e.g., SERVICE, MATERIAL, TRAVEL, TIP, PLATFORM_FEE, BOOKING_FEE, TAX).
- **PlatformFeeRule**: Configurable rule engine for platform fees based on amount slabs.
- **BookingFeeRule**: Configurable rule engine for booking fees.

### `payments`
- **PaymentOrder**: Represents the intent to pay for a `BillingRecord`. Stores `razorpay_order_id`.
- **PaymentTransaction**: Represents individual payment attempts (captured, failed). Stores `razorpay_payment_id` and signatures.

### `finance`
- **FinanceAccount**: Tracks balances (pending, available, lifetime earned) for businesses.
- **LedgerEntry**: Immutable double-entry ledger for all money movements (customer payment, platform fee deduction, business earning, refund).

### `payouts`
- **PayoutAccount**: Securely stores verified bank account details (account number, IFSC).
- **Payout**: Represents a withdrawal request (WEEKLY, EMERGENCY) and its state.

### `invoices`
- **Invoice**: Immutable snapshot representing a customer invoice.
- **InvoiceItem**: Line items for the invoice.
- **SettlementStatement**: Represents a payout settlement document for businesses.

### `reconciliation`
- **ReconciliationRecord**: Logs discrepancies found between the DB and Razorpay for manual review.

## 3. Key Relationships and Constraints
- **Currency**: Enforced as `INR` via constants.
- **Decimals**: `DecimalField` is used universally; no Python floats.
- **XOR Constraint**: A `BillingRecord` must point to exactly one of `Booking` OR `InstantBooking`.
- **Row Locking**: `select_for_update()` must be used during payment captures, coin redemptions, and payouts to prevent concurrency issues.
- **Idempotency**: Webhooks and payment creations use idempotency keys or unique constraint checks to prevent double processing.

## 4. Flow

1. **Booking** -> **Billing**: A booking is made, triggering the Billing Calculator to generate a `BillingRecord`.
2. **Billing** -> **Payment**: The user proceeds to pay, generating a `PaymentOrder` and `Razorpay Order`.
3. **Payment** -> **Ledger**: On successful webhook capture, the `PaymentTransaction` is logged, and `LedgerEntry` records are created.
4. **Ledger** -> **Payout**: `PENDING` funds move to `AVAILABLE` after service completion. Payout rules (e.g., 70% max) govern withdrawals.
5. **Billing** -> **Invoice**: On finalization, a PDF `Invoice` is generated.
