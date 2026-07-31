import { Component, type ReactNode } from "react";
import { Button, Result } from "antd";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export default class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          minHeight: "100vh",
          background: "#0d0d0d",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}>
          <Result
            status="500"
            title="Something went wrong"
            subTitle={this.state.error?.message || "An unexpected error occurred"}
            extra={
              <Button type="primary" onClick={() => window.location.reload()}>
                Reload Page
              </Button>
            }
          />
        </div>
      );
    }

    return this.props.children;
  }
}
