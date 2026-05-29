import { Component, type ReactNode } from 'react';
import { AlertTriangle, RotateCcw } from 'lucide-react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    // eslint-disable-next-line no-console
    console.error('ErrorBoundary caught an error:', error, errorInfo);
  }

  private handleReload = () => {
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="h-screen flex flex-col items-center justify-center bg-apple-gray-50 text-apple-gray-900 p-8">
          <div className="apple-card p-8 max-w-sm w-full flex flex-col items-center text-center gap-5 animate-scale-in">
            <div className="w-14 h-14 rounded-2xl bg-apple-red-light flex items-center justify-center">
              <AlertTriangle size={28} className="text-apple-red" strokeWidth={2} />
            </div>
            <div>
              <h1 className="text-lg font-bold text-apple-gray-900 tracking-tight mb-1">
                出错了
              </h1>
              <p className="text-sm text-apple-gray-400 font-medium">
                页面渲染失败，请刷新重试
              </p>
            </div>
            {this.state.error && (
              <div className="w-full rounded-xl bg-apple-gray-50 p-3 text-left">
                <p className="text-[11px] font-mono text-apple-gray-500 break-all leading-relaxed">
                  {this.state.error.message}
                </p>
              </div>
            )}
            <button
              onClick={this.handleReload}
              className="apple-btn-primary gap-2 w-full justify-center"
              aria-label="刷新页面"
            >
              <RotateCcw size={14} strokeWidth={2.5} />
              刷新页面
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
