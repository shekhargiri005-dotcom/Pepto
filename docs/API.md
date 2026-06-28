# =============================================================================
# Pepto API Documentation
# =============================================================================

## Base URL

| Environment | Base URL |
|-------------|----------|
| Development | `http://localhost:5000` |
| Staging     | `https://staging-api.pepto.app` |
| Production  | `https://api.pepto.app` |

All endpoints are prefixed with `/api/`.

---

## Authentication

Pepto uses **JWT Bearer tokens**. Include the token in every protected request:

```
Authorization: Bearer <your_jwt_access_token>
```

Tokens expire after **60 minutes**. Use the refresh endpoint to get a new one without re-logging in.

---

## Endpoint Reference

### 🔑 Auth

| Method | Path | Auth | Description | Request Body | Response |
|--------|------|------|-------------|--------------|----------|
| `POST` | `/api/auth/register` | ❌ | Register a new user | `{email, password, first_name, last_name, role}` | `{user, access_token, refresh_token}` |
| `POST` | `/api/auth/login` | ❌ | Login and get tokens | `{email, password}` | `{access_token, refresh_token, user}` |
| `POST` | `/api/auth/refresh` | ✅ Refresh token | Get a new access token | — | `{access_token}` |
| `POST` | `/api/auth/logout` | ✅ | Revoke refresh token | — | `{message}` |
| `POST` | `/api/auth/forgot-password` | ❌ | Send password reset email | `{email}` | `{message}` |
| `POST` | `/api/auth/reset-password` | ❌ | Reset password with token | `{token, new_password}` | `{message}` |
| `GET`  | `/api/auth/me` | ✅ | Get current user profile | — | `{user}` |

---

### 👤 Users

| Method | Path | Auth | Description | Request Body | Response |
|--------|------|------|-------------|--------------|----------|
| `GET`  | `/api/users/<id>` | ✅ | Get public user profile | — | `{user}` |
| `PUT`  | `/api/users/<id>` | ✅ Own user | Update profile | `{first_name, last_name, phone, avatar_url}` | `{user}` |
| `POST` | `/api/users/<id>/avatar` | ✅ Own user | Upload avatar (multipart) | `file` | `{avatar_url}` |
| `DELETE` | `/api/users/<id>` | ✅ Own/Admin | Delete account | — | `{message}` |

---

### 🐾 Pets

| Method | Path | Auth | Description | Request Body | Response |
|--------|------|------|-------------|--------------|----------|
| `GET`  | `/api/pets` | ✅ | List current user's pets | — | `{pets: [...]}` |
| `POST` | `/api/pets` | ✅ | Add a new pet | `{name, species, breed, age, weight, notes}` | `{pet}` |
| `GET`  | `/api/pets/<id>` | ✅ Own | Get pet details | — | `{pet}` |
| `PUT`  | `/api/pets/<id>` | ✅ Own | Update pet profile | `{name, breed, age, weight, notes}` | `{pet}` |
| `POST` | `/api/pets/<id>/photos` | ✅ Own | Upload pet photos (multipart) | `files[]` | `{photos: [...]}` |
| `DELETE` | `/api/pets/<id>` | ✅ Own | Delete pet | — | `{message}` |

---

### 🏪 Providers

| Method | Path | Auth | Description | Request Body | Response |
|--------|------|------|-------------|--------------|----------|
| `GET`  | `/api/providers` | ❌ | Search/list providers | `?service_type&lat&lng&radius&min_rating&page` | `{providers, pagination}` |
| `GET`  | `/api/providers/<id>` | ❌ | Get provider profile | — | `{provider, services, reviews}` |
| `POST` | `/api/providers` | ✅ | Create provider profile | `{business_name, bio, address, lat, lng, service_types}` | `{provider}` |
| `PUT`  | `/api/providers/<id>` | ✅ Own | Update provider profile | `{business_name, bio, address, ...}` | `{provider}` |
| `GET`  | `/api/providers/<id>/availability` | ❌ | Get available time slots | `?date_from&date_to` | `{slots: [...]}` |
| `POST` | `/api/providers/<id>/availability` | ✅ Own | Set availability schedule | `{schedule: [...]}` | `{schedule}` |

