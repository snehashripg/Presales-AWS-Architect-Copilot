import React from 'react';
import { useNavigate } from 'react-router-dom';
import './ChatAgent.css';

function ChatAgent({ user, onLogout }) {
  const navigate = useNavigate();

  return (
    <div className="chat-container">
      {/* Navigation Bar */}
      <nav className="navbar">
        <div className="navbar-brand">
          <h2>RFx Agent Dashboard</h2>
        </div>
        <div className="navbar-menu">
          <button className="nav-item" onClick={() => navigate('/dashboard')}>
            Dashboard
          </button>
          <button className="nav-item active" onClick={() => navigate('/chat')}>
            Chat with Agent
          </button>
          <div className="navbar-user">
            <span>{user.email}</span>
            <button className="btn btn-secondary btn-sm" onClick={onLogout}>
              Logout
            </button>
          </div>
        </div>
      </nav>

      {/* Chat Content */}
      <div className="chat-content">
        <div className="container">
          <div className="card chat-placeholder">
            <div className="placeholder-icon"></div>
            <h3>Chat with AI Agent</h3>
            <p>This feature is coming soon!</p>
            <p className="placeholder-text">
              You'll be able to chat with our AI agent to get instant answers about your RFP documents,
              ask questions about proposals, and get expert guidance throughout the process.
            </p>
            <div className="placeholder-features">
              <div className="feature-item">
                <span className="feature-icon"></span>
                <span>Ask questions about RFP requirements</span>
              </div>
              <div className="feature-item">
                <span className="feature-icon">💡</span>
                <span>Get suggestions for proposals</span>
              </div>
              <div className="feature-item">
                <span className="feature-icon"></span>
                <span>Analyze pricing and timelines</span>
              </div>
              <div className="feature-item">
                <span className="feature-icon"></span>
                <span>Draft responses collaboratively</span>
              </div>
            </div>
            <button className="btn btn-primary" onClick={() => navigate('/dashboard')}>
              Back to Dashboard
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default ChatAgent;

