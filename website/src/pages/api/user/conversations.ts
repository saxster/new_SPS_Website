import type { APIRoute } from 'astro';

// Server-rendered API route
export const prerender = false;

// Note: In production, this would connect to SQLite via content_brain.py
// For now, we use a simple in-memory store (per-session)
// TODO: Implement proper database connection

interface Message {
  sender: 'user' | 'expert';
  content: string;
  created_at: string;
}

interface Conversation {
  id: string;
  title: string;
  messages: Message[];
  created_at: string;
}

// Temporary in-memory store (for development)
const userConversations = new Map<string, Conversation[]>();

export const GET: APIRoute = async ({ locals }) => {
  try {
    const auth = locals.auth();

    if (!auth.userId) {
      return new Response(JSON.stringify({ error: 'Unauthorized' }), {
        status: 401,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    const conversations = userConversations.get(auth.userId) || [];

    // Return summarized version for list view
    const summaries = conversations.map(conv => ({
      id: conv.id,
      title: conv.title,
      created_at: conv.created_at,
      message_count: conv.messages.length,
      last_message_preview: conv.messages.length > 0
        ? conv.messages[conv.messages.length - 1].content.substring(0, 100)
        : '',
    }));

    return new Response(JSON.stringify({ conversations: summaries }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  } catch (error) {
    console.error('Error fetching conversations:', error);
    return new Response(JSON.stringify({ error: 'Internal server error' }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    });
  }
};

export const POST: APIRoute = async ({ locals, request }) => {
  try {
    const auth = locals.auth();

    if (!auth.userId) {
      return new Response(JSON.stringify({ error: 'Unauthorized' }), {
        status: 401,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    const body = await request.json();
    const { title, message } = body;

    if (!message || typeof message !== 'string') {
      return new Response(JSON.stringify({ error: 'Invalid message' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    const currentConversations = userConversations.get(auth.userId) || [];

    const newConversation: Conversation = {
      id: `conv_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      title: title || message.substring(0, 50),
      messages: [{
        sender: 'user',
        content: message,
        created_at: new Date().toISOString(),
      }],
      created_at: new Date().toISOString(),
    };

    userConversations.set(auth.userId, [newConversation, ...currentConversations]);

    return new Response(JSON.stringify({ success: true, conversation: newConversation }), {
      status: 201,
      headers: { 'Content-Type': 'application/json' },
    });
  } catch (error) {
    console.error('Error creating conversation:', error);
    return new Response(JSON.stringify({ error: 'Internal server error' }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    });
  }
};
