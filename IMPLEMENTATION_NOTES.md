# TodayFix — Backend API Requirements

## 1. Authentication & Account Management

Authentication should be based on a single user account. A user can initially register as a regular customer and later become an individual service provider or business owner.

### Authentication

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/auth/register` | Register a new user |
| POST | `/api/auth/login` | Login user |
| POST | `/api/auth/logout` | Logout user |
| POST | `/api/auth/refresh` | Generate a new access token |
| POST | `/api/auth/otp/generate` | Generate OTP |
| POST | `/api/auth/otp/verify` | Verify OTP |
| POST | `/api/auth/forgot-password` | Request password reset |
| POST | `/api/auth/reset-password` | Reset password |

### Registration

Required information may include:

- Name
- Email
- Phone
- Password
- OTP verification

After registration, the user should be created as a regular customer by default.

A user should **not need to create another account** to become a service provider/business owner later.

---

# 2. Users

### User APIs

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/users` | Get users — admin only |
| GET | `/api/users/{userId}` | Get user details |
| PUT/PATCH | `/api/users/{userId}` | Update user details |
| DELETE | `/api/users/{userId}` | Delete/deactivate user |
| GET | `/api/users/me` | Get currently authenticated user's profile |
| PATCH | `/api/users/me` | Update current user's profile |

### Recommendation

Use `/me` wherever possible.

For example:

`GET /api/users/me`

is preferable to:

`GET /api/users/{userId}`

when the user is requesting their own information.

The backend should derive the user ID from the authenticated JWT instead of trusting a user ID supplied by the frontend.

---

# 3. Addresses

A user can have multiple addresses.

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/users/me/addresses` | Get user's addresses |
| GET | `/api/users/me/addresses/{addressId}` | Get specific address |
| POST | `/api/users/me/addresses` | Add address |
| PATCH | `/api/users/me/addresses/{addressId}` | Update address |
| DELETE | `/api/users/me/addresses/{addressId}` | Delete address |

### Address information

Possible fields:

- Address line
- Area/locality
- City
- State
- Pincode
- Latitude
- Longitude
- Address type (`HOME`, `WORK`, `OTHER`)
- Default address

Latitude/longitude will become particularly useful for the **nearby provider broadcast system**.

---

# 4. Service Requests / Bookings

A customer requests a service and nearby eligible providers receive the request.

### Customer APIs

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/service-requests` | Get user's service requests |
| GET | `/api/service-requests/{requestId}` | Get specific request |
| POST | `/api/service-requests` | Create/request a service |
| DELETE | `/api/service-requests/{requestId}` | Cancel service request |

### Provider APIs

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/provider/service-requests` | Get requests available to provider |
| GET | `/api/provider/service-requests/{requestId}` | Get request details |
| POST | `/api/service-requests/{requestId}/accept` | Accept request |
| POST | `/api/service-requests/{requestId}/reject` | Reject request |

### Request lifecycle

The backend should maintain a request status such as:

```text
CREATED
   ↓
BROADCASTING
   ↓
ACCEPTED
   ↓
PROVIDER_ASSIGNED
   ↓
IN_PROGRESS
   ↓
COMPLETED
```

Possible alternative states:

```text
CANCELLED
EXPIRED
REJECTED
```

This is important because a service request is not simply something that gets created and deleted.

---

# 5. Services

Services are the actual services offered through TodayFix.

Examples:

- Plumbing
- Electrical repair
- AC repair
- Cleaning
- Painting

### APIs

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/services` | Get all available services |
| GET | `/api/services/{serviceId}` | Get service details |
| POST | `/api/services` | Create service |
| PATCH | `/api/services/{serviceId}` | Update service |
| DELETE | `/api/services/{serviceId}` | Delete service |
| PATCH | `/api/services/{serviceId}/availability` | Enable/disable service |

### Important distinction

There are two different concepts:

**Service**

> "AC Repair"

**Service Offering**

> "ABC AC Services provides AC Repair for ₹499"

Eventually you may want to model these separately.

For example:

```text
Category
   └── Service
          └── Provider Service Offering
```

This will make pricing and provider-specific services much easier to manage.

---

# 6. Vendors / Businesses

A provider should be able to create either:

### Individual Provider

Example:

```text
Rahul
Individual Electrician
```

### Registered Business

Example:

```text
ABC Home Services Pvt Ltd
```

