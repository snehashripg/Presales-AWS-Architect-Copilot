import React, { useMemo } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import Dashboard from './Dashboard';

// Results page reuses Dashboard rendering by passing results via location state/localStorage
function Results({ user, onLogout }) {
  const navigate = useNavigate();
  const location = useLocation();

  const results = useMemo(() => {
    if (location.state?.results) return location.state.results;
    try {
      const cached = localStorage.getItem('rfx_results');
      return cached ? JSON.parse(cached) : null;
    } catch (e) {
      return null;
    }
  }, [location.state]);

  // We render the Dashboard component but prevent the upload section by passing a flag
  return (
    <div>
      <Dashboard user={user} onLogout={onLogout} presetResults={results} hideUploader />
    </div>
  );
}

export default Results;


