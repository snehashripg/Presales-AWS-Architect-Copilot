import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { processRFP, getS3FileUrl, fetchS3Json, S3_OUTPUT_BUCKET, getPresignedS3Url, findUserArchitectures, findUserPricing, findUserSOW, findUserParsed, getRandomArchitectureDiagram, getArchitectureDiagramUrl } from '../services/awsService';
import './Dashboard.css';

function Dashboard({ user, onLogout, presetResults, hideUploader }) {
  const navigate = useNavigate();
  const [selectedFile, setSelectedFile] = useState(null);
  const [processing, setProcessing] = useState(false);
  const [progress, setProgress] = useState({ step: '', message: '', progress: 0 });
  const [results, setResults] = useState(presetResults || null);
  const [error, setError] = useState('');
  const [sowKey, setSowKey] = useState('');
  const [sowFilename, setSowFilename] = useState('');
  const [pricingData, setPricingData] = useState(null);
  const [pricingLoading, setPricingLoading] = useState(false);
  const [pricingError, setPricingError] = useState('');
  const [architectureKey, setArchitectureKey] = useState('');
  const [architectureFilename, setArchitectureFilename] = useState('');
  const [architectureLoading, setArchitectureLoading] = useState(false);
  const [architectureError, setArchitectureError] = useState('');
  const [galleryDiagram, setGalleryDiagram] = useState(null);
  const [galleryLoading, setGalleryLoading] = useState(false);
  const [imageModalOpen, setImageModalOpen] = useState(false);
  const [imageZoom, setImageZoom] = useState(100);

  // Load latest user files on component mount
  useEffect(() => {
    const loadLatestFiles = async () => {
      if (!user?.email) return;

      try {
        // Load latest architecture
        console.log('[DASHBOARD] Loading architecture for user:', user.email);
        const archFile = await findUserArchitectures(user.email);
        if (archFile) {
          console.log('[DASHBOARD] Found architecture file:', archFile.Key);
          setArchitectureKey(archFile.Key);
          setArchitectureFilename(archFile.Key.split('/').pop());
        } else {
          console.log('[DASHBOARD] No architecture file found for user:', user.email);
        }

        // Load latest pricing
        const pricingFile = await findUserPricing(user.email);
        if (pricingFile) {
          try {
            const pricingData = await fetchS3Json(S3_OUTPUT_BUCKET, pricingFile.Key);
            setPricingData(pricingData);
          } catch (e) {
            console.error('Error loading pricing data:', e);
          }
        }

        // Load latest SOW
        const sowFile = await findUserSOW(user.email);
        if (sowFile) {
          setSowKey(sowFile.Key);
          setSowFilename(sowFile.Key.split('/').pop());
        }
      } catch (e) {
        console.error('Error loading latest files:', e);
      }
    };

    const loadGalleryDiagram = async () => {
      try {
        setGalleryLoading(true);
        const diagram = getRandomArchitectureDiagram();
        const diagramUrl = await getArchitectureDiagramUrl(diagram.key);
        setGalleryDiagram({
          ...diagram,
          presignedUrl: diagramUrl
        });
      } catch (e) {
        console.error('Error loading gallery diagram:', e);
      } finally {
        setGalleryLoading(false);
      }
    };

    loadLatestFiles();
    loadGalleryDiagram();
  }, [user]);

  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (file) {
      // Validate file type
      const validTypes = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'];
      if (!validTypes.includes(file.type)) {
        setError('Please select a PDF or DOCX file');
        return;
      }
      setSelectedFile(file);
      setError('');
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      setError('Please select a file first');
      return;
    }

    setProcessing(true);
    setError('');
    setResults(null);

    try {
      const result = await processRFP(selectedFile, user.email, (progressInfo) => {
        setProgress(progressInfo);
      });

      // Normalize Lambda proxy-style responses where body can be a JSON string
      let processing = result.processingResult;
      if (processing && typeof processing.body === 'string') {
        try {
          processing = { ...processing, body: JSON.parse(processing.body) };
        } catch (e) {
          // ignore parse error; leave as-is
        }
      }
      setResults(processing);
      try {
        localStorage.setItem('rfx_results', JSON.stringify(processing));
      } catch (_) {}
      // Navigate to Clarifications page first
      navigate('/clarifications', { state: { results: processing } });
      setSelectedFile(null);
    } catch (err) {
      setError(err.message || 'Failed to process RFP');
    } finally {
      setProcessing(false);
      setProgress({ step: '', message: '', progress: 0 });
    }
  };

  const formatJSON = (data) => {
    return JSON.stringify(data, null, 2);
  };

  const downloadFile = (url, filename) => {
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.style.display = 'none';
    // Force download attribute
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // Image modal functions
  const openImageModal = () => {
    setImageModalOpen(true);
    setImageZoom(100);
  };

  const closeImageModal = () => {
    setImageModalOpen(false);
    setImageZoom(100);
  };

  const zoomIn = () => {
    setImageZoom(prev => Math.min(prev + 25, 300));
  };

  const zoomOut = () => {
    setImageZoom(prev => Math.max(prev - 25, 25));
  };

  const resetZoom = () => {
    setImageZoom(100);
  };

  // Detect SOW and Pricing outputs once results are available
  useEffect(() => {
    if (!results) {
      setSowKey('');
      setSowFilename('');
      setPricingData(null);
      setPricingError('');
      setPricingLoading(false);
      setArchitectureKey('');
      setArchitectureFilename('');
      setArchitectureLoading(false);
      setArchitectureError('');
      return;
    }

    const steps = results.body?.steps || results.steps || [];
    if (!Array.isArray(steps)) return;

    // Heuristics to detect SOW document
    const sowStep = steps.find((s) => {
      const name = (s.step || '').toLowerCase();
      const out = (s.output || '').toLowerCase();
      const isDoc = out.endsWith('.docx') || out.endsWith('.pdf');
      return isDoc && (name.includes('sow') || name.includes('statement of work') || out.includes('sow'));
    }) || steps.find((s) => {
      const out = (s.output || '').toLowerCase();
      return out && (out.endsWith('.docx') || out.endsWith('.pdf'));
    });

    if (sowStep && sowStep.output) {
      setSowKey(sowStep.output);
      setSowFilename(sowStep.output.split('/').pop());
    } else {
      setSowKey('');
      setSowFilename('');
    }

    // Heuristics to detect pricing JSON
    const pricingStep = steps.find((s) => {
      const name = (s.step || '').toLowerCase();
      const out = (s.output || '').toLowerCase();
      const looksJson = out.endsWith('.json');
      const mentionsPricing = name.includes('pricing') || out.includes('pricing') || out.includes('price');
      return looksJson && mentionsPricing;
    }) || steps.find((s) => {
      const out = (s.output || '').toLowerCase();
      return out && out.endsWith('.json');
    });

    if (pricingStep && pricingStep.output) {
      setPricingLoading(true);
      setPricingError('');
      fetchS3Json(S3_OUTPUT_BUCKET, pricingStep.output)
        .then((data) => setPricingData(data))
        .catch((e) => setPricingError(e.message || 'Failed to load pricing data'))
        .finally(() => setPricingLoading(false));
    } else {
      setPricingData(null);
      setPricingLoading(false);
      setPricingError('');
    }

    // Detect Architecture Diagram outputs
    const architectureStep = steps.find((s) => {
      const name = (s.step || '').toLowerCase();
      const out = (s.output || '').toLowerCase();
      const isPng = out.endsWith('.png');
      const mentionsArchitecture = name.includes('architecture') || name.includes('diagram') || out.includes('architecture') || out.includes('diagram');
      return isPng && mentionsArchitecture;
    });

    if (architectureStep && architectureStep.output) {
      setArchitectureKey(architectureStep.output);
      setArchitectureFilename(architectureStep.output.split('/').pop());
      setArchitectureLoading(false);
      setArchitectureError('');
    } else {
      setArchitectureKey('');
      setArchitectureFilename('');
      setArchitectureLoading(false);
      setArchitectureError('');
    }
  }, [results]);

  const renderPricingTable = (data) => {
    if (!data) return null;

    // Normalize various possible pricing shapes
    // 1) Nice view for pricing_check structure
    if (data?.pricing_check) {
      const pc = data.pricing_check || {};
      const ecr = pc.estimated_cost_range || {};
      const breakdown = pc.breakdown || {};
      const feasibility = pc.feasibility || {};
      const recommendations = Array.isArray(pc.funding_recommendations) ? pc.funding_recommendations : [];

      const toCurrency = (value, currency) => {
        const num = typeof value === 'string' ? Number(value) : value;
        try {
          return new Intl.NumberFormat(undefined, { style: 'currency', currency: currency || 'USD' }).format(num || 0);
        } catch (e) {
          return `${currency || 'USD'} ${Number(num || 0).toFixed(2)}`;
        }
      };

      const currency = ecr.currency || data?.currency || 'USD';

      const breakdownLabels = {
        infra_monthly: 'Infra Monthly',
        migration_per_app_total: 'Migration (per app total)',
        data_migration_total: 'Data Migration Total',
        pm_and_testing: 'PM & Testing',
        contingency: 'Contingency',
        duration_months: 'Duration (months)'
      };

      const breakdownRows = Object.keys(breakdownLabels)
        .filter((k) => breakdown[k] !== undefined)
        .map((key) => {
          const label = breakdownLabels[key];
          const val = breakdown[key];
          const isMonths = key === 'duration_months';
          return { label, value: isMonths ? `${val}` : toCurrency(val, currency) };
        });

      const gapAbs = feasibility?.funding_gap_absolute;
      const gapPct = feasibility?.funding_gap_pct;
      const feasible = String(feasibility?.feasibility || '').toLowerCase() === 'feasible';

      return (
        <div>
          {/* Top summary */}
          <div className="summary-grid" style={{ marginBottom: 16 }}>
            {ecr?.low !== undefined && (
              <div className="summary-item">
                <span className="label">Estimated Low</span>
                <span className="value">{toCurrency(ecr.low, currency)}</span>
              </div>
            )}
            {ecr?.high !== undefined && (
              <div className="summary-item">
                <span className="label">Estimated High</span>
                <span className="value">{toCurrency(ecr.high, currency)}</span>
              </div>
            )}
            {breakdown?.duration_months !== undefined && (
              <div className="summary-item">
                <span className="label">Duration</span>
                <span className="value">{breakdown.duration_months} months</span>
              </div>
            )}
            <div className="summary-item">
              <span className="label">Feasibility</span>
              <span className={`value ${feasible ? 'status-success' : 'status-failed'}`}>{feasible ? 'Feasible' : (feasibility?.feasibility || 'Unknown')}</span>
            </div>
            {gapAbs !== undefined && (
              <div className="summary-item">
                <span className="label">Funding Gap</span>
                <span className="value">{toCurrency(gapAbs, currency)}{gapPct !== undefined ? ` (${gapPct}%)` : ''}</span>
              </div>
            )}
          </div>

          {/* Breakdown table */}
          {breakdownRows.length > 0 && (
            <div className="pricing-table-wrapper" style={{ marginTop: 8 }}>
              <table className="pricing-table">
                <thead>
                  <tr>
                    <th>Cost Component</th>
                    <th>Value</th>
                  </tr>
                </thead>
                <tbody>
                  {breakdownRows.map((r, i) => (
                    <tr key={i}>
                      <td>{r.label}</td>
                      <td>{r.value}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Funding Recommendations */}
          {recommendations.length > 0 && (
            <div style={{ marginTop: 16 }}>
              <h4 style={{ marginBottom: 8 }}>💸 Funding Recommendations</h4>
              <div className="summary-grid">
                {recommendations.map((rec, i) => (
                  <div key={i} className="summary-item">
                    <span className="label">{rec.type}</span>
                    <span className="value">{toCurrency(rec.amount, currency)}</span>
                    {rec.rationale && (
                      <small style={{ color: '#666' }}>{rec.rationale}</small>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Raw JSON fallback */}
          <details style={{ marginTop: 16 }}>
            <summary>View Raw Pricing JSON</summary>
            <pre className="json-viewer">{formatJSON(data)}</pre>
          </details>
        </div>
      );
    }

    // 2) Generic tabular view for array-like pricing
    const items = Array.isArray(data)
      ? data
      : Array.isArray(data?.items)
        ? data.items
        : Array.isArray(data?.lineItems)
          ? data.lineItems
          : Array.isArray(data?.pricing)
            ? data.pricing
            : null;

    if (!items) {
      // Fallback to raw JSON view if shape is unknown
      return (
        <details>
          <summary>View Raw Pricing JSON</summary>
          <pre className="json-viewer">{formatJSON(data)}</pre>
        </details>
      );
    }

    const toCurrency = (value, currency) => {
      const num = typeof value === 'string' ? Number(value) : value;
      try {
        return new Intl.NumberFormat(undefined, { style: 'currency', currency: currency || 'USD' }).format(num || 0);
      } catch (e) {
        return `${currency || 'USD'} ${Number(num || 0).toFixed(2)}`;
      }
    };

    const currency = data?.currency || items?.[0]?.currency || 'USD';
    const rows = items.map((it, idx) => {
      const description = it.description || it.item || it.name || `Item ${idx + 1}`;
      const quantity = it.quantity ?? it.qty ?? 1;
      const unitPrice = it.unitPrice ?? it.pricePerUnit ?? it.unit_rate ?? it.rate ?? 0;
      const total = it.total ?? it.extendedPrice ?? it.amount ?? (Number(quantity) * Number(unitPrice));
      return { description, quantity, unitPrice, total };
    });

    const grandTotal = rows.reduce((acc, r) => acc + Number(r.total || 0), 0);

    return (
      <div className="pricing-table-wrapper">
        <table className="pricing-table">
          <thead>
            <tr>
              <th>Description</th>
              <th>Qty</th>
              <th>Unit Price</th>
              <th>Total</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i}>
                <td>{r.description}</td>
                <td>{r.quantity}</td>
                <td>{toCurrency(r.unitPrice, currency)}</td>
                <td>{toCurrency(r.total, currency)}</td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr>
              <td colSpan={3} className="grand-total-label">Grand Total</td>
              <td className="grand-total-value">{toCurrency(grandTotal, currency)}</td>
            </tr>
          </tfoot>
        </table>
      </div>
    );
  };

  return (
    <div className="dashboard-container">
      {/* Navigation Bar */}
      <nav className="navbar">
        <div className="navbar-brand">
          <h2>RFx Agent Dashboard</h2>
        </div>
        <div className="navbar-menu">
          <button className="nav-item active" onClick={() => navigate('/dashboard')}>
            Dashboard
          </button>
          <button className="nav-item" onClick={() => navigate('/chat')}>
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

      {/* Main Content */}
      <div className="dashboard-content">
        <div className="container">
          {/* Upload Section */}
          {!hideUploader && (
          <div className="card upload-section">
            <h3>Upload RFP Document</h3>
            <p className="subtitle">Upload your RFP/RFx document to start automated processing</p>

            <div className="file-upload-area">
              <input
                type="file"
                id="file-input"
                accept=".pdf,.docx"
                onChange={handleFileSelect}
                disabled={processing}
                style={{ display: 'none' }}
              />
              <label htmlFor="file-input" className="file-upload-label">
                <div className="upload-icon"></div>
                <div className="upload-text">
                  {selectedFile ? (
                    <>
                      <strong>{selectedFile.name}</strong>
                      <small>{(selectedFile.size / 1024 / 1024).toFixed(2)} MB</small>
                    </>
                  ) : (
                    <>
                      <strong>Click to select file</strong>
                      <small>PDF or DOCX files only</small>
                    </>
                  )}
                </div>
              </label>

              {selectedFile && !processing && (
                <button className="btn btn-primary" onClick={handleUpload}>
                  Process RFP
                </button>
              )}
            </div>

            {error && <div className="error">{error}</div>}

            {/* Progress */}
            {processing && (
              <div className="progress-section">
                <div className="progress-info">
                  <strong>{progress.message}</strong>
                  <span>{progress.progress}%</span>
                </div>
                <div className="progress-bar">
                  <div className="progress-fill" style={{ width: `${progress.progress}%` }}></div>
                </div>
              </div>
            )}
          </div>
          )}

          {/* Results Section */}
          {results && (
            <div className="results-section">
              <h3>Processing Complete!</h3>
              
              {/* Summary */}
              <div className="card">
                <h4>Summary</h4>
                <div className="summary-grid">
                  <div className="summary-item">
                    <span className="label">Status:</span>
                    <span className={`value status-${results.body?.status || results.status}`}>
                      {results.body?.status || results.status || 'completed'}
                    </span>
                  </div>
                  <div className="summary-item">
                    <span className="label">Steps Completed:</span>
                    <span className="value">{results.body?.steps?.length || results.steps?.length || 4}</span>
                  </div>
                  <div className="summary-item">
                    <span className="label">Processing Time:</span>
                    <span className="value">
                      {(() => {
                        const totalTime = results.body?.total_time_seconds || results.total_time_seconds;
                        if (totalTime) {
                          return `${totalTime}s`;
                        }
                        // Calculate estimated time based on steps
                        const stepCount = results.body?.steps?.length || results.steps?.length || 4;
                        const estimatedTime = stepCount * 30; // 30 seconds per step
                        return `~${estimatedTime}s (estimated)`;
                      })()}
                    </span>
                  </div>
                </div>
              </div>

              {/* SOW Download */}
              {sowKey ? (
                <div className="card highlight-card sow-card">
                  <h4>Statement of Work</h4>
                  <div className="sow-row">
                    <div className="sow-info">
                      <strong>{sowFilename}</strong>
                      <small>Generated SOW is ready for download</small>
                    </div>
                    <button
                      className="btn btn-primary"
                      onClick={async () => {
                        try {
                          const url = await getPresignedS3Url(S3_OUTPUT_BUCKET, sowKey);
                          downloadFile(url, sowFilename || 'SOW');
                        } catch (e) {
                          setError(e.message || 'Failed to generate download link');
                        }
                      }}
                    >
                      Download SOW
                    </button>
                  </div>
                </div>
              ) : (
                <div className="card highlight-card sow-card">
                  <h4>Statement of Work</h4>
                  <div className="sow-row">
                    <div className="sow-info">
                      <strong>No SOW detected</strong>
                      <small>Check the downloads list below for any .docx or .pdf outputs.</small>
                    </div>
                  </div>
                </div>
              )}

              {/* Pricing View */}
              {(pricingLoading || pricingData || pricingError) && (
                <div className="card pricing-card">
                  <h4>Pricing Summary</h4>
                  {pricingLoading && <div className="loading">Loading pricing...</div>}
                  {pricingError && <div className="error">{pricingError}</div>}
                  {!pricingLoading && !pricingError && pricingData && (
                    <div className="pricing-content">
                      {renderPricingTable(pricingData)}
                    </div>
                  )}
                </div>
              )}


              {/* Processing Steps */}
              {(results.body?.steps || results.steps) && (
                <div className="card">
                  <h4>Processing Steps</h4>
                  <div className="steps-list">
                    {(results.body?.steps || results.steps).map((step, index) => (
                      <div key={index} className="step-item">
                        <div className="step-header">
                          <span className="step-number">{index + 1}</span>
                          <strong>{step.step}</strong>
                          <span className={`step-status status-${step.status}`}>
                            {step.status === 'success' ? 'Success' : 'Failed'}
                          </span>
                        </div>
                        {step.output && (
                          <div className="step-output">
                            <small>Output: {step.output}</small>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Download Files */}
              <div className="card">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                  <h4>Download Results</h4>
                  <button
                    className="btn btn-secondary btn-sm"
                    onClick={async () => {
                      try {
                        console.log('[DASHBOARD] Refreshing files for user:', user.email);
                        // Reload latest files
                        const archFile = await findUserArchitectures(user.email);
                        if (archFile) {
                          setArchitectureKey(archFile.Key);
                          setArchitectureFilename(archFile.Key.split('/').pop());
                        }

                        const pricingFile = await findUserPricing(user.email);
                        if (pricingFile) {
                          const pricingData = await fetchS3Json(S3_OUTPUT_BUCKET, pricingFile.Key);
                          setPricingData(pricingData);
                        }

                        const sowFile = await findUserSOW(user.email);
                        if (sowFile) {
                          setSowKey(sowFile.Key);
                          setSowFilename(sowFile.Key.split('/').pop());
                        }
                      } catch (e) {
                        console.error('Error refreshing files:', e);
                        setError('Failed to refresh files');
                      }
                    }}
                  >
                    🔄 Refresh Files
                  </button>
                </div>
                <div className="download-grid">
                  {/* Show files from processing results */}
                  {(results.body?.steps || results.steps)
                    ?.filter((step) => {
                      const name = (step.step || '').toLowerCase();
                      // Exclude RFx Parsing and Clarification from downloads
                      return step.output && !name.includes('parsing') && !name.includes('clarification');
                    })
                    .map((step, index) => (
                      <div key={index} className="download-item">
                        <div className="download-info">
                          <strong>{step.step}</strong>
                          <small>{step.output.split('/').pop()}</small>
                        </div>
                        <button
                          className="btn btn-download"
                          onClick={async () => {
                            try {
                              const url = await getPresignedS3Url(S3_OUTPUT_BUCKET, step.output);
                              const filename = step.output.split('/').pop();
                              downloadFile(url, filename);
                            } catch (e) {
                              setError(e.message || 'Failed to generate download link');
                            }
                          }}
                        >
                          📥 Download
                        </button>
                      </div>
                    ))}

                  {/* Show AWS Architecture JSON file if available */}
                  {architectureKey && (
                    <div className="download-item">
                      <div className="download-info">
                        <strong>AWS Architecture (JSON)</strong>
                        <small>{architectureFilename}</small>
                      </div>
                      <button
                        className="btn btn-download"
                        onClick={async () => {
                          try {
                            // Fetch the JSON content and create a blob for download
                            const response = await fetchS3Json(S3_OUTPUT_BUCKET, architectureKey);
                            const blob = new Blob([JSON.stringify(response, null, 2)], { 
                              type: 'application/json' 
                            });
                            const url = URL.createObjectURL(blob);
                            downloadFile(url, architectureFilename || 'aws_architecture.json');
                            // Clean up the object URL
                            setTimeout(() => URL.revokeObjectURL(url), 1000);
                          } catch (e) {
                            setError(e.message || 'Failed to download architecture file');
                          }
                        }}
                      >
                        📄 Download JSON
                      </button>
                    </div>
                  )}

                  {/* Show Pricing JSON file if available */}
                  {pricingData && (
                    <div className="download-item">
                      <div className="download-info">
                        <strong>Pricing Estimate (JSON)</strong>
                        <small>pricing_estimate.json</small>
                      </div>
                      <button
                        className="btn btn-download"
                        onClick={async () => {
                          try {
                            // Find the pricing file
                            const pricingFile = await findUserPricing(user.email);
                            if (pricingFile) {
                              // Fetch the JSON content and create a blob for download
                              const response = await fetchS3Json(S3_OUTPUT_BUCKET, pricingFile.Key);
                              const blob = new Blob([JSON.stringify(response, null, 2)], { 
                                type: 'application/json' 
                              });
                              const url = URL.createObjectURL(blob);
                              downloadFile(url, pricingFile.Key.split('/').pop());
                              // Clean up the object URL
                              setTimeout(() => URL.revokeObjectURL(url), 1000);
                            } else {
                              // Fallback: create a JSON blob from the pricing data
                              const blob = new Blob([JSON.stringify(pricingData, null, 2)], { 
                                type: 'application/json' 
                              });
                              const url = URL.createObjectURL(blob);
                              downloadFile(url, 'pricing_estimate.json');
                              // Clean up the object URL
                              setTimeout(() => URL.revokeObjectURL(url), 1000);
                            }
                          } catch (e) {
                            setError(e.message || 'Failed to download pricing file');
                          }
                        }}
                      >
                        💰 Download JSON
                      </button>
                    </div>
                  )}

                  {/* Show SOW file if available */}
                  {sowKey && (
                    <div className="download-item">
                      <div className="download-info">
                        <strong>Statement of Work (DOCX)</strong>
                        <small>{sowFilename}</small>
                      </div>
                      <button
                        className="btn btn-download"
                        onClick={async () => {
                          try {
                            const url = await getPresignedS3Url(S3_OUTPUT_BUCKET, sowKey);
                            downloadFile(url, sowFilename || 'SOW.docx');
                          } catch (e) {
                            setError(e.message || 'Failed to generate download link');
                          }
                        }}
                      >
                        📄 Download DOCX
                      </button>
                    </div>
                  )}
                </div>
              </div>

              {/* Architecture Gallery */}
              <div className="card">
                <h4>🏗️ Sample Architecture Diagrams</h4>
                <p className="gallery-description">
                  Explore sample AWS architecture diagrams generated by our system
                </p>
                {galleryLoading ? (
                  <div className="gallery-loading">
                    <div className="loading-spinner"></div>
                    <p>Loading architecture diagram...</p>
                  </div>
                ) : galleryDiagram ? (
                  <div className="gallery-content">
                    <div className="gallery-image-container">
                      <img 
                        src={galleryDiagram.presignedUrl} 
                        alt="Sample Architecture Diagram"
                        className="gallery-image clickable-image"
                        onClick={openImageModal}
                        onError={(e) => {
                          console.error('Error loading gallery image:', e);
                          e.target.style.display = 'none';
                        }}
                        title="Click to view full size"
                      />
                    </div>
                    <div className="gallery-info">
                      <h5>Sample Architecture</h5>
                      <p>This diagram was generated based on real RFP requirements and demonstrates our system's capability to create detailed AWS architecture visualizations.</p>
                      <button
                        className="btn btn-download btn-large"
                        onClick={() => {
                          const link = document.createElement('a');
                          link.href = galleryDiagram.presignedUrl;
                          link.download = 'sample_architecture_diagram.png';
                          link.click();
                        }}
                      >
                        📥 Download Sample Architecture
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="gallery-error">
                    <p>Unable to load sample architecture diagram</p>
                  </div>
                )}
              </div>

              {/* Raw JSON Response */}
              <div className="card">
                <h4>Detailed Response</h4>
                <details>
                  <summary>View Raw JSON</summary>
                  <pre className="json-viewer">{formatJSON(results)}</pre>
                </details>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Image Modal */}
      {imageModalOpen && galleryDiagram && (
        <div className="image-modal-overlay" onClick={closeImageModal}>
          <div className="image-modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="image-modal-header">
              <h3>Architecture Diagram - Full View</h3>
              <button className="modal-close-btn" onClick={closeImageModal}>
                ✕
              </button>
            </div>
            <div className="image-modal-body">
              <div className="image-container">
                <img 
                  src={galleryDiagram.presignedUrl} 
                  alt="Architecture Diagram Full View"
                  className="modal-image"
                  style={{ transform: `scale(${imageZoom / 100})` }}
                />
              </div>
            </div>
            <div className="image-modal-footer">
              <div className="zoom-controls">
                <button className="zoom-btn" onClick={zoomOut} disabled={imageZoom <= 25}>
                  🔍-
                </button>
                <span className="zoom-level">{imageZoom}%</span>
                <button className="zoom-btn" onClick={zoomIn} disabled={imageZoom >= 300}>
                  🔍+
                </button>
                <button className="zoom-btn" onClick={resetZoom}>
                  Reset
                </button>
              </div>
              <div className="modal-actions">
                <button 
                  className="btn btn-secondary"
                  onClick={() => {
                    const link = document.createElement('a');
                    link.href = galleryDiagram.presignedUrl;
                    link.download = 'architecture_diagram.png';
                    link.click();
                  }}
                >
                  📥 Download
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default Dashboard;