---

### 🛎️ Services

| Method | Path | Auth | Description | Request Body | Response |
|--------|------|------|-------------|--------------|----------|
| `GET`  | `/api/services` | ❌ | List all service categories | — | `{categories: [...]}` |
| `GET`  | `/api/providers/<id>/services` | ❌ | Get a provider's services | — | `{services: [...]}` |
| `POST` | `/api/providers/<id>/services` | ✅ Own | Add a service offering | `{name, description, price, duration_minutes, pet_types}` | `{service}` |
| `PUT`  | `/api/services/<id>` | ✅ Own | Update a service | `{name, description, price, duration_minutes}` | `{service}` |
| `DELETE` | `/api/services/<id>` | ✅ Own | Remove a service | — | `{message}` |

---

### 📅 Bookings

| Method | Path | Auth | Description | Request Body | Response |
|--------|------|------|-------------|--------------|----------|
| `GET`  | `/api/bookings` | ✅ | List user's bookings | `?status&page` | `{bookings, pagination}` |
| `POST` | `/api/bookings` | ✅ | Create a booking | `{provider_id, service_id, pet_id, scheduled_at, notes}` | `{booking, payment_intent_client_secret}` |
| `GET`  | `/api/bookings/<id>` | ✅ Own | Get booking details | — | `{booking}` |
| `PUT`  | `/api/bookings/<id>/confirm` | ✅ Provider | Confirm a booking | — | `{booking}` |
| `PUT`  | `/api/bookings/<id>/complete` | ✅ Provider | Mark booking complete | — | `{booking}` |
| `PUT`  | `/api/bookings/<id>/cancel` | ✅ Own | Cancel a booking | `{reason}` | `{booking, refund_amount}` |
| `GET`  | `/api/providers/<id>/bookings` | ✅ Own Provider | Provider's booking queue | `?status&date_from&date_to` | `{bookings, pagination}` |

---

### 💳 Payments

| Method | Path | Auth | Description | Request Body | Response |
|--------|------|------|-------------|--------------|----------|
| `POST` | `/api/payments/intent` | ✅ | Create Stripe PaymentIntent | `{booking_id}` | `{client_secret, amount, currency}` |
| `POST` | `/api/payments/confirm` | ✅ | Confirm payment capture | `{payment_intent_id}` | `{payment, booking}` |
| `GET`  | `/api/payments/<id>` | ✅ Own | Get payment details | — | `{payment}` |
| `POST` | `/api/payments/webhook` | ❌ Stripe | Stripe webhook handler | Raw Stripe event | `{received: true}` |
| `GET`  | `/api/providers/<id>/earnings` | ✅ Own Provider | Provider earnings summary | `?period=month` | `{total, pending, paid_out, transactions}` |

---

### ⭐ Reviews

| Method | Path | Auth | Description | Request Body | Response |
|--------|------|------|-------------|--------------|----------|
| `GET`  | `/api/providers/<id>/reviews` | ❌ | Get provider reviews | `?page&per_page&sort` | `{reviews, pagination, average_rating}` |
| `POST` | `/api/reviews` | ✅ | Submit a review | `{booking_id, rating, comment}` | `{review}` |
| `PUT`  | `/api/reviews/<id>` | ✅ Own | Edit own review (within 24h) | `{rating, comment}` | `{review}` |
| `DELETE` | `/api/reviews/<id>` | ✅ Own/Admin | Delete review | — | `{message}` |

---

### 💬 Messages

| Method | Path | Auth | Description | Request Body | Response |
|--------|------|------|-------------|--------------|----------|
| `GET`  | `/api/conversations` | ✅ | List user's conversations | — | `{conversations: [...]}` |
| `GET`  | `/api/conversations/<id>/messages` | ✅ Own | Get messages in thread | `?before_id&limit` | `{messages: [...]}` |
| `POST` | `/api/conversations/<id>/messages` | ✅ Own | Send a message | `{content, attachment_url?}` | `{message}` |
| `POST` | `/api/conversations` | ✅ | Start conversation | `{recipient_id, booking_id?, message}` | `{conversation, message}` |

---

