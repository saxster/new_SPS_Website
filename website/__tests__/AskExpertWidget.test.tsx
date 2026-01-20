/** @jsxImportSource preact */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, fireEvent, waitFor, screen } from '@testing-library/preact';
import { h } from 'preact';
import AskExpertWidget from '../src/components/widgets/AskExpertWidget';

/**
 * Tests for AskExpertWidget Streaming Functionality
 *
 * These tests verify:
 * 1. Widget attempts EventSource for streaming by default
 * 2. Widget falls back to POST if EventSource fails
 * 3. Streaming text is displayed incrementally
 * 4. Streaming cursor is shown during stream
 * 5. Cursor is hidden after stream completes
 */

// Mock EventSource
class MockEventSource {
  url: string;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  onopen: ((event: Event) => void) | null = null;
  readyState: number = 0;

  static instances: MockEventSource[] = [];

  constructor(url: string) {
    this.url = url;
    this.readyState = 0; // CONNECTING
    MockEventSource.instances.push(this);
  }

  close() {
    this.readyState = 2; // CLOSED
  }

  // Helper to simulate receiving a message
  simulateMessage(data: string) {
    if (this.onmessage) {
      this.onmessage({ data } as MessageEvent);
    }
  }

  // Helper to simulate error
  simulateError() {
    this.readyState = 2;
    if (this.onerror) {
      this.onerror(new Event('error'));
    }
  }

  // Helper to simulate open
  simulateOpen() {
    this.readyState = 1; // OPEN
    if (this.onopen) {
      this.onopen(new Event('open'));
    }
  }

  static clearInstances() {
    MockEventSource.instances = [];
  }
}

