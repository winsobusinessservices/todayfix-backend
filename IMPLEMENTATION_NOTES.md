# TodayFix business-role implementation

## New flow
1. Public registration always creates `CustomUser.role = USER`.
2. An authenticated USER submits `POST /api/business/upgrade/`.
3. The request is stored as `BusinessUpgradeRequest(PENDING)`.
4. An ADMIN/super-admin reviews the request.
5. Approval changes the user's role to `BUSINESS`, sets `has_business=True` and `business_verified=True`.
6. The BUSINESS user creates one or more `BusinessProfile` records and selects `INDIVIDUAL`, `COMPANY`, or `INVESTOR`.
7. COMPANY and INVESTOR profiles can manage multiple child profiles through `ManagedBusiness`.

## API endpoints

### User
- `POST /api/auth/register/user/`
- `POST /api/auth/login/`
- `POST /api/auth/logout/`
- `GET /api/auth/profile/`
- `POST /api/auth/profile/update/`

### Business upgrade
- `POST /api/business/upgrade/`
- `GET /api/business/upgrade/status/`
- `GET /api/business/profiles/`
- `POST /api/business/profiles/`
- `POST /api/business/management/`

### Admin
- `GET /api/business/admin/upgrades/`
- `POST /api/business/admin/upgrades/<id>/approve/`
- `POST /api/business/admin/upgrades/<id>/reject/`

The previous direct public business-registration endpoint is no longer routed. A visitor must register as USER first and then go through the upgrade/approval flow.

## Database
- `accounts_customuser`: authentication and top-level role.
- `business_businessupgraderequest`: approval workflow and review history.
- `business_businessprofile`: actual business entities and subtype.
- `business_managedbusiness`: parent/child business management relationship.

## Migration
Run in the project virtual environment:

```bash
python manage.py makemigrations
python manage.py migrate
python manage.py check
```

The uploaded environment contains a Windows virtualenv, so it is intentionally not included in this clean source archive.
