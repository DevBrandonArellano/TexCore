import React, { Component, ErrorInfo, ReactNode } from 'react';
import { createLogger } from '../../lib/logger';

// RFC 5424 — Severity 2 (CRITICAL) para errores de renderizado no recuperables
const logger = createLogger('ErrorBoundary');

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // RFC 5424 Severity 2 — CRITICAL: error de renderizado no recuperable
    logger.critical('Error de renderizado no recuperable capturado', {
      error: error.message,
      name: error.name,
      component: errorInfo.componentStack?.trim().split('\n')[1]?.trim() ?? 'unknown',
    });
  }

  public render() {
    if (this.state.hasError && this.state.error) {
      if (this.props.fallback) {
        return this.props.fallback;
      }
      return (
        <div className="p-4 border border-destructive rounded-lg bg-destructive/10">
          <p className="font-semibold text-destructive">Error al cargar</p>
          <p className="text-sm mt-1">{this.state.error.message}</p>
        </div>
      );
    }
    return this.props.children;
  }
}