describe('AskExpertWidget', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    MockEventSource.clearInstances();
    // @ts-ignore - mocking global
    global.EventSource = MockEventSource;
    // Mock scrollIntoView for jsdom
    Element.prototype.scrollIntoView = vi.fn();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('Basic Rendering', () => {
    it('should render the trigger button when closed', () => {
      render(<AskExpertWidget />);
      expect(screen.getByText('ASK AI EXPERT')).toBeDefined();
    });

    it('should open panel when trigger is clicked', async () => {
      render(<AskExpertWidget />);
      const trigger = screen.getByText('ASK AI EXPERT');
      fireEvent.click(trigger);

      await waitFor(() => {
        expect(screen.getByText('SPS ORACLE v2.0')).toBeDefined();
      });
    });
  });

  describe('Streaming with EventSource', () => {
    it('should use EventSource for queries when streaming is enabled', async () => {
      render(<AskExpertWidget />);

      // Open the widget
      fireEvent.click(screen.getByText('ASK AI EXPERT'));

      await waitFor(() => {
        expect(screen.getByPlaceholderText('Ask a security question...')).toBeDefined();
      });

      // Type and submit a query
      const input = screen.getByPlaceholderText('Ask a security question...');
      fireEvent.input(input, { target: { value: 'test query' } });
      fireEvent.submit(input.closest('form')!);

      // Should have created an EventSource instance
      await waitFor(() => {
        expect(MockEventSource.instances.length).toBeGreaterThan(0);
      });

      // Verify the URL contains the query
      const eventSource = MockEventSource.instances[MockEventSource.instances.length - 1];
      expect(eventSource.url).toContain('query=');
      expect(eventSource.url).toContain('test%20query');
    });

    it('should display streaming tokens incrementally', async () => {
      render(<AskExpertWidget />);

      // Open and submit
      fireEvent.click(screen.getByText('ASK AI EXPERT'));
      await waitFor(() => {
        expect(screen.getByPlaceholderText('Ask a security question...')).toBeDefined();
      });

      const input = screen.getByPlaceholderText('Ask a security question...');
      fireEvent.input(input, { target: { value: 'streaming test' } });
      fireEvent.submit(input.closest('form')!);

      await waitFor(() => {
        expect(MockEventSource.instances.length).toBeGreaterThan(0);
      });

      const eventSource = MockEventSource.instances[MockEventSource.instances.length - 1];
      eventSource.simulateOpen();

      // Simulate streaming tokens
      eventSource.simulateMessage(JSON.stringify({ token: 'Hello' }));
      await waitFor(() => {
        expect(screen.getByText(/Hello/)).toBeDefined();
      });

      eventSource.simulateMessage(JSON.stringify({ token: ' World' }));
      await waitFor(() => {
        expect(screen.getByText(/Hello World/)).toBeDefined();
      });

      // Complete the stream
      eventSource.simulateMessage(JSON.stringify({ done: true }));
    });

    it('should show streaming cursor during active stream', async () => {
      render(<AskExpertWidget />);

      // Open and submit
      fireEvent.click(screen.getByText('ASK AI EXPERT'));
      await waitFor(() => {
        expect(screen.getByPlaceholderText('Ask a security question...')).toBeDefined();
      });

      const input = screen.getByPlaceholderText('Ask a security question...');
      fireEvent.input(input, { target: { value: 'cursor test' } });
      fireEvent.submit(input.closest('form')!);

      await waitFor(() => {
        expect(MockEventSource.instances.length).toBeGreaterThan(0);
      });

      const eventSource = MockEventSource.instances[MockEventSource.instances.length - 1];
      eventSource.simulateOpen();
      eventSource.simulateMessage(JSON.stringify({ token: 'Test' }));

      // Should show streaming cursor
      await waitFor(() => {
        const streamingElement = document.querySelector('.streaming-cursor');
        expect(streamingElement).toBeDefined();
      });
    });

    it('should hide cursor after stream completes', async () => {
      render(<AskExpertWidget />);

      // Open and submit
      fireEvent.click(screen.getByText('ASK AI EXPERT'));
      await waitFor(() => {
        expect(screen.getByPlaceholderText('Ask a security question...')).toBeDefined();
      });

      const input = screen.getByPlaceholderText('Ask a security question...');
      fireEvent.input(input, { target: { value: 'cursor complete test' } });
      fireEvent.submit(input.closest('form')!);

      await waitFor(() => {
        expect(MockEventSource.instances.length).toBeGreaterThan(0);
      });

      const eventSource = MockEventSource.instances[MockEventSource.instances.length - 1];
      eventSource.simulateOpen();
      eventSource.simulateMessage(JSON.stringify({ token: 'Complete' }));
      eventSource.simulateMessage(JSON.stringify({ done: true }));

      // Cursor should be hidden after done
      await waitFor(() => {
        const streamingElement = document.querySelector('.streaming-cursor');
        expect(streamingElement).toBeNull();
      });
    });
  });

  describe('Fallback to POST', () => {
    it('should fall back to POST when EventSource fails', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ response: 'Fallback response' }),
      });
      global.fetch = mockFetch;

      render(<AskExpertWidget />);

      // Open and submit
      fireEvent.click(screen.getByText('ASK AI EXPERT'));
      await waitFor(() => {
        expect(screen.getByPlaceholderText('Ask a security question...')).toBeDefined();
      });

      const input = screen.getByPlaceholderText('Ask a security question...');
      fireEvent.input(input, { target: { value: 'fallback test' } });
      fireEvent.submit(input.closest('form')!);

      await waitFor(() => {
        expect(MockEventSource.instances.length).toBeGreaterThan(0);
      });

      // Simulate EventSource error
      const eventSource = MockEventSource.instances[MockEventSource.instances.length - 1];
      eventSource.simulateError();

      // Should have called fetch as fallback
      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(
          '/api/ask-expert',
          expect.objectContaining({
            method: 'POST',
          })
        );
      });

      // Should display the fallback response
      await waitFor(() => {
        expect(screen.getByText(/Fallback response/)).toBeDefined();
      });
    });
  });

  describe('Cached Response Handling', () => {
    it('should handle cached responses with full content', async () => {
      render(<AskExpertWidget />);

      // Open and submit
      fireEvent.click(screen.getByText('ASK AI EXPERT'));
      await waitFor(() => {
        expect(screen.getByPlaceholderText('Ask a security question...')).toBeDefined();
      });

      const input = screen.getByPlaceholderText('Ask a security question...');
      fireEvent.input(input, { target: { value: 'cached query' } });
      fireEvent.submit(input.closest('form')!);

      await waitFor(() => {
        expect(MockEventSource.instances.length).toBeGreaterThan(0);
      });

      const eventSource = MockEventSource.instances[MockEventSource.instances.length - 1];
      eventSource.simulateOpen();

      // Simulate cached response (full response in one event)
      eventSource.simulateMessage(JSON.stringify({
        response: 'This is a cached response',
        cached: true,
        done: true,
      }));

      await waitFor(() => {
        expect(screen.getByText(/This is a cached response/)).toBeDefined();
      });
    });
  });

  describe('Error Handling', () => {
    it('should display error message from stream', async () => {
      render(<AskExpertWidget />);

      // Open and submit
      fireEvent.click(screen.getByText('ASK AI EXPERT'));
      await waitFor(() => {
        expect(screen.getByPlaceholderText('Ask a security question...')).toBeDefined();
      });

      const input = screen.getByPlaceholderText('Ask a security question...');
      fireEvent.input(input, { target: { value: 'error test' } });
      fireEvent.submit(input.closest('form')!);

      await waitFor(() => {
        expect(MockEventSource.instances.length).toBeGreaterThan(0);
      });

      const eventSource = MockEventSource.instances[MockEventSource.instances.length - 1];
      eventSource.simulateOpen();
      eventSource.simulateMessage(JSON.stringify({
        error: 'An error occurred',
        done: true,
      }));

      await waitFor(() => {
        expect(screen.getByText(/An error occurred/)).toBeDefined();
      });
    });
  });
});
