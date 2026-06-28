import React from 'react';

class ErrorBoundary extends React.Component {
    constructor(props) {
        super(props);
        this.state = { hasError: false, error: null };
    }

    static getDerivedStateFromError(error) {
        return { hasError: true, error };
    }

    render() {
        if (this.state.hasError) {
            return (
                <div className="min-h-screen flex items-center justify-center bg-[#0F0F1A] text-white p-6 text-center">
                    <div className="glass p-10 rounded-2xl max-w-md">
                        <span className="text-5xl block mb-4">😵</span>
                        <h1 className="text-2xl font-bold mb-2">Oops! Something went wrong.</h1>
                        <p className="text-slate-400 mb-6 text-sm">{this.state.error?.message || "An unexpected error occurred."}</p>
                        <button onClick={() => window.location.reload()} className="gradient-btn px-6 py-2 rounded-full font-medium">Refresh Page</button>
                    </div>
                </div>
            );
        }
        return this.props.children;
    }
}
export default ErrorBoundary;
