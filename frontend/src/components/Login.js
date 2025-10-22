import React, { useState } from 'react';
import './Login.css';

function Login({ onLogin }) {
  const [email, setEmail] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    setError('');

    // Validate email ends with @hcltech.com
    if (!email.endsWith('@hcltech.com')) {
      setError('Only @hcltech.com email addresses are allowed');
      return;
    }

    // Email validation
    const emailRegex = /^[^\s@]+@hcltech\.com$/;
    if (!emailRegex.test(email)) {
      setError('Please enter a valid email address');
      return;
    }

    onLogin(email);
  };

  return (
    <div className="login-container">
      <div className="login-card">
        <div className="login-header">
          <h1>RFx Agent Dashboard</h1>
          <p>AI-Powered RFP Processing System</p>
        </div>

        <form onSubmit={handleSubmit} className="login-form">
          <div className="form-group">
            <label htmlFor="email">Email Address</label>
            <input
              type="email"
              id="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="your.name@hcltech.com"
              required
              className="input-field"
            />
            <small>Only @hcltech.com emails are allowed</small>
          </div>

          {error && <div className="error">{error}</div>}

          <button type="submit" className="btn btn-primary btn-block">
            Sign In
          </button>
        </form>

        <div className="login-footer">
          <p>Powered by Amazon Bedrock & AWS Lambda</p>
        </div>
      </div>
    </div>
  );
}

export default Login;