### APIs

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/vendors` | Get providers/businesses |
| GET | `/api/vendors/{vendorId}` | Get provider/business details |
| POST | `/api/vendors` | Create provider/business profile |
| PATCH | `/api/vendors/{vendorId}` | Update provider/business |
| DELETE | `/api/vendors/{vendorId}` | Delete/deactivate provider/business |

### Vendor Search & Filtering

`GET /api/vendors` should support query parameters for filtering, nearby search, text search, and featured providers.

#### Filter by city

```text
GET /api/vendors?cityId=123
```

#### Filter by service

```text
GET /api/vendors?serviceId=456
```

#### Nearby provider search

```text
GET /api/vendors?lat=12.9716&lng=77.5946&radius=10
```

- `lat` — latitude
- `lng` — longitude
- `radius` — search radius, preferably in kilometers

This will be important for TodayFix's nearby provider discovery and broadcast system.

#### Text search

```text
GET /api/vendors?q=plumbing
```

The `q` parameter can be used to search provider/business names, services, descriptions, etc.

#### Featured providers

```text
GET /api/vendors?isFeatured=true
```

This can be used by the `FeaturedSection` component on the frontend.

### Parameters can be combined

For example:

```text
GET /api/vendors?cityId=123&serviceId=456&lat=12.9716&lng=77.5946&radius=10&q=plumbing&isFeatured=true
```

The backend should treat these as optional filters rather than creating separate endpoints for every combination.

---

# 7. Provider Portfolio

Providers/businesses should be able to upload images showcasing their previous work.

### APIs

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/vendors/me/portfolio` | Upload portfolio image |
| DELETE | `/api/vendors/me/portfolio/{imageId}` | Remove portfolio image |

### Portfolio image information

A portfolio item can contain:

```text
imageId
imageUrl
vendorId
createdAt
```

The actual image file should preferably be stored in object storage rather than directly inside the application database.

Examples:

- AWS S3
- Cloudinary
- Cloudflare R2
- Similar object storage

The database should generally store the image metadata and URL/reference.

---

# 8. Provider Verification

I recommend adding a dedicated verification module.

### APIs

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/vendors/{vendorId}/verification` | Submit verification |
| GET | `/api/vendors/{vendorId}/verification` | Get verification status |
| PATCH | `/api/admin/vendors/{vendorId}/verification` | Approve/reject verification |

### Individual verification

Potential information:

- PAN
- Identity information
- Address
- Supporting documents
- Bank/payout information

### Business verification

Potential information:

- GSTIN
- Business PAN
- Business name
- Registered address
- Business documents
- Authorized person's details
- Bank/payout information

The exact verification requirements should be finalized based on the legal/payment requirements applicable to TodayFix.

### Verification status

```text
PENDING
UNDER_REVIEW
VERIFIED
REJECTED
```

Do not simply consider the existence of a PAN/GST number as verification.

---

# 9. Provider Services

A provider needs to specify which services they offer.

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/vendors/{vendorId}/services` | Get services offered by provider |
| POST | `/api/vendors/{vendorId}/services` | Add service offering |
| PATCH | `/api/vendors/{vendorId}/services/{serviceId}` | Update offering |
| DELETE | `/api/vendors/{vendorId}/services/{serviceId}` | Remove offering |

Example:

```text
ABC Services
   │
   ├── AC Repair        ₹499
   ├── AC Installation  ₹999
   └── AC Maintenance   ₹699
```

---

# 10. Provider Availability

Since TodayFix will broadcast service requests to nearby providers, provider availability should be tracked.

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/providers/me/availability` | Get provider availability |
| PATCH | `/api/providers/me/availability` | Toggle available/unavailable |
| PATCH | `/api/providers/me/location` | Update provider location |

Example statuses:

```text
AVAILABLE
UNAVAILABLE
BUSY
```

This helps the broadcast system determine which providers should receive a request.

---

# 11. Provider Earnings

Providers need access to their financial summary.

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/providers/me/earnings` | Get earnings summary including completed jobs, pending payouts, and total revenue |

The response can contain information such as:

```text
totalRevenue
pendingPayouts
completedJobs
paidAmount
currentPeriodRevenue
```

The exact financial fields can be expanded later based on the payment system.

---

# 12. Provider Payouts

Providers should be able to view their payout history.

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/providers/me/payouts` | Get history of money transferred to provider's bank account |

Possible payout information:

```text
payoutId
amount
status
bankAccount
transactionReference
processedAt
createdAt
```

Possible payout statuses:

```text
PENDING
PROCESSING
COMPLETED
FAILED
```

---

# 13. Reviews

Reviews should be associated with a completed service/request rather than allowing arbitrary reviews.

### APIs

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/reviews/my` | Get reviews given by current user |
| GET | `/api/vendors/{vendorId}/reviews` | Get reviews for provider/business |
| POST | `/api/vendors/{vendorId}/reviews` | Add review |
| DELETE | `/api/reviews/{reviewId}` | Delete review |