### 🔔 Notifications

| Method | Path | Auth | Description | Request Body | Response |
|--------|------|------|-------------|--------------|----------|
| `GET`  | `/api/notifications` | ✅ | List notifications | `?unread_only&page` | `{notifications, unread_count}` |
| `PUT`  | `/api/notifications/<id>/read` | ✅ Own | Mark as read | — | `{notification}` |
| `PUT`  | `/api/notifications/read-all` | ✅ | Mark all as read | — | `{message}` |

---

### 🛡️ Admin (`/api/admin` — admin role required)

| Method | Path | Auth | Description | Response |
|--------|------|------|-------------|----------|
| `GET`  | `/api/admin/stats` | ✅ Admin | Platform stats dashboard | `{users, providers, bookings, revenue, reviews}` |
| `GET`  | `/api/admin/users` | ✅ Admin | Paginated user list | `{users, pagination}` |
| `PUT`  | `/api/admin/users/<id>/status` | ✅ Admin | Activate/deactivate user | `{message, user}` |
| `PUT`  | `/api/admin/providers/<id>/verify` | ✅ Admin | Verify provider business | `{message, provider}` |
| `GET`  | `/api/admin/bookings` | ✅ Admin | All bookings with filters | `{bookings, pagination}` |
| `DELETE` | `/api/admin/reviews/<id>` | ✅ Admin | Remove inappropriate review | `{message}` |

---

### ❤️ Health & Meta

| Method | Path | Auth | Description | Response |
|--------|------|------|-------------|----------|
| `GET`  | `/api/health` | ❌ | Service health check | `{status, db, redis, version}` |
| `GET`  | `/api/version` | ❌ | App version info | `{version, env, commit_sha}` |

---

## Error Response Format

All errors follow a consistent JSON structure:

```json
{
  "error": "error_code",
  "message": "Human-readable description of the error.",
  "details": {}
}
```

### HTTP Error Codes

| HTTP Status | Error Code | Description |
|-------------|------------|-------------|
| `400` | `bad_request` | Malformed request syntax |
| `401` | `unauthorized` | Missing or invalid JWT token |
| `403` | `forbidden` | Authenticated but insufficient permissions |
| `404` | `not_found` | Resource does not exist |
| `409` | `conflict` | Resource already exists or state conflict |
| `422` | `validation_error` | Request body failed validation |
| `429` | `rate_limited` | Too many requests — slow down |
| `500` | `internal_error` | Unexpected server error |
| `503` | `service_unavailable` | Database or downstream service unavailable |

---

## Pagination

All list endpoints return a `pagination` object:

```json
{
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 142,
    "pages": 8,
    "has_next": true,
    "has_prev": false
  }
}
```

---

## Example cURL Commands

### Register a new user
```bash
curl -X POST https://api.pepto.app/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "jane@example.com",
    "password": "SecurePass123!",
    "first_name": "Jane",
    "last_name": "Doe",
    "role": "user"
  }'
```

### Login
```bash
curl -X POST https://api.pepto.app/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "jane@example.com", "password": "SecurePass123!"}'
```

### Search for dog walkers near me
```bash
curl "https://api.pepto.app/api/providers?service_type=dog_walking&lat=12.9716&lng=77.5946&radius=10&min_rating=4.0&page=1" \
  -H "Authorization: Bearer $TOKEN"
```

### Create a booking
```bash
curl -X POST https://api.pepto.app/api/bookings \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "provider_id": 42,
    "service_id": 7,
    "pet_id": 3,
    "scheduled_at": "2026-07-15T10:00:00Z",
    "notes": "Max is shy at first but warms up quickly."
  }'
```

### Upload a pet photo
```bash
curl -X POST https://api.pepto.app/api/pets/3/photos \
  -H "Authorization: Bearer $TOKEN" \
  -F "files[]=@/path/to/buddy.jpg"
```

### Submit a review
```bash
curl -X POST https://api.pepto.app/api/reviews \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "booking_id": 101,
    "rating": 5,
    "comment": "Amazing service! My dog absolutely loved it."
  }'
```

### Admin — get platform stats
```bash
curl https://api.pepto.app/api/admin/stats \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```
