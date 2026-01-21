import type { APIRoute } from 'astro';

export const POST: APIRoute = async ({ request }) => {
  const pythonApiUrl = 'http://localhost:8000/knowledge/query';
  
  try {
    const body = await request.json();
    
    const response = await fetch(pythonApiUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
        return new Response(JSON.stringify({ answer: "System Error: Brain unreachable." }), { status: 500 });
    }

    const result = await response.json();
    return new Response(JSON.stringify(result), { status: 200 });

  } catch (error) {
    return new Response(JSON.stringify({ answer: "Connection Error." }), { status: 500 });
  }
};
