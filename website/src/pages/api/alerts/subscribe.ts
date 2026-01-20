import type { APIRoute } from 'astro';

// Server-rendered API route
export const prerender = false;

// Note: In production, this would connect to the Python backend via a worker/queue
// For now, we use a simple in-memory store

interface Subscription {
  id: string;
  email: string;
  sectors: string[];
  frequency: 'instant' | 'daily' | 'weekly';
  channels: string[];
  verified: boolean;
  created_at: string;
}

// Temporary in-memory store
const subscriptions = new Map<string, Subscription>();

// Simple hash function for subscriber ID
function hashEmail(email: string): string {
  let hash = 0;
  for (let i = 0; i < email.length; i++) {
    const char = email.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash;
  }
  return Math.abs(hash).toString(16);
}

export const POST: APIRoute = async ({ request }) => {
  try {
    const body = await request.json();
    const { email, sectors, frequency = 'instant', channels = ['email'] } = body;

    // Validate email
    if (!email || typeof email !== 'string' || !email.includes('@')) {
      return new Response(JSON.stringify({ error: 'Valid email required' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    // Validate sectors
    if (!Array.isArray(sectors) || sectors.length === 0) {
      return new Response(JSON.stringify({ error: 'At least one sector required' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    // Validate frequency
    if (!['instant', 'daily', 'weekly'].includes(frequency)) {
      return new Response(JSON.stringify({ error: 'Invalid frequency' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    // Validate channels
    const validChannels = ['email', 'sms', 'push'];
    const filteredChannels = channels.filter((c: string) => validChannels.includes(c));
    if (filteredChannels.length === 0) {
      return new Response(JSON.stringify({ error: 'At least one valid channel required' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    const subscriberId = hashEmail(email.toLowerCase().trim());

    const subscription: Subscription = {
      id: subscriberId,
      email: email.toLowerCase().trim(),
      sectors: sectors.slice(0, 10), // Max 10 sectors
      frequency,
      channels: filteredChannels,
      verified: false, // Requires email verification in production
      created_at: new Date().toISOString(),
    };

    subscriptions.set(subscriberId, subscription);

    // TODO: In production, send verification email via Resend

    return new Response(JSON.stringify({
      success: true,
      subscription: {
        id: subscription.id,
        email: subscription.email,
        sectors: subscription.sectors,
        frequency: subscription.frequency,
        verified: subscription.verified,
      },
      message: 'Subscription created. Please check your email to verify.',
    }), {
      status: 201,
      headers: { 'Content-Type': 'application/json' },
    });
  } catch (error) {
    console.error('Subscription error:', error);
    return new Response(JSON.stringify({ error: 'Internal server error' }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    });
  }
};

export const DELETE: APIRoute = async ({ request }) => {
  try {
    const body = await request.json();
    const { email } = body;

    if (!email || typeof email !== 'string') {
      return new Response(JSON.stringify({ error: 'Email required' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    const subscriberId = hashEmail(email.toLowerCase().trim());
    const existed = subscriptions.delete(subscriberId);

    return new Response(JSON.stringify({
      success: true,
      unsubscribed: existed,
    }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  } catch (error) {
    console.error('Unsubscribe error:', error);
    return new Response(JSON.stringify({ error: 'Internal server error' }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    });
  }
};
