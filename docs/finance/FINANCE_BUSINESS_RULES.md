# Finance Business Rules

This document outlines the core business and financial rules driving the TodayFix backend finance system.

## 1. Platform Fee Rules
Platform fees are calculated based on the base service amount (Service + Extended Service + Materials + Travel). Tips are excluded by default.
Slabs:
- ₹0–₹499 → 2%
- ₹500–₹999 → 3%
- ₹1000–₹1999 → 4%
- ₹2000+ → 5%

## 2. Booking Fee Rules
Services with a payment-related amount greater than ₹500 incur a booking charge.
- *Ambiguity Note*: The exact flat fee or percentage is not explicitly defined in existing models. A configurable rule structure will be implemented with a safe placeholder default (e.g., ₹0 or a predefined flat amount).

## 3. Tip Rules
- 100% of the tip belongs to the business/provider.
- Platform fee on tip = 0%.

## 4. FixCoin Rules (Preserved from Existing System)
- 500 coins awarded on signup.
- 500 coins = ₹50 (Conversion: 10 coins = ₹1).
- Maximum redemption is 15% of the *eligible bill amount* (Service + Extended Service + Materials + Travel + Booking Fee + Platform Fee + Tax). Tip is excluded.
- Reward: 10 coins per ₹100 spent. Granted *only* after service completion and payment capture.

## 5. Business Payout Rules
- **Maximum Weekly Payout**: 70% of the *eligible available earnings* (not gross customer payment).
- **Emergency Payouts**: Maximum 2 times per *calendar month* (not rolling 30 days).
- Funds start as `PENDING` when the customer pays and move to `AVAILABLE` only after service completion and eligibility conditions are satisfied.

## 6. Refund Rules
- Refunds can be FULL or PARTIAL.
- Total refunded amount can never exceed the captured amount.
- **FixCoin Reversal**: If an order used FixCoins, refunds will reverse the coins proportionally or via a configurable policy.
- **Refund after Payout**: If a refund occurs after a business has withdrawn funds, the business's available balance may become negative or marked as a `recoverable_amount` for future deduction.

## 7. Ambiguities & Unresolved Rules for Product Review
1. **GST Percentage**: The exact GST rate (e.g., 18%) is not strictly defined for all services. Will implement as a configurable parameter on the Billing/Platform rule.
2. **Cancellation Fee**: The rules around fees when a booking is cancelled by a user vs. provider need explicit definition.
3. **Refund FixCoin Policy**: Whether a partial refund refunds cash first or FixCoins first. Default assumption: Pro-rata or cash first.
4. **Booking Fee Amount**: Exact booking fee value for amounts > ₹500.

These rules will be driven by database configurations (e.g., `PlatformFeeRule`, `BookingFeeRule`) rather than hardcoded constants to allow future flexibility.