### Review

Possible fields:

```text
reviewId
rating
comment
userId
vendorId
serviceRequestId
createdAt
updatedAt
```

The backend should verify that:

1. The user actually used the service.
2. The service request is completed.
3. The user has not already reviewed that request.

---

# 14. Chat

Chat should be associated with a service request.

```text
Customer
    │
    │
    ▼
Service Request
    │
    └──── Chat ──── Provider
```

### APIs

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/chats` | Get user's conversations |
| GET | `/api/chats/{chatId}/messages` | Get chat messages |
| POST | `/api/chats/{chatId}/messages` | Send message |

For real-time communication, use:

```text
WebSocket
```

rather than regular REST requests for sending/receiving messages.

REST can still be used for retrieving chat history.

Possible WebSocket destination:

```text
/ws/chat/{chatId}
```

---

# 15. Notifications

Important events should generate notifications.

Examples:

- New service request
- Request accepted
- Provider assigned
- Provider arriving
- Service completed
- New message
- Review received
- Verification approved/rejected
- Subscription expiring
- Payout completed/failed

### APIs

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/notifications` | Get notifications |
| PATCH | `/api/notifications/{id}/read` | Mark notification as read |
| PATCH | `/api/notifications/read-all` | Mark all as read |

Real-time notifications can later use WebSockets/push notifications.

---

# 16. Cities

Cities should be admin-managed.

| Method | Endpoint | Access |
|---|---|---|
| GET | `/api/cities` | Public |
| GET | `/api/cities/{cityId}` | Public |
| POST | `/api/admin/cities` | Admin |
| PATCH | `/api/admin/cities/{cityId}` | Admin |
| DELETE | `/api/admin/cities/{cityId}` | Admin |

---

# 17. Categories

Categories should also be admin-managed.

| Method | Endpoint | Access |
|---|---|---|
| GET | `/api/categories` | Public |
| GET | `/api/categories/{categoryId}` | Public |
| POST | `/api/admin/categories` | Admin |
| PATCH | `/api/admin/categories/{categoryId}` | Admin |
| DELETE | `/api/admin/categories/{categoryId}` | Admin |

Example:

```text
Home Services
 ├── Plumbing
 ├── Electrical
 ├── AC Repair
 └── Cleaning
```

---

# 18. Subscriptions

TodayFix can have different provider subscription plans.

Example:

```text
FREE
PRO
ENTERPRISE
```

### APIs

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/subscriptions/plans` | Get available plans |
| GET | `/api/subscriptions/me` | Get current subscription |
| POST | `/api/subscriptions` | Subscribe to a plan |
| PATCH | `/api/subscriptions/{subscriptionId}` | Change subscription |
| DELETE | `/api/subscriptions/{subscriptionId}` | Cancel subscription |

If payment integration is added later:

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/payments/create-order` | Create payment order |
| POST | `/api/payments/verify` | Verify payment |
| POST | `/api/payments/webhook` | Receive payment provider webhook |
| GET | `/api/payments/{paymentId}` | Get payment details |

The payment webhook is especially important because the backend should not trust only the frontend's payment-success response.

---

# 19. Admin APIs

The admin will eventually need more than Cities and Categories.

Potential admin modules:

```text
Users
Providers
Businesses
Provider Verification
Services
Categories
Cities
Service Requests
Reviews
Subscriptions
Payments
Reports
```

Example:

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/admin/users` | Get/manage users |
| GET | `/api/admin/vendors` | Get/manage providers |
| GET | `/api/admin/service-requests` | Get/manage service requests |
| GET | `/api/admin/reviews` | Get/manage reviews |
| GET | `/api/admin/verifications` | Get pending verifications |
| PATCH | `/api/admin/verifications/{id}` | Approve/reject verification |

---

# 20. Recommended High-Level API Structure

```text
/api
│
├── /auth
│   ├── register
│   ├── login
│   ├── logout
│   ├── refresh
│   ├── otp
│   ├── forgot-password
│   └── reset-password
│
├── /users
│
├── /addresses
│
├── /services
│
├── /service-requests
│
├── /vendors
│   ├── portfolio
│   ├── verification
│   └── services
│
├── /providers
│   ├── availability
│   ├── location
│   ├── earnings
│   └── payouts
│
├── /reviews
│
├── /chats
│
├── /notifications
│
├── /cities
│
├── /categories
│
├── /subscriptions
│
├── /payments
│
└── /admin
    ├── users
    ├── vendors
    ├── verifications
    ├── services
    ├── categories
    ├── cities
    ├── requests
    ├── reviews
    └── subscriptions
