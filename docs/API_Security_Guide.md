# API Security Implementation Guide

**Date**: January 27, 2026  
**Status**: ✅ IMPLEMENTED

---

## Overview

The SPS Brain API is now secured with:
1. **CORS** - Only allows requests from trusted domains
2. **API Key Authentication** - Requires X-API-Key header for protected endpoints
3. **Cloudflare Access** - Additional layer for admin tools (automator.sukhi.in)

---

## 🔑 API Key Usage

### API Key Location

**Production**: Stored in `/root/sps-platform/.env` on server
```env
SPS_API_KEY=y71ztOnBIXsFjeLGDYQK1y7M_KiU9x5RRTL9fX-NNVs
```

**Local Development**: Stored in `.env` file (never commit!)

### How to Use the API Key

#### From Frontend (Astro/JavaScript)

```javascript
// Example: Call protected endpoint from website
const response = await fetch('https://api.sukhi.in/assess-risk', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': import.meta.env.PUBLIC_SPS_API_KEY  // Or hardcode in build
  },
  body: JSON.stringify({
    sector: 'retail',
    data: { /* risk data */ }
  })
});

const result = await response.json();
```

#### From n8n Workflows

In n8n HTTP Request node:
```
URL: https://api.sukhi.in/knowledge/ingest
Method: POST
Headers:
  - Name: X-API-Key
  - Value: {{$env.SPS_API_KEY}}
Body: { /* your data */ }
```

Make sure to add `SPS_API_KEY` to n8n environment variables.

#### From curl (Testing)

```bash
curl -X POST https://api.sukhi.in/assess-risk \
  -H "Content-Type: application/json" \
  -H "X-API-Key: y71ztOnBIXsFjeLGDYQK1y7M_KiU9x5RRTL9fX-NNVs" \
  -d '{"sector":"retail","data":{}}'
```

---

## 🔒 CORS Configuration

### Allowed Origins

Only these domains can call the API:
- `https://sukhi.in`
- `https://www.sukhi.in`
- `https://automator.sukhi.in`

Any other domain will receive a CORS error.

### Allowed Methods

- `GET`
- `POST`
- `OPTIONS` (preflight)

---

## 📡 Endpoint Security Matrix

| Endpoint | Auth Required | CORS Protected | Purpose |
|----------|---------------|----------------|---------|
| `GET /` | ❌ No | ✅ Yes | API info |
| `GET /health` | ❌ No | ✅ Yes | Health check |
| `POST /assess-risk` | ✅ Yes | ✅ Yes | Risk assessment |
| `POST /intelligence/mine` | ✅ Yes | ✅ Yes | News mining |
| `POST /mission/run` | ✅ Yes | ✅ Yes | CCO trigger |
| `GET /system/status` | ✅ Yes | ✅ Yes | System status |
| `POST /internal/broadcast` | ✅ Yes | ✅ Yes | WebSocket broadcast |
| `POST /knowledge/ingest` | ✅ Yes | ✅ Yes | RAG ingest |
| `POST /knowledge/query` | ✅ Yes | ✅ Yes | RAG query |
| `WS /ws` | ⚠️ Special | ✅ Yes | WebSocket (needs upgrade) |

---

## 🚨 Error Responses

### Missing API Key
```json
{
  "detail": "Invalid or missing API key. Include 'X-API-Key' header."
}
```
**Status**: `403 Forbidden`

### Wrong API Key
```json
{
  "detail": "Invalid or missing API key. Include 'X-API-Key' header."
}
```
**Status**: `403 Forbidden`

### CORS Violation
Browser console:
```
Access to fetch at 'https://api.sukhi.in/assess-risk' from origin 
'https://malicious-site.com' has been blocked by CORS policy
```

---

## 🔄 Rotating API Keys

### When to Rotate

- Every 3-6 months (proactive)
- Immediately if key is compromised
- After employee/contractor departure
- After security audit

### How to Rotate

