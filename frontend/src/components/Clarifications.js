import React, { useEffect, useMemo, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { fetchS3Json, S3_OUTPUT_BUCKET, findUserClarifications } from '../services/awsService';
import './Clarifications.css';

function Clarifications({ user, onLogout }) {
  const navigate = useNavigate();
  const location = useLocation();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [questions, setQuestions] = useState([]);
  const [answers, setAnswers] = useState({});
  const [continuing, setContinuing] = useState(false);

  const results = useMemo(() => {
    return location.state?.results || (() => {
      try {
        const cached = localStorage.getItem('rfx_results');
        return cached ? JSON.parse(cached) : null;
      } catch (e) {
        return null;
      }
    })();
  }, [location.state]);

  useEffect(() => {
    const loadClarifications = async () => {
      try {
        setLoading(true);
        setError('');

        // First try to find clarifications from processing results
        if (results) {
          const steps = results.body?.steps || results.steps || [];
          const clarStep = steps.find((s) => {
            const name = (s.step || '').toLowerCase();
            const out = (s.output || '').toLowerCase();
            return out.endsWith('.json') && (name.includes('clarification') || out.includes('clarification'));
          }) || steps.find((s) => (s.output || '').toLowerCase().endsWith('.json'));

          if (clarStep?.output) {
            console.log('Found clarifications in processing results:', clarStep.output);
            const json = await fetchS3Json(S3_OUTPUT_BUCKET, clarStep.output);
            processClarifications(json);
            return;
          }
        }

        // If no results or no clarifications in results, try to find latest user file
        if (user?.email) {
          console.log('Searching for latest clarifications for user:', user.email);
          const latestFile = await findUserClarifications(user.email);
          
          if (latestFile) {
            console.log('Found latest clarifications file:', latestFile.Key);
            const json = await fetchS3Json(S3_OUTPUT_BUCKET, latestFile.Key);
            processClarifications(json);
            return;
          }
        }

        setError('No clarifications found. Please process an RFP first.');
      } catch (e) {
        console.error('Error loading clarifications:', e);
        setError(e.message || 'Failed to load clarifications');
      } finally {
        setLoading(false);
      }
    };

    const processClarifications = (json) => {
      let qList = [];
      if (Array.isArray(json)) {
        qList = json.map((q) => {
          if (typeof q === 'string') return { text: q };
          const text = q.question || q.q || q.text || q.prompt || JSON.stringify(q);
          return { text };
        });
      } else if (Array.isArray(json?.questions)) {
        qList = json.questions.map((q) => (typeof q === 'string' ? { text: q } : { text: q.question || q.text || JSON.stringify(q) }));
      } else if (Array.isArray(json?.clarifications)) {
        qList = json.clarifications.map((q) => (typeof q === 'string' ? { text: q } : { text: q.question || q.text || JSON.stringify(q) }));
      } else {
        // Fallback: treat object keys as questions
        qList = Object.keys(json || {}).map((k) => ({ text: `${k}: ${typeof json[k] === 'string' ? json[k] : JSON.stringify(json[k])}` }));
      }
      setQuestions(qList);
    };

    loadClarifications();
  }, [results, user]);

  const handleAnswerChange = (index, value) => {
    setAnswers((prev) => ({ ...prev, [index]: value }));
  };

  const handleContinue = () => {
    try {
      localStorage.setItem('rfx_results', JSON.stringify(results));
      localStorage.setItem('rfx_clarification_answers', JSON.stringify(answers));
    } catch (_) {}
    setContinuing(true);
    setTimeout(() => {
      navigate('/results', { state: { results, clarificationAnswers: answers } });
    }, 4500);
  };

  return (
    <div className="clar-page">
      <nav className="navbar">
        <div className="navbar-brand">
          <h2>RFx Agent Dashboard</h2>
        </div>
        <div className="navbar-menu">
          <button className="nav-item" onClick={() => navigate('/dashboard')}>Dashboard</button>
          <div className="navbar-user">
            <span>{user?.email}</span>
            <button className="btn btn-secondary btn-sm" onClick={onLogout}>Logout</button>
          </div>
        </div>
      </nav>

      <div className="clar-content">
        <div className="container">
          <div className="card">
            <h3>Clarification Questions</h3>
            {loading && <div className="loading">Loading clarifications...</div>}
            {error && <div className="error">{error}</div>}
            {!loading && !error && (
              <div className="clar-list">
                {questions.map((q, idx) => (
                  <div className="clar-item" key={idx}>
                    <div className="clar-q">
                      <span className="clar-num">{idx + 1}</span>
                      <span>{q.text}</span>
                    </div>
                    <textarea
                      className="clar-input"
                      placeholder="Type your answer here..."
                      value={answers[idx] || ''}
                      onChange={(e) => handleAnswerChange(idx, e.target.value)}
                      rows={3}
                    />
                  </div>
                ))}
                {questions.length === 0 && (
                  <div className="empty">No clarification questions found.</div>
                )}
                <div className="clar-actions">
                  <button className="btn btn-secondary" onClick={() => navigate('/dashboard')}>Back</button>
                  <button className="btn btn-primary" onClick={handleContinue} disabled={continuing}>
                    {continuing ? 'Preparing results…' : 'Continue to Results'}
                  </button>
                </div>
                {continuing && <div className="loading" style={{ marginTop: 8 }}>Please wait ~4–5 seconds…</div>}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default Clarifications;


