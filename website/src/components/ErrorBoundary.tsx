import { Component } from 'preact';
import type { ComponentChildren } from 'preact';

interface ErrorBoundaryProps {
  children: ComponentChildren;
  fallbackTitle?: string;
  fallbackMessage?: string;
  showRetry?: boolean;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

/**
 * ErrorBoundary component for catching and handling errors in React/Preact component trees.
 *
 * Usage:
 * <ErrorBoundary fallbackTitle="Feed Unavailable" fallbackMessage="Unable to load threat data.">
 *   <CisaKevFeed />
 * </ErrorBoundary>
 */
export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: any) {
    // Log error for debugging (in production, send to error tracking service)
    console.error('ErrorBoundary caught error:', error);
    console.error('Component stack:', errorInfo?.componentStack);
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    const {
      children,
      fallbackTitle = 'Component Error',
      fallbackMessage = 'This component encountered an error and cannot be displayed.',
      showRetry = true,
    } = this.props;

    if (this.state.hasError) {
      return (
        <div class="bg-neutral-900/50 border-2 border-red-500/30 p-6 rounded" role="alert">
          <div class="flex items-start gap-3 mb-4">
            <span class="flex-shrink-0 w-6 h-6 flex items-center justify-center bg-red-500/20 rounded-full">
              <svg class="w-4 h-4 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
              </svg>
            </span>
            <div class="flex-1">
              <h3 class="text-white font-bold text-lg mb-1">{fallbackTitle}</h3>
              <p class="text-neutral-400 text-sm">{fallbackMessage}</p>
            </div>
          </div>

          {/* Error details (development mode) */}
          {this.state.error && (
            <details class="mb-4 text-xs font-mono">
              <summary class="text-neutral-500 cursor-pointer hover:text-neutral-300 transition-colors">
                Technical Details
              </summary>
              <pre class="mt-2 p-3 bg-black/50 border border-neutral-800 overflow-x-auto text-red-400 whitespace-pre-wrap">
                {this.state.error.message}
              </pre>
            </details>
          )}

          {showRetry && (
            <button
              onClick={this.handleRetry}
              class="inline-flex items-center gap-2 px-4 py-2 bg-neutral-800 hover:bg-neutral-700 border border-neutral-700 text-white text-sm font-medium transition-colors"
            >
              <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              Retry
            </button>
          )}
        </div>
      );
    }

    return children;
  }
}

/**
 * Higher-order component wrapper for adding error boundary to any component
 */
export function withErrorBoundary<P extends object>(
  WrappedComponent: (props: P) => any,
  fallbackTitle?: string,
  fallbackMessage?: string
) {
  return function WithErrorBoundaryWrapper(props: P) {
    return (
      <ErrorBoundary fallbackTitle={fallbackTitle} fallbackMessage={fallbackMessage}>
        <WrappedComponent {...props} />
      </ErrorBoundary>
    );
  };
}

export default ErrorBoundary;