1. **Generate new key**:
   ```bash
   python3 -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

2. **Update server .env**:
   ```bash
   ssh root@72.61.172.188
   cd /root/sps-platform
   nano .env
   # Change SPS_API_KEY value
   ```

3. **Restart API container**:
   ```bash
   docker compose -f docker-compose.prod.yml restart sps-brain
   ```

4. **Update frontend** (if hardcoded):
   - Update environment variable in website build
   - Redeploy website container

5. **Update n8n workflows**:
   - Go to automator.sukhi.in
   - Update environment variables
   - Save workflows

6. **Update local .env** (development):
   ```bash
   # On your Mac
   nano /Users/amar/Desktop/MyCode/new_SPS_Website/.env
   # Change SPS_API_KEY value
   ```

---

## 🛡️ Additional Security Layers

### Cloudflare WAF Rules (Optional)

Add these rules in Cloudflare Dashboard → Security → WAF:

**Rule 1: Rate Limiting**
```
Field: Hostname
Operator: equals
Value: api.sukhi.in

AND

Rate: > 100 requests per minute from same IP

Action: Challenge
```

**Rule 2: Geo-Blocking** (if only serving India)
```
Field: Hostname
Operator: equals
Value: api.sukhi.in

AND

Field: Country
Operator: does not equal
Value: IN (India)

Action: Block
```

### IP Allowlist (Most Restrictive - Optional)

If you want to lock down API to specific IPs:

```
Field: Hostname
Operator: equals
Value: api.sukhi.in

AND

Field: IP Address
Operator: not in list
Value: [Your office/home IP addresses]

Action: Block
```

---

## 🧪 Testing Security

### Test 1: No API Key
```bash
curl -X POST https://api.sukhi.in/assess-risk \
  -H "Content-Type: application/json" \
  -d '{"sector":"retail","data":{}}'

# Expected: 403 Forbidden
```

### Test 2: Wrong API Key
```bash
curl -X POST https://api.sukhi.in/assess-risk \
  -H "Content-Type: application/json" \
  -H "X-API-Key: wrong-key" \
  -d '{"sector":"retail","data":{}}'

# Expected: 403 Forbidden
```

### Test 3: Correct API Key
```bash
curl -X POST https://api.sukhi.in/assess-risk \
  -H "Content-Type: application/json" \
  -H "X-API-Key: y71ztOnBIXsFjeLGDYQK1y7M_KiU9x5RRTL9fX-NNVs" \
  -d '{"sector":"retail","data":{}}'

# Expected: 200 OK with risk assessment
```

### Test 4: Public Endpoints (No Auth)
```bash
curl https://api.sukhi.in/health

# Expected: 200 OK
# {"status":"operational","version":"2.0.0"}
```

---

## 📝 Frontend Integration

### Option 1: Environment Variable (Recommended)

**In Astro**:
```javascript
// .env file
PUBLIC_SPS_API_KEY=y71ztOnBIXsFjeLGDYQK1y7M_KiU9x5RRTL9fX-NNVs

// In component/page
const API_KEY = import.meta.env.PUBLIC_SPS_API_KEY;

