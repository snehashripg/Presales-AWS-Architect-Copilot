import React, { useState, useEffect } from 'react';
import { fetchS3Json, S3_OUTPUT_BUCKET } from '../services/awsService';
import './ArchitectureDiagram.css';

function ArchitectureDiagram({ results }) {
  const [architectureData, setArchitectureData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!results || !results.steps) return;

    // Find the architecture diagram step
    const architectureStep = results.steps.find(step => 
      step.step === 'Architecture Diagram' && 
      step.output && 
      step.output.endsWith('.json')
    );

    if (architectureStep && architectureStep.output) {
      setLoading(true);
      setError('');
      fetchS3Json(S3_OUTPUT_BUCKET, architectureStep.output)
        .then((data) => setArchitectureData(data))
        .catch((e) => setError(e.message || 'Failed to load architecture diagram'))
        .finally(() => setLoading(false));
    } else {
      setArchitectureData(null);
      setLoading(false);
      setError('');
    }
  }, [results]);

  const downloadDiagram = async () => {
    if (!architectureData || !architectureData.architecture_diagram) return;

    const diagram = architectureData.architecture_diagram;
    if (diagram.diagram && diagram.diagram.mermaid_code) {
      // Create a text file with the mermaid code
      const blob = new Blob([diagram.diagram.mermaid_code], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'architecture_diagram.mmd';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }
  };

  const renderArchitectureInfo = () => {
    if (!architectureData || !architectureData.architecture_diagram) return null;

    const proposal = architectureData.architecture_diagram.proposal;
    const diagram = architectureData.architecture_diagram.diagram;

    return (
      <div className="architecture-info">
        <h3>Architecture Overview</h3>
        
        {/* Project Info */}
        <div className="project-info">
          <h4>Project Details</h4>
          <div className="info-grid">
            <div className="info-item">
              <span className="label">Project Title:</span>
              <span className="value">{proposal.project_info.title}</span>
            </div>
            <div className="info-item">
              <span className="label">Customer:</span>
              <span className="value">{proposal.project_info.customer}</span>
            </div>
            <div className="info-item">
              <span className="label">Generated:</span>
              <span className="value">{new Date(proposal.project_info.generated_at).toLocaleString()}</span>
            </div>
          </div>
        </div>

        {/* Recommended Services */}
        <div className="services-section">
          <h4>Recommended AWS Services</h4>
          <div className="services-grid">
            {proposal.architecture.recommended_services.map((service, index) => (
              <div key={index} className="service-badge">
                {service}
              </div>
            ))}
          </div>
        </div>

        {/* Architecture Explanation */}
        <div className="explanation-section">
          <h4>Architecture Explanation</h4>
          <p className="explanation-text">{proposal.architecture.explanation}</p>
        </div>

        {/* Mermaid Diagram */}
        {diagram && diagram.mermaid_code && (
          <div className="diagram-section">
            <h4>Architecture Diagram</h4>
            <div className="diagram-container">
              <pre className="mermaid-code">{diagram.mermaid_code}</pre>
            </div>
            <div className="diagram-actions">
              <button 
                className="download-btn"
                onClick={downloadDiagram}
                title="Download Mermaid diagram code"
              >
                📥 Download Diagram Code
              </button>
              <div className="diagram-note">
                <small>
                  💡 Copy the diagram code above and paste it into a Mermaid editor (like <a href="https://mermaid.live" target="_blank" rel="noopener noreferrer">mermaid.live</a>) to visualize the architecture
                </small>
              </div>
            </div>
          </div>
        )}

        {/* Implementation Notes */}
        {proposal.implementation_notes && proposal.implementation_notes.length > 0 && (
          <div className="implementation-section">
            <h4>Implementation Notes</h4>
            <ul className="implementation-list">
              {proposal.implementation_notes.map((note, index) => (
                <li key={index} className="implementation-item">
                  {note}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    );
  };

  if (loading) {
    return (
      <div className="architecture-diagram-container">
        <div className="section-header">
          <h2>🏗️ Architecture Diagram</h2>
        </div>
        <div className="loading-state">
          <div className="spinner"></div>
          <p>Loading architecture diagram...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="architecture-diagram-container">
        <div className="section-header">
          <h2>🏗️ Architecture Diagram</h2>
        </div>
        <div className="error-state">
          <p>❌ {error}</p>
        </div>
      </div>
    );
  }

  if (!architectureData) {
    return (
      <div className="architecture-diagram-container">
        <div className="section-header">
          <h2>🏗️ Architecture Diagram</h2>
        </div>
        <div className="no-data-state">
          <p>No architecture diagram data available</p>
        </div>
      </div>
    );
  }

  return (
    <div className="architecture-diagram-container">
      <div className="section-header">
        <h2>🏗️ Architecture Diagram</h2>
      </div>
      {renderArchitectureInfo()}
    </div>
  );
}

export default ArchitectureDiagram;
