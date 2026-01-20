import type { APIRoute } from 'astro';

export const POST: APIRoute = async ({ request }) => {
  try {
    const body = await request.json();
    const { sector, data } = body;

    // Call Python Backend
    const pythonApiUrl = 'http://127.0.0.1:8000/assess-risk';
    const response = await fetch(pythonApiUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-sps-auth': 'sps-secret', // Internal auth key
      },
      body: JSON.stringify({
        sector,
        data
      }),
    });

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        return new Response(JSON.stringify({ error: errorData.detail || 'Backend calculation failed' }), {
            status: response.status,
            headers: { 'Content-Type': 'application/json' }
        });
    }

    const result = await response.json();
    return new Response(JSON.stringify(result), {
      status: 200,
      headers: { 'Content-Type': 'application/json' }
    });

  } catch (error) {
    console.error('Risk Assessment Proxy Error:', error);
    return new Response(JSON.stringify({ error: 'Internal Server Error' }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
};