fetch('https://api.sukhi.in/assess-risk', {
  headers: {
    'X-API-Key': API_KEY
  },
  // ... rest of request
});
```

### Option 2: Build-Time Injection

**In astro.config.mjs**:
```javascript
export default defineConfig({
  // ...
  vite: {
    define: {
      'import.meta.env.SPS_API_KEY': JSON.stringify(process.env.SPS_API_KEY)
    }
  }
});
```

### Option 3: Server-Side Only (Most Secure)

Create API routes in Astro that proxy to backend:

```javascript
// src/pages/api/risk.ts
export async function post({ request }) {
  const body = await request.json();
  
  const response = await fetch('https://api.sukhi.in/assess-risk', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': import.meta.env.SPS_API_KEY  // Server-side only!
    },
    body: JSON.stringify(body)
  });
  
  return response;
}
```

Then frontend calls: `/api/risk` (no key exposure!)

---

## 🔐 n8n Security

### Adding API Key to n8n

1. **Login to automator.sukhi.in**

2. **Settings → Environment Variables**:
   ```
   Name: SPS_API_KEY
   Value: y71ztOnBIXsFjeLGDYQK1y7M_KiU9x5RRTL9fX-NNVs
   ```

3. **Use in HTTP Request nodes**:
   ```
   Headers:
   - X-API-Key: {{$env.SPS_API_KEY}}
   ```

### Securing n8n with Cloudflare Access

See section below on Cloudflare Access configuration.

---

## ☁️ Cloudflare Access for n8n

### Step 1: Create Application

1. Go to: https://one.dash.cloudflare.com/
2. Navigate: **Access → Applications**
3. Click: **Add an application**
4. Select: **Self-hosted**

### Step 2: Configure Application

```
Application name: n8n Admin Dashboard
Session duration: 24 hours
Application domain: automator.sukhi.in
```

### Step 3: Create Access Policy

```
Policy name: Only Authorized Users
Action: Allow

Include:
- Emails: amar@example.com (your email)

OR

Include:
- IP ranges: 103.x.x.x (your office IP)
```

### Step 4: Test

1. Logout from n8n
2. Visit: https://automator.sukhi.in
3. Should see Cloudflare login screen
4. Verify with email → Get access

**Result**: Two-layer security (Cloudflare + n8n login)

---

## 📊 Monitoring

### API Usage Logs

```bash
# On server
docker compose -f docker-compose.prod.yml logs sps-brain | grep "403"

# Shows all blocked requests (no API key or wrong key)
```

### Cloudflare Analytics

1. Go to Cloudflare Dashboard
2. Select: sukhi.in
3. Navigate: **Analytics → Traffic**
4. Filter by: api.sukhi.in
5. Check for:
   - Unusual traffic spikes
   - 403 errors (blocked requests)
   - Geographic distribution

---

## 🆘 Troubleshooting

### "403 Forbidden" on Valid Requests

**Check**:
1. API key is correct in .env
2. Container restarted after .env change
3. Header name is exactly: `X-API-Key` (case-sensitive)
4. Value has no extra spaces

### CORS Errors

**Check**:
1. Request is from allowed origin (sukhi.in, www.sukhi.in, automator.sukhi.in)
2. Not using `http://` (must be `https://`)
3. Cloudflare proxy is enabled (orange cloud)

### Frontend Can't Connect

**Check**:
1. API key is exposed to frontend correctly
2. Environment variable is prefixed with `PUBLIC_` (Astro)
3. Build includes the API key
4. Browser DevTools → Network tab shows `X-API-Key` header

---

## ✅ Security Checklist

**Production Readiness**:

- [x] API key generated and stored in .env
- [x] CORS configured for allowed domains
- [x] All protected endpoints use `Depends(verify_api_key)`
- [x] docker-compose.prod.yml passes SPS_API_KEY to container
- [ ] Frontend sends X-API-Key header (needs implementation)
- [ ] n8n workflows updated with API key
- [ ] Cloudflare Access configured for automator.sukhi.in
- [ ] API key rotation schedule documented
- [ ] Monitoring and alerting configured

**Optional Enhancements**:

- [ ] Rate limiting via Cloudflare WAF
- [ ] Geo-blocking (if applicable)
- [ ] IP allowlist (for extra security)
- [ ] API key rotation automation
- [ ] Audit logging for all API calls

---

## 📚 References

- FastAPI Security: https://fastapi.tiangolo.com/tutorial/security/
- CORS Guide: https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS
- Cloudflare Access: https://developers.cloudflare.com/cloudflare-one/applications/
- API Key Best Practices: https://www.cloudflare.com/learning/security/api/api-key/

---

**Last Updated**: January 27, 2026  
**Version**: 1.0  
**Status**: Active