```

# 21. Most Important Backend Relationships

The backend developer should think about the domain roughly like this:

```text
User
 │
 ├──────── Addresses
 │
 ├──────── Service Requests
 │               │
 │               ├──── Service
 │               │
 │               ├──── Address
 │               │
 │               ├──── Provider
 │               │
 │               ├──── Chat
 │               │
 │               └──── Review
 │
 └──────── Provider/Vendor
                  │
                  ├──── Verification
                  │
                  ├──── Services
                  │
                  ├──── Portfolio
                  │
                  ├──── Availability
                  │
                  ├──── Location
                  │
                  ├──── Earnings
                  │
                  ├──── Payouts
                  │
                  ├──── Subscription
                  │
                  └──── Reviews
```

# 22. Key Backend Rules

The following business rules should be implemented on the backend rather than relying on the frontend.

### Authentication

- Protected APIs require authentication.
- User identity should come from JWT.
- Users should not be able to access another user's private data.
- Passwords must be hashed.
- Refresh tokens should be handled securely.

### Provider

- Only verified providers should be allowed to receive service requests.
- Provider availability should determine whether they receive broadcasts.
- A provider should only manage their own services/business profile.
- Only the provider/business owner should be able to upload/delete their portfolio images.
- Earnings and payout information must only be accessible to the authenticated provider.

### Vendor Search

`GET /api/vendors` should support optional query parameters:

```text
cityId
serviceId
lat
lng
radius
q
isFeatured
```

Example:

```text
GET /api/vendors?cityId=123&serviceId=456
```

Nearby search:

```text
GET /api/vendors?lat=12.9716&lng=77.5946&radius=10
```

Text search:

```text
GET /api/vendors?q=plumbing
```

Featured providers:

```text
GET /api/vendors?isFeatured=true
```

The backend should support combining these filters when required.

### Service Requests

- A customer can only cancel requests that are cancellable.
- Only eligible providers can accept requests.
- Once a request is accepted, other providers should no longer be able to accept it.
- Request state transitions should be validated by the backend.
- Only providers matching the required service and availability/location criteria should receive broadcasts.

### Reviews

- Only customers who completed the corresponding service can review.
- One review per completed service request.
- Users cannot review themselves.

### Portfolio

- Only the owner of a vendor profile can upload/remove portfolio images.
- Image files should preferably be stored in object storage.
- Database should store image metadata and storage URL/reference.
- File type and size should be validated by the backend.

### Payments & Payouts

- Payment status must be verified server-side.
- Payment provider webhooks should be treated as the source of truth for payment events.
- Providers should not be able to modify their own earnings or payout records.
- Payout records should be immutable financial records.
- Earnings should be calculated from completed/eligible jobs according to the platform's payout rules.

### Admin

Admin APIs must be protected using role-based authorization.

Example roles:

```text
CUSTOMER
PROVIDER
BUSINESS_OWNER
ADMIN
```

A user can potentially have more than one capability/role over time.

# 23. Suggested MVP API Priority

Don't implement everything simultaneously.

### Phase 1 — Core

```text
Auth
Users
Addresses
Cities
Categories
Services
Vendors
Service Requests
```

### Phase 2 — Marketplace

```text
Provider Verification
Provider Services
Provider Availability
Provider Location
Provider Portfolio
Broadcasting
Accept/Reject Request
Notifications
```

### Phase 3 — Engagement

```text
Reviews
Chat
```

### Phase 4 — Monetization

```text
Subscriptions
Payments
Earnings
Payouts
```

### Phase 5 — Admin & Analytics

```text
Admin Dashboard
Reports
Provider Analytics
Revenue Analytics
Service Analytics
```

# 24. Important Domain Distinction

The backend should maintain a clear distinction between:

```text
Category
    ↓
Service
    ↓
Provider Service Offering
    ↓
Service Request
    ↓
Completed Job
    ↓
Review
    ↓
Provider Earnings
    ↓
Provider Payout
```

For example:

```text
Category:
Home Maintenance

        ↓

Service:
AC Repair

        ↓

Provider Offering:
ABC AC Services
₹499

        ↓

Service Request:
Customer requests AC Repair

        ↓

Completed Job:
ABC AC Services completes the job

        ↓

Review:
Customer gives 5 stars

        ↓

Earnings:
₹499 revenue
- Platform commission
= Provider earnings

        ↓

Payout:
Amount transferred to provider bank account
```

This separation will make the TodayFix backend significantly easier to extend when you add the **nearby broadcast system, provider subscriptions, commissions, payments, earnings, and payouts**.