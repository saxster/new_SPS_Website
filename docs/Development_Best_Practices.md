# Development Best Practices for SPS Platform

**Date**: January 27, 2026  
**Status**: Active Reference Guide

---

## Table of Contents

1. [Astro Development Gotchas](#astro-development-gotchas)
2. [Internal vs External Architecture](#internal-vs-external-architecture)
3. [Docker Network Communication](#docker-network-communication)
4. [Code Organization](#code-organization)
5. [Testing Best Practices](#testing-best-practices)
6. [Performance Optimization](#performance-optimization)

---

## Astro Development Gotchas

### Rule 1: Async/Await in Frontmatter Only

Astro components have TWO sections:
1. **Frontmatter** (between `---` markers) - async-friendly
2. **JSX/Template** - NOT async-friendly

**❌ WRONG - Will cause build failure:**

```astro
---
import { getCollection } from 'astro:content';
---

<div>
  {
    (() => {
      // This IIFE is NOT async, so await fails
      const data = await getCollection('items');  // ❌ ERROR!
      return data.map(item => <div>{item.title}</div>);
    })()
  }
</div>
```

**Error Message:**
```
"await" can only be used inside an "async" function
Location: /app/src/pages/index.astro:64:31
Build failed in 1.41s
```

**✅ CORRECT - Move async operations to frontmatter:**

```astro
---
import { getCollection } from 'astro:content';

// Async operations here - ALWAYS works
const items = await getCollection('items');
const sortedItems = items.sort((a, b) => a.order - b.order);
---

<div>
  {
    sortedItems.map(item => (
      <div>{item.title}</div>
    ))
  }
</div>
```

**Why This Matters:**
- Frontmatter executes at build time (server-side)
- JSX expressions execute in the template
- Astro doesn't allow async JSX expressions
- Always resolve async data BEFORE using in JSX

### Rule 2: Sort/Filter Before JSX

**❌ WRONG - Complex logic in JSX:**

```astro
<div>
  {
    items
      .filter(item => item.active)
      .sort((a, b) => {
        // Complex sorting logic with await
        const scoreA = await calculateScore(a);  // ❌ Can't await!
        return scoreA - scoreB;
      })
      .map(item => <Card {...item} />)
  }
</div>
```

**✅ CORRECT - Pre-process in frontmatter:**

```astro
---
const items = await getCollection('items');

// All filtering, sorting, async operations here
const activeItems = items.filter(item => item.active);
const scoredItems = await Promise.all(
  activeItems.map(async item => ({
    ...item,
    score: await calculateScore(item)
  }))
);
const sortedItems = scoredItems.sort((a, b) => b.score - a.score);
---

<div>
  {sortedItems.map(item => <Card {...item} />)}
</div>
```

### Rule 3: API Calls in Server Routes

**❌ WRONG - Calling external APIs in component:**

```astro
---
// This runs at build time once, not per request!
const response = await fetch('https://api.example.com/data');
const data = await response.json();
---

<div>{data.value}</div>  <!-- Stale data! -->
```

**✅ CORRECT - Use API routes for dynamic data:**

```javascript
// src/pages/api/data.js
export async function get() {
  const response = await fetch('https://api.example.com/data');
  const data = await response.json();
  return new Response(JSON.stringify(data), {
    headers: { 'Content-Type': 'application/json' }
  });
}
```

```astro
---
// Component just references the endpoint
---

<div id="data-container"></div>

<script>
  // Client-side fetch from your API route
  fetch('/api/data')
    .then(r => r.json())
    .then(data => {
      document.getElementById('data-container').textContent = data.value;
    });
</script>
```

### Rule 4: Environment Variables

**Client-side (PUBLIC_ prefix)**:
```javascript
// Accessible in browser - use for non-sensitive config
const apiUrl = import.meta.env.PUBLIC_API_URL;
```

**Server-side (no prefix)**:
```javascript
// Only accessible at build/server time - use for secrets
const apiKey = import.meta.env.API_KEY;
```

**Never expose secrets to client**:
```javascript
// ❌ WRONG - API key exposed in browser!
<script>
  const key = import.meta.env.API_KEY;  // Doesn't work anyway
</script>

// ✅ CORRECT - Keep on server
// src/pages/api/proxy.js
export async function post({ request }) {
  const apiKey = import.meta.env.API_KEY;  // Server-only
  const response = await fetch('...', {
    headers: { 'X-API-Key': apiKey }
  });
  return response;
}
```

---

## Internal vs External Architecture

### Two Communication Patterns

Your SPS Platform has TWO distinct ways services communicate:

#### Pattern 1: Internal Communication (Docker Network)

```
┌─────────────┐         ┌───────────┐
│ sps-website │────────>│ sps-brain │
│   :4321     │ Docker  │   :8000   │
└─────────────┘ Network └───────────┘
       │
       │ filesystem
       ↓
   ┌────────┐
   │  n8n   │
   │ :5678  │
   └────────┘
```

**Characteristics:**
- ✅ Direct Docker network communication
- ✅ Uses container names (e.g., `sps-brain:8000`)
- ✅ No API key required
- ✅ No Cloudflare tunnel involved
- ✅ Fast, local communication
- ✅ Never hits public domain

**Example - Website Server-Side:**
```javascript
// website/src/pages/api/assess-risk.ts
export async function post({ request }) {
  const body = await request.json();
  
  // Calls INTERNAL Docker address - no API key needed!
  const response = await fetch('http://sps-brain:8000/assess-risk', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    // Note: NO X-API-Key header!
    body: JSON.stringify(body)
  });
  
  return response;
}
```

**Example - n8n Workflow:**
```json
{
  "nodes": [
    {
      "type": "n8n-nodes-base.executeCommand",
      "parameters": {
        "command": "python3 /app/agent_backend/scripts/analyze.py"
      }
    }
  ]
}
```
No HTTP call, no API key - direct filesystem access.

#### Pattern 2: External Communication (Public API)

```
Internet
    ↓
Cloudflare CDN
    ↓
Cloudflare Tunnel (Encrypted)
    ↓
┌──────────────┐
│  cloudflared │
└──────────────┘
    ↓
┌───────────┐
│ sps-brain │
│   :8000   │
└───────────┘
```

**Characteristics:**
- ⚠️ Goes through Cloudflare tunnel
- ⚠️ Uses public domain (api.sukhi.in)
- ⚠️ Requires X-API-Key header
- ⚠️ Subject to CORS restrictions
- ⚠️ Subject to rate limiting
- ⚠️ Adds latency (Cloudflare routing)

**Example - External Client:**
```bash
curl -X POST https://api.sukhi.in/assess-risk \
  -H "Content-Type: application/json" \
  -H "X-API-Key: y71ztOnBIXsFjeLGDYQK1y7M_KiU9x5RRTL9fX-NNVs" \
  -d '{"sector":"retail","data":{}}'
```

**Example - Client-Side JavaScript:**
```javascript
// This runs in the browser, so uses public API
fetch('https://api.sukhi.in/assess-risk', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': 'y71ztOnBIXsFjeLGDYQK1y7M_KiU9x5RRTL9fX-NNVs'
  },
  body: JSON.stringify({ sector: 'retail', data: {} })
});
```

### Decision Tree: Which Pattern to Use?

```
Where is the code running?
├─ Website server-side (Astro API routes)?
│  └─> Use INTERNAL: http://sps-brain:8000
│      No API key needed
│
├─ n8n workflow?
│  └─> Use FILESYSTEM: Direct Python execution
│      No API key needed
│
├─ Website client-side (browser JavaScript)?
│  └─> Use EXTERNAL: https://api.sukhi.in
│      Requires API key (but expose via server proxy!)
│
└─ External service/mobile app?
   └─> Use EXTERNAL: https://api.sukhi.in
       Requires API key
```

### Common Mistake: Using Wrong Pattern

**❌ WRONG - Website using external API:**
```javascript
// src/pages/api/assess-risk.ts
export async function post({ request }) {
  // This goes through Cloudflare tunnel unnecessarily!
  const response = await fetch('https://api.sukhi.in/assess-risk', {
    headers: { 'X-API-Key': process.env.API_KEY }  // Extra work!
  });
  return response;
}
```

**✅ CORRECT - Website using internal Docker network:**
```javascript
// src/pages/api/assess-risk.ts
export async function post({ request }) {
  // Direct Docker network call - fast and secure!
  const response = await fetch('http://sps-brain:8000/assess-risk', {
    headers: { 'Content-Type': 'application/json' }
    // No API key needed!
  });
  return response;
}
```

### Why This Architecture?

**Benefits of Internal Communication:**
1. **Performance**: No extra hops through Cloudflare
2. **Security**: API key not needed for trusted internal services
3. **Simplicity**: No authentication management
4. **Reliability**: No external network dependencies

**Benefits of External API:**
1. **Access Control**: API key required from untrusted sources
2. **Rate Limiting**: Cloudflare can throttle abuse
3. **DDoS Protection**: Cloudflare filters malicious traffic
4. **Monitoring**: See external usage in Cloudflare analytics

### Verifying Your Setup

**Check website uses internal addresses:**
```bash
cd /Users/amar/Desktop/MyCode/new_SPS_Website
grep -r "http://sps-brain" website/src/pages/api/

# Expected: Shows internal Docker network calls
# If empty or shows "https://api.sukhi.in" → WRONG! Update to internal
```

**Check n8n uses filesystem:**
```bash
grep -r "executeCommand" n8n_*.json

# Expected: Shows Python script executions
# If shows HTTP calls to api.sukhi.in → Consider switching to filesystem
```

**Test internal communication:**
```bash
# On server, inside website container
docker exec -it sps-website sh
apk add curl  # Install curl in alpine container
curl http://sps-brain:8000/health

# Expected: {"status":"healthy"}
# If fails: Check Docker network connectivity
```

---

## Docker Network Communication

### Docker Network Basics

All SPS Platform services run on a shared Docker network called `sps-network`:

```yaml
# docker-compose.prod.yml
networks:
  sps-network:
    driver: bridge
```

**Services on this network:**
- `sps-website` (website:4321)
- `sps-brain` (sps-brain:8000)
- `n8n` (n8n:5678)
- `sps-chroma` (sps-chroma:8000)
- `cloudflared` (cloudflared)

### Service Discovery

Docker provides **automatic DNS resolution** for container names:

```javascript
// Inside sps-website container, this works:
fetch('http://sps-brain:8000/health')
fetch('http://n8n:5678/health')
fetch('http://sps-chroma:8000/api/v1/heartbeat')

// Container name = hostname
```

### Network Isolation

Services on `sps-network` can talk to each other, but NOT to:
- Host machine ports (unless explicitly exposed)
- Other Docker networks
- Internet (unless outbound allowed)

**This is SECURITY by design:**
```
Internet → Can only access via Cloudflare tunnel
         → Cannot directly reach containers
         
Containers → Can talk to each other
           → Can access internet
           → Cannot be reached directly from internet
```

### Debugging Network Issues

**Test connectivity between containers:**
```bash
# From host, exec into website container
docker exec -it sps-website sh

# Test sps-brain
wget -O- http://sps-brain:8000/health

# Test chroma
wget -O- http://sps-chroma:8000/api/v1/heartbeat

# Test n8n
wget -O- http://n8n:5678/healthz
```

**Check network configuration:**
```bash
# List networks
docker network ls

# Inspect sps-network
docker network inspect sps-platform_sps-network

# Should show all 5 containers
```

**Check container network settings:**
```bash
# Get container network info
docker inspect sps-website | jq '.[0].NetworkSettings.Networks'

# Should show sps-network with IPv4Address
```

---

## Code Organization

### File Structure Best Practices

```
website/src/
├── pages/
│   ├── index.astro           # Homepage
│   ├── about.astro            # About page
│   └── api/                   # Server-side API routes
│       ├── assess-risk.ts     # Internal proxy to sps-brain
│       └── health.ts          # Health check endpoint
├── components/
│   ├── Card.astro             # Reusable components
│   └── widgets/               # Complex interactive components
│       └── SectorIntelligence.tsx  # React components
├── layouts/
│   └── Layout.astro           # Base layout wrapper
└── content/
    ├── sectors/               # Content collections
    └── casestudies/
```

### When to Use Each File Type

**`.astro` files**: Static or server-rendered content
- Pages that don't need interactivity
- Layout wrappers
- Server-side data fetching

**`.tsx/.jsx` files**: Client-side interactivity
- Forms with validation
- Interactive widgets
- State management
- Real-time updates

**`.ts` files in `/api`**: Server-side logic
- API proxies
- Authentication
- Data processing
- External API calls

### API Route Patterns

**Pattern 1: Simple Proxy**
```typescript
// src/pages/api/proxy.ts
export async function post({ request }) {
  const body = await request.json();
  const response = await fetch('http://sps-brain:8000/endpoint', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  });
  return response;
}
```

**Pattern 2: Data Transformation**
```typescript
// src/pages/api/transform.ts
export async function get() {
  const response = await fetch('http://sps-brain:8000/raw-data');
  const rawData = await response.json();
  
  // Transform for frontend
  const transformed = rawData.items.map(item => ({
    id: item.id,
    title: item.title,
    // Only send what frontend needs
  }));
  
  return new Response(JSON.stringify(transformed), {
    headers: { 'Content-Type': 'application/json' }
  });
}
```

**Pattern 3: Authentication Wrapper**
```typescript
// src/pages/api/secure.ts
export async function post({ request, cookies }) {
  // Check authentication
  const token = cookies.get('auth-token');
  if (!token) {
    return new Response(JSON.stringify({ error: 'Unauthorized' }), {
      status: 401
    });
  }
  
  // Forward to backend
  const response = await fetch('http://sps-brain:8000/secure-endpoint', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: await request.text()
  });
  
  return response;
}
```

---

## Testing Best Practices

### Local Development Testing

**1. Start development servers:**
```bash
# Terminal 1: Backend
cd agent_backend
uvicorn api:app --reload --port 8000

# Terminal 2: Frontend
cd website
npm run dev
```

**2. Test internal communication:**
```javascript
// In browser console on localhost:4321
fetch('/api/health')
  .then(r => r.json())
  .then(console.log);
```

**3. Test API directly:**
```bash
curl http://localhost:8000/health
```

### Docker Testing (Pre-Production)

**Build and test locally:**
```bash
# Build containers
docker compose -f docker-compose.prod.yml build

# Start services
docker compose -f docker-compose.prod.yml up

# Test (in another terminal)
curl http://localhost:4321  # Website
curl http://localhost:8000/health  # API
curl http://localhost:5678/healthz  # n8n
```

### Production Testing Checklist

```bash
#!/bin/bash
# save as: test-production.sh

echo "=== Production Health Check ==="

echo "\n1. Website..."
curl -I https://sukhi.in | head -1

echo "\n2. API Health..."
curl -s https://api.sukhi.in/health | jq '.'

echo "\n3. n8n Health..."
curl -I https://automator.sukhi.in | head -1

echo "\n4. SSL Grade..."
echo "Check: https://www.ssllabs.com/ssltest/analyze.html?d=sukhi.in"

echo "\n5. Container Status..."
ssh root@72.61.172.188 'cd /root/sps-platform && docker ps'

echo "\n=== Tests Complete ==="
```

---

## Performance Optimization

### Image Optimization

**Use Astro's Image component:**
```astro
---
import { Image } from 'astro:assets';
import hero from '../assets/hero.jpg';
---

<!-- ❌ WRONG - Large unoptimized image -->
<img src="/images/hero.jpg" alt="Hero" />

<!-- ✅ CORRECT - Automatically optimized -->
<Image src={hero} alt="Hero" width={1200} height={600} />
```

**Benefits:**
- Automatic format conversion (WebP/AVIF)
- Responsive image sizes
- Lazy loading
- Optimized compression

### Code Splitting

**Lazy load heavy components:**
```astro
---
// Don't import heavy React components at top level
// import HeavyChart from '../components/HeavyChart';
---

<!-- Lazy load when needed -->
<div id="chart-container"></div>

<script>
  // Load chart library only when user scrolls to it
  const observer = new IntersectionObserver(async (entries) => {
    if (entries[0].isIntersecting) {
      const { HeavyChart } = await import('../components/HeavyChart');
      // Render chart
    }
  });
  observer.observe(document.getElementById('chart-container'));
</script>
```

### Caching Strategies

**API Route Caching:**
```typescript
// src/pages/api/cached-data.ts
const cache = new Map();
const CACHE_TTL = 60000; // 1 minute

export async function get() {
  const now = Date.now();
  const cached = cache.get('data');
  
  if (cached && (now - cached.timestamp) < CACHE_TTL) {
    return new Response(JSON.stringify(cached.data), {
      headers: { 'Content-Type': 'application/json' }
    });
  }
  
  // Fetch fresh data
  const response = await fetch('http://sps-brain:8000/data');
  const data = await response.json();
  
  cache.set('data', { data, timestamp: now });
  
  return new Response(JSON.stringify(data), {
    headers: { 'Content-Type': 'application/json' }
  });
}
```

### Build Optimization

**Minimize bundle size:**
```javascript
// astro.config.mjs
export default defineConfig({
  build: {
    inlineStylesheets: 'auto',
  },
  vite: {
    build: {
      rollupOptions: {
        output: {
          manualChunks: {
            'vendor': ['react', 'react-dom'],
          }
        }
      }
    }
  }
});
```

---

## Summary: Key Takeaways

### Critical Rules

1. ✅ **Async/await ONLY in frontmatter** - Never in JSX
2. ✅ **Internal communication uses Docker network** - No API key
3. ✅ **External communication uses api.sukhi.in** - Requires API key
4. ✅ **Pre-process data in frontmatter** - Keep JSX simple
5. ✅ **Use API routes for dynamic data** - Not component fetching

### Common Mistakes to Avoid

1. ❌ Using `await` in JSX expressions
2. ❌ Calling public API from server-side code
3. ❌ Exposing API keys to client-side
4. ❌ Complex logic in JSX templates
5. ❌ Unoptimized images and heavy bundles

### Quick Reference Commands

```bash
# Start local development
npm run dev

# Build for production
npm run build

# Test Docker build
docker compose -f docker-compose.prod.yml build

# Deploy to production
git push origin main
ssh root@72.61.172.188 'cd /root/sps-platform && git pull && docker compose -f docker-compose.prod.yml up -d --build'
```

---

**Last Updated**: January 27, 2026  
**Version**: 1.0  
**Status**: Active Reference
