import React, { useState, useEffect } from 'react';
import {
  Search, Shield, MapPin, Calendar,
  Moon, Sun, PlusCircle, CheckCircle, AlertCircle, ArrowRight,
  LogOut, LogIn, ExternalLink, RefreshCw, Box, Lock, Upload, Image as ImageIcon
} from 'lucide-react';
import { api, type User, type Location, type ItemReport, type MatchResponse, type Claim, type CustodyEvent } from './api';

export function App() {
  const [theme, setTheme] = useState<'light' | 'dark'>('light');
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [activeTab, setActiveTab] = useState<'browse' | 'lost' | 'found' | 'claims'>('browse');
  const [staffSubTab, setStaffSubTab] = useState<'register' | 'claims' | 'transfers'>('register');

  // Data states
  const [reports, setReports] = useState<ItemReport[]>([]);
  const [locations, setLocations] = useState<Location[]>([]);
  const [myClaims, setMyClaims] = useState<Claim[]>([]);
  const [staffClaimsList, setStaffClaimsList] = useState<Claim[]>([]);
  const [pendingTransfers, setPendingTransfers] = useState<CustodyEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [errorNotice, setErrorNotice] = useState<string | null>(null);
  const [successNotice, setSuccessNotice] = useState<string | null>(null);

  // Transfer modal
  const [transferModalReport, setTransferModalReport] = useState<ItemReport | null>(null);
  const [transferToLocation, setTransferToLocation] = useState('');
  const [transferNote, setTransferNote] = useState('');

  // Filters
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('');
  const [selectedType, setSelectedType] = useState('');
  const [selectedLocation, setSelectedLocation] = useState('');

  // Modals
  const [authModalOpen, setAuthModalOpen] = useState(false);
  const [matchesModalReport, setMatchesModalReport] = useState<ItemReport | null>(null);
  const [matchResults, setMatchResults] = useState<MatchResponse | null>(null);
  const [matchingLoading, setMatchingLoading] = useState(false);
  const [claimModalReport, setClaimModalReport] = useState<ItemReport | null>(null);
  const [claimStatement, setClaimStatement] = useState('');

  // Forms
  const [lostForm, setLostForm] = useState({
    title: '',
    category: 'ELECTRONICS',
    public_description: '',
    last_seen_location: '',
    last_seen_at: '',
    private_description: '',
    distinguishing_details: '',
  });

  const [foundForm, setFoundForm] = useState({
    title: '',
    category: 'ELECTRONICS',
    public_description: '',
    found_location: '',
    current_holding_location: '',
    found_at: '',
    private_description: '',
    distinguishing_details: '',
  });

  const [lostImage, setLostImage] = useState<File | null>(null);
  const [foundImage, setFoundImage] = useState<File | null>(null);

  // Auth Form
  const [authForm, setAuthForm] = useState({
    email: '',
    password: '',
    isRegister: false,
    display_name: '',
  });

  // Initialize theme
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);

  // Check auth & fetch initial data
  useEffect(() => {
    checkCurrentUser();
    loadLocations();
  }, []);

  useEffect(() => {
    loadReports();
  }, [searchQuery, selectedCategory, selectedType, selectedLocation]);

  useEffect(() => {
    if (activeTab === 'claims' && currentUser) {
      loadMyClaims();
    }
    if (activeTab === 'found' && currentUser) {
      loadStaffData();
    }
  }, [activeTab, currentUser]);

  const toggleTheme = () => {
    setTheme(prev => (prev === 'light' ? 'dark' : 'light'));
  };

  const checkCurrentUser = async () => {
    try {
      const res = await api.auth.me();
      setCurrentUser(res.user);
    } catch {
      setCurrentUser(null);
    }
  };

  const loadLocations = async () => {
    try {
      const data = await api.locations.list();
      setLocations(Array.isArray(data) ? data : []);
    } catch (err: unknown) {
      console.error(err);
      setLocations([]);
    }
  };

  const loadReports = async () => {
    setLoading(true);
    try {
      const params: Record<string, string> = {};
      if (searchQuery.trim()) params.q = searchQuery.trim();
      if (selectedCategory) params.category = selectedCategory;
      if (selectedType) params.report_type = selectedType;
      if (selectedLocation) params.location = selectedLocation;

      const data = await api.reports.list(params);
      if (Array.isArray(data)) {
        setReports(data);
      } else if (data && Array.isArray(data.results)) {
        setReports(data.results);
      } else {
        setReports([]);
      }
    } catch (err: unknown) {
      setErrorNotice(err instanceof Error ? err.message : 'Failed to load reports');
    } finally {
      setLoading(false);
    }
  };

  const loadMyClaims = async () => {
    try {
      const claims = await api.claims.myClaims();
      setMyClaims(Array.isArray(claims) ? claims : ((claims as unknown as { results: Claim[] })?.results || []));
    } catch (err: unknown) {
      setErrorNotice(err instanceof Error ? err.message : 'Failed to load claims');
      setMyClaims([]);
    }
  };

  const loadStaffData = async () => {
    try {
      const [claims, transfers] = await Promise.all([
        api.claims.staffClaims().catch(() => []),
        api.custody.pendingTransfers().catch(() => []),
      ]);
      setStaffClaimsList(Array.isArray(claims) ? claims : []);
      setPendingTransfers(Array.isArray(transfers) ? transfers : []);
    } catch (err: unknown) {
      console.error(err);
    }
  };

  const handleDecideClaim = async (claimId: string, decision: 'approve' | 'reject') => {
    const note = prompt(`Enter staff review note for ${decision}:`) || '';
    try {
      await api.claims.decide(claimId, decision, note);
      setSuccessNotice(`Claim successfully marked as ${decision.toUpperCase()}.`);
      loadStaffData();
    } catch (err: unknown) {
      setErrorNotice(err instanceof Error ? err.message : 'Action failed');
    }
  };

  const handleCompleteHandover = async (claimId: string) => {
    if (!confirm('Confirm that the physical item has been handed over to the claimant?')) return;
    try {
      await api.claims.completeHandover(claimId);
      setSuccessNotice('Handover recorded! Item marked as RETURNED in network custody.');
      loadStaffData();
      loadReports();
    } catch (err: unknown) {
      setErrorNotice(err instanceof Error ? err.message : 'Failed to complete handover');
    }
  };

  const handleAcceptTransfer = async (custodyId: string) => {
    try {
      await api.custody.acceptTransfer(custodyId);
      setSuccessNotice('Custody transfer accepted! Holding location updated.');
      loadStaffData();
      loadReports();
    } catch (err: unknown) {
      setErrorNotice(err instanceof Error ? err.message : 'Failed to accept transfer');
    }
  };

  const handleInitiateTransfer = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!transferModalReport || !transferToLocation) return;
    try {
      await api.custody.requestTransfer(transferModalReport.id, transferToLocation, transferNote);
      setSuccessNotice('Transfer requested! Waiting for destination staff acknowledgement.');
      setTransferModalReport(null);
      setTransferToLocation('');
      setTransferNote('');
      loadReports();
      loadStaffData();
    } catch (err: unknown) {
      setErrorNotice(err instanceof Error ? err.message : 'Failed to request transfer');
    }
  };

  const handleAuthSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorNotice(null);
    try {
      if (authForm.isRegister) {
        const res = await api.auth.register({
          email: authForm.email,
          password: authForm.password,
          display_name: authForm.display_name,
        });
        setCurrentUser(res.user);
        setSuccessNotice('Account registered and signed in!');
      } else {
        const res = await api.auth.login({
          email: authForm.email,
          password: authForm.password,
        });
        setCurrentUser(res.user);
        setSuccessNotice('Signed in successfully!');
      }
      setAuthModalOpen(false);
    } catch (err: unknown) {
      setErrorNotice(err instanceof Error ? err.message : 'Authentication failed');
    }
  };

  const handleLogout = async () => {
    try {
      await api.auth.logout();
      setCurrentUser(null);
      setSuccessNotice('Signed out.');
      if (activeTab === 'claims' || activeTab === 'found') {
        setActiveTab('browse');
      }
    } catch (err: unknown) {
      console.error(err);
    }
  };

  const handleCreateLost = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!currentUser) {
      setAuthModalOpen(true);
      return;
    }
    setErrorNotice(null);
    try {
      let distinguishingParsed = {};
      if (lostForm.distinguishing_details.trim()) {
        try {
          distinguishingParsed = JSON.parse(lostForm.distinguishing_details);
        } catch {
          distinguishingParsed = { note: lostForm.distinguishing_details };
        }
      }

      const report = await api.reports.createLost({
        title: lostForm.title,
        category: lostForm.category,
        public_description: lostForm.public_description,
        last_seen_location: lostForm.last_seen_location || undefined,
        last_seen_at: lostForm.last_seen_at ? new Date(lostForm.last_seen_at).toISOString() : undefined,
        private_description: lostForm.private_description,
        distinguishing_details: distinguishingParsed,
      });

      if (lostImage) {
        try {
          await api.reports.uploadImage(report.id, lostImage);
        } catch (imgErr) {
          console.error('Image upload failed:', imgErr);
        }
      }

      setSuccessNotice('Lost item reported! Analyzing database for matches...');
      setLostForm({
        title: '',
        category: 'ELECTRONICS',
        public_description: '',
        last_seen_location: '',
        last_seen_at: '',
        private_description: '',
        distinguishing_details: '',
      });
      setLostImage(null);
      loadReports();
      openMatchesModal(report);
    } catch (err: unknown) {
      setErrorNotice(err instanceof Error ? err.message : 'Failed to submit report');
    }
  };

  const handleCreateFound = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorNotice(null);
    try {
      let distinguishingParsed = {};
      if (foundForm.distinguishing_details.trim()) {
        try {
          distinguishingParsed = JSON.parse(foundForm.distinguishing_details);
        } catch {
          distinguishingParsed = { note: foundForm.distinguishing_details };
        }
      }

      const report = await api.reports.createFound({
        title: foundForm.title,
        category: foundForm.category,
        public_description: foundForm.public_description,
        found_location: foundForm.found_location || undefined,
        current_holding_location: foundForm.current_holding_location || undefined,
        found_at: foundForm.found_at ? new Date(foundForm.found_at).toISOString() : undefined,
        private_description: foundForm.private_description,
        distinguishing_details: distinguishingParsed,
      });

      if (foundImage) {
        try {
          await api.reports.uploadImage(report.id, foundImage);
        } catch (imgErr) {
          console.error('Image upload failed:', imgErr);
        }
      }

      setSuccessNotice('Found item registered and indexed in custody records.');
      setFoundForm({
        title: '',
        category: 'ELECTRONICS',
        public_description: '',
        found_location: '',
        current_holding_location: '',
        found_at: '',
        private_description: '',
        distinguishing_details: '',
      });
      setFoundImage(null);
      loadReports();
      openMatchesModal(report);
    } catch (err: unknown) {
      setErrorNotice(err instanceof Error ? err.message : 'Failed to register found item');
    }
  };

  const openMatchesModal = async (report: ItemReport) => {
    setMatchesModalReport(report);
    setMatchingLoading(true);
    setMatchResults(null);
    try {
      const data = await api.matching.getMatches(report.id);
      setMatchResults(data);
    } catch (err: unknown) {
      console.error(err);
    } finally {
      setMatchingLoading(false);
    }
  };

  const handleSendFeedback = async (candidateId: string, feedback: string) => {
    if (!matchesModalReport) return;
    try {
      await api.matching.sendFeedback(matchesModalReport.id, candidateId, feedback);
      setSuccessNotice(`Feedback marked as ${feedback}.`);
    } catch (err: unknown) {
      setErrorNotice(err instanceof Error ? err.message : 'Could not submit feedback');
    }
  };

  const handleClaimSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!claimModalReport) return;
    if (!currentUser) {
      setAuthModalOpen(true);
      return;
    }
    setErrorNotice(null);
    try {
      await api.claims.create(claimModalReport.id, claimStatement);
      setSuccessNotice('Claim submitted securely! Location staff will review your proof.');
      setClaimModalReport(null);
      setClaimStatement('');
      setActiveTab('claims');
      loadMyClaims();
    } catch (err: unknown) {
      setErrorNotice(err instanceof Error ? err.message : 'Claim submission failed');
    }
  };

  return (
    <div className="app-container">
      {/* Header */}
      <header className="app-header">
        <div className="header-top">
          <a href="#browse" className="brand" onClick={(e) => { e.preventDefault(); setActiveTab('browse'); }}>
            <Shield size={24} color="var(--accent-red)" />
            <span>The Unclaimed Things Network</span>
            <span className="brand-badge">PILOT</span>
          </a>

          <div className="header-actions">
            <button className="nav-btn" onClick={toggleTheme} aria-label="Toggle theme" style={{ padding: '0.4rem 0.6rem' }}>
              {theme === 'light' ? <Moon size={16} /> : <Sun size={16} />}
            </button>

            {currentUser ? (
              <div className="header-user-badge">
                <span className="header-user-name" title={currentUser.email}>{currentUser.display_name || currentUser.email}</span>
                <button className="btn btn-secondary" style={{ height: '36px', padding: '0 0.75rem', fontSize: '0.8rem' }} onClick={handleLogout}>
                  <LogOut size={14} /> Sign out
                </button>
              </div>
            ) : (
              <button className="btn btn-primary" style={{ height: '36px', fontSize: '0.85rem' }} onClick={() => setAuthModalOpen(true)}>
                <LogIn size={14} /> Sign in
              </button>
            )}
          </div>
        </div>

        <nav className="header-nav" aria-label="Main navigation">
          <button
            className={`nav-btn ${activeTab === 'browse' ? 'active' : ''}`}
            onClick={() => setActiveTab('browse')}
          >
            <Search size={16} /> Browse & Search
          </button>
          <button
            className={`nav-btn ${activeTab === 'lost' ? 'active' : ''}`}
            onClick={() => {
              if (!currentUser) setAuthModalOpen(true);
              else setActiveTab('lost');
            }}
          >
            <PlusCircle size={16} /> Report Lost Item
          </button>
          <button
            className={`nav-btn ${activeTab === 'found' ? 'active' : ''}`}
            onClick={() => {
              if (!currentUser) setAuthModalOpen(true);
              else setActiveTab('found');
            }}
          >
            <Box size={16} /> Staff Workspace
          </button>
          {currentUser && (
            <button
              className={`nav-btn ${activeTab === 'claims' ? 'active' : ''}`}
              onClick={() => setActiveTab('claims')}
            >
              <CheckCircle size={16} /> My Claims
            </button>
          )}
        </nav>
      </header>

      {/* Global Notices */}
      {errorNotice && (
        <div className="notice notice-error">
          <AlertCircle size={18} />
          <div style={{ flex: 1 }}>{errorNotice}</div>
          <button style={{ background: 'none', border: 'none', cursor: 'pointer' }} onClick={() => setErrorNotice(null)}>×</button>
        </div>
      )}
      {successNotice && (
        <div className="notice notice-info">
          <CheckCircle size={18} />
          <div style={{ flex: 1 }}>{successNotice}</div>
          <button style={{ background: 'none', border: 'none', cursor: 'pointer' }} onClick={() => setSuccessNotice(null)}>×</button>
        </div>
      )}

      {/* Main Content Area */}
      <main style={{ flex: 1 }}>
        {/* TAB 1: BROWSE & SEARCH */}
        {activeTab === 'browse' && (
          <div>
            <div className="search-bar-wrap">
              <div className="search-input-box">
                <Search size={18} className="search-icon" />
                <input
                  type="text"
                  className="form-input"
                  placeholder="Search belongings by keyword, description, or title..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
              </div>
              <button className="btn btn-secondary" onClick={loadReports}>
                <RefreshCw size={16} /> Refresh
              </button>
            </div>

            <div className="filters-row">
              <select
                className="form-select filter-select"
                value={selectedType}
                onChange={(e) => setSelectedType(e.target.value)}
              >
                <option value="">All Status Types</option>
                <option value="LOST">Lost Reports</option>
                <option value="FOUND">Found Items</option>
              </select>

              <select
                className="form-select filter-select"
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
              >
                <option value="">All Categories</option>
                <option value="ELECTRONICS">Electronics</option>
                <option value="BAG">Bags & Backpacks</option>
                <option value="KEYS">Keys</option>
                <option value="BOTTLE">Bottles & Flasks</option>
                <option value="DOCUMENT">Documents / Cards</option>
                <option value="CLOTHING">Clothing</option>
                <option value="ACCESSORY">Accessories</option>
                <option value="OTHER">Other</option>
              </select>

              <select
                className="form-select filter-select"
                value={selectedLocation}
                onChange={(e) => setSelectedLocation(e.target.value)}
              >
                <option value="">All Campus Locations</option>
                {(Array.isArray(locations) ? locations : []).map((loc) => (
                  <option key={loc.id} value={loc.id}>
                    {loc.name}
                  </option>
                ))}
              </select>
            </div>

            {loading ? (
              <div className="state-box">
                <RefreshCw size={24} className="animate-spin" />
                <p>Loading items from network...</p>
              </div>
            ) : reports.length === 0 ? (
              <div className="state-box">
                <Box size={32} />
                <p>No matching reports found.</p>
                <span style={{ fontSize: '0.85rem' }}>Try adjusting your search terms or filters.</span>
              </div>
            ) : (
              <div className="report-list">
                {reports.map((report) => {
                  const loc = report.current_holding_location || report.found_location || report.last_seen_location;
                  return (
                    <div key={report.id} className="card card-interactive report-item">
                      <div className="report-item-header">
                        <div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.35rem' }}>
                            <span className={`badge ${report.report_type === 'LOST' ? 'badge-lost' : 'badge-found'}`}>
                              {report.report_type}
                            </span>
                            <span className="badge badge-status">{report.category}</span>
                            <span className="badge badge-status">{report.status}</span>
                          </div>
                          <h3 style={{ fontSize: '1.1rem', fontWeight: 600 }}>{report.title}</h3>
                        </div>

                        <div className="report-actions">
                          <button
                            className="btn btn-secondary"
                            style={{ height: '36px', fontSize: '0.85rem' }}
                            onClick={() => openMatchesModal(report)}
                          >
                            <ExternalLink size={14} /> AI Matches
                          </button>
                          {currentUser?.is_staff && report.report_type === 'FOUND' && report.status === 'OPEN' && (
                            <button
                              className="btn btn-secondary"
                              style={{ height: '36px', fontSize: '0.85rem' }}
                              onClick={() => {
                                setTransferModalReport(report);
                                setTransferToLocation('');
                                setTransferNote('');
                              }}
                              title="Transfer physical custody to another location"
                            >
                              <Box size={14} /> Transfer
                            </button>
                          )}
                          {report.report_type === 'FOUND' && report.status === 'OPEN' && (
                            <button
                              className="btn btn-primary"
                              style={{ height: '36px', fontSize: '0.85rem' }}
                              onClick={() => {
                                if (!currentUser) setAuthModalOpen(true);
                                else setClaimModalReport(report);
                              }}
                            >
                              Claim this Item
                            </button>
                          )}
                        </div>
                      </div>

                      <p style={{ fontSize: '0.925rem', color: 'var(--text)' }}>
                        {report.public_description}
                      </p>

                      {report.images && report.images.length > 0 && (
                        <div style={{ display: 'flex', gap: '0.5rem', margin: '0.5rem 0', flexWrap: 'wrap' }}>
                          {report.images.map((img) => (
                            <img
                              key={img.id}
                              src={img.url}
                              alt={report.title}
                              style={{
                                width: '70px',
                                height: '70px',
                                objectFit: 'cover',
                                borderRadius: 'var(--radius)',
                                border: '1px solid var(--border)',
                              }}
                            />
                          ))}
                        </div>
                      )}

                      <div className="report-meta">
                        {loc && (
                          <div className="meta-item">
                            <MapPin size={14} />
                            <span>{loc.name}</span>
                          </div>
                        )}
                        <div className="meta-item">
                          <Calendar size={14} />
                          <span>Reported {new Date(report.created_at).toLocaleDateString()}</span>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* TAB 2: REPORT LOST ITEM */}
        {activeTab === 'lost' && (
          <div style={{ maxWidth: '680px', margin: '0 auto' }}>
            <div className="card">
              <h2 style={{ marginBottom: '0.5rem' }}>Report a Lost Item</h2>
              <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', marginBottom: '1.5rem' }}>
                Your public details will help campus locations identify candidates. Private verification details remain strictly isolated.
              </p>

              <form onSubmit={handleCreateLost}>
                <div className="form-group">
                  <label className="form-label">
                    <span>Item Title *</span>
                    <span className="label-scope">PUBLIC</span>
                  </label>
                  <input
                    type="text"
                    required
                    className="form-input"
                    placeholder="e.g. Matte blue HydroFlask water bottle"
                    value={lostForm.title}
                    onChange={(e) => setLostForm({ ...lostForm, title: e.target.value })}
                  />
                  <span className="form-help">A concise title summarizing your item.</span>
                </div>

                <div className="form-group">
                  <label className="form-label">
                    <span>Category *</span>
                    <span className="label-scope">PUBLIC</span>
                  </label>
                  <select
                    className="form-select"
                    value={lostForm.category}
                    onChange={(e) => setLostForm({ ...lostForm, category: e.target.value })}
                  >
                    <option value="ELECTRONICS">Electronics</option>
                    <option value="BAG">Bag / Backpack</option>
                    <option value="KEYS">Keys</option>
                    <option value="BOTTLE">Bottle / Flask</option>
                    <option value="DOCUMENT">Document / ID Card</option>
                    <option value="CLOTHING">Clothing</option>
                    <option value="ACCESSORY">Accessory</option>
                    <option value="OTHER">Other</option>
                  </select>
                </div>

                <div className="form-group">
                  <label className="form-label">
                    <span>Public Description *</span>
                    <span className="label-scope">PUBLIC</span>
                  </label>
                  <textarea
                    required
                    className="form-textarea"
                    placeholder="Describe visible features: color, material, shape. Do NOT include secret marks or contact info."
                    value={lostForm.public_description}
                    onChange={(e) => setLostForm({ ...lostForm, public_description: e.target.value })}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">
                    <span>Last Seen Location</span>
                    <span className="label-scope">PUBLIC</span>
                  </label>
                  <select
                    className="form-select"
                    value={lostForm.last_seen_location}
                    onChange={(e) => setLostForm({ ...lostForm, last_seen_location: e.target.value })}
                  >
                    <option value="">Unknown / Not sure</option>
                    {(Array.isArray(locations) ? locations : []).map((loc) => (
                      <option key={loc.id} value={loc.id}>{loc.name}</option>
                    ))}
                  </select>
                </div>

                {/* Secure Boundary Section */}
                <div style={{ marginTop: '2rem', padding: '1rem', border: '1px solid var(--border)', borderRadius: 'var(--radius)', background: 'var(--surface-muted)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem', color: 'var(--accent-blue)', fontWeight: 600 }}>
                    <Lock size={16} /> Private Verification Vault (Never Public)
                  </div>
                  <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '1rem' }}>
                    Information entered below is NEVER visible on public listings or sent to external search APIs. It is only accessible to authorized location staff when reviewing a match.
                  </p>

                  <div className="form-group">
                    <label className="form-label">
                      <span>Private Description & Hidden Markings</span>
                      <span className="label-scope" style={{ color: 'var(--accent-blue)' }}>ENCRYPTED / PRIVATE</span>
                    </label>
                    <textarea
                      className="form-textarea"
                      placeholder="e.g. Small scratch near bottom, specific sticker on lid, initials engraved..."
                      value={lostForm.private_description}
                      onChange={(e) => setLostForm({ ...lostForm, private_description: e.target.value })}
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label">
                      <span>Serial Numbers / Specific Identifiers (Optional)</span>
                      <span className="label-scope" style={{ color: 'var(--accent-blue)' }}>ENCRYPTED / PRIVATE</span>
                    </label>
                    <input
                      type="text"
                      className="form-input"
                      placeholder="e.g. Serial # or ID card digits"
                      value={lostForm.distinguishing_details}
                      onChange={(e) => setLostForm({ ...lostForm, distinguishing_details: e.target.value })}
                    />
                  </div>
                </div>

                <div className="form-group" style={{ marginTop: '1.25rem' }}>
                  <label className="form-label">
                    <span style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}><Upload size={14} /> Attach Photo (Optional)</span>
                    <span className="label-scope">EXIF-PURGED</span>
                  </label>
                  <input
                    type="file"
                    accept="image/png,image/jpeg,image/webp"
                    className="form-input"
                    onChange={(e) => {
                      if (e.target.files && e.target.files[0]) {
                        setLostImage(e.target.files[0]);
                      }
                    }}
                  />
                  <span className="form-help">Max 5MB (JPEG, PNG, WEBP). Location metadata and camera serials are stripped automatically.</span>
                </div>

                <div style={{ marginTop: '1.5rem', display: 'flex', justifyContent: 'flex-end', gap: '0.75rem' }}>
                  <button type="button" className="btn btn-secondary" onClick={() => setActiveTab('browse')}>
                    Cancel
                  </button>
                  <button type="submit" className="btn btn-primary">
                    Submit Report & Find Matches <ArrowRight size={16} />
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* TAB 3: STAFF WORKSPACE */}
        {activeTab === 'found' && (
          <div>
            <div className="staff-header">
              <div>
                <h2>Staff Custody & Claims Workspace</h2>
                <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                  Manage item intake, verify ownership claims, and handle multi-location transfers.
                </span>
              </div>
              <div className="staff-subtabs">
                <button
                  className={`btn ${staffSubTab === 'register' ? 'btn-primary' : 'btn-secondary'}`}
                  style={{ height: '36px', fontSize: '0.85rem' }}
                  onClick={() => setStaffSubTab('register')}
                >
                  <PlusCircle size={14} /> Register Found Item
                </button>
                <button
                  className={`btn ${staffSubTab === 'claims' ? 'btn-primary' : 'btn-secondary'}`}
                  style={{ height: '36px', fontSize: '0.85rem' }}
                  onClick={() => setStaffSubTab('claims')}
                >
                  <Shield size={14} /> Review Claims ({staffClaimsList.filter(c => c.status === 'PENDING').length})
                </button>
                <button
                  className={`btn ${staffSubTab === 'transfers' ? 'btn-primary' : 'btn-secondary'}`}
                  style={{ height: '36px', fontSize: '0.85rem' }}
                  onClick={() => setStaffSubTab('transfers')}
                >
                  <Box size={14} /> Transfers ({pendingTransfers.length})
                </button>
              </div>
            </div>

            {/* SUB-TAB 1: REGISTER FOUND ITEM */}
            {staffSubTab === 'register' && (
              <div style={{ maxWidth: '680px', margin: '0 auto' }}>
                <div className="card">
                  <h3 style={{ marginBottom: '0.5rem' }}>Register Found Belonging</h3>
                  <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginBottom: '1.5rem' }}>
                    Record newly received belongings. Private features will be encrypted and hidden from public search.
                  </p>

                  <form onSubmit={handleCreateFound}>
                    <div className="form-group">
                      <label className="form-label">
                        <span>Item Title *</span>
                        <span className="label-scope">PUBLIC</span>
                      </label>
                      <input
                        type="text"
                        required
                        className="form-input"
                        placeholder="e.g. Dark wireless headphone case"
                        value={foundForm.title}
                        onChange={(e) => setFoundForm({ ...foundForm, title: e.target.value })}
                      />
                    </div>

                    <div className="form-group">
                      <label className="form-label">
                        <span>Category *</span>
                        <span className="label-scope">PUBLIC</span>
                      </label>
                      <select
                        className="form-select"
                        value={foundForm.category}
                        onChange={(e) => setFoundForm({ ...foundForm, category: e.target.value })}
                      >
                        <option value="ELECTRONICS">Electronics</option>
                        <option value="BAG">Bag / Backpack</option>
                        <option value="KEYS">Keys</option>
                        <option value="BOTTLE">Bottle / Flask</option>
                        <option value="DOCUMENT">Document / ID Card</option>
                        <option value="CLOTHING">Clothing</option>
                        <option value="ACCESSORY">Accessory</option>
                        <option value="OTHER">Other</option>
                      </select>
                    </div>

                    <div className="form-group">
                      <label className="form-label">
                        <span>Public Description *</span>
                        <span className="label-scope">PUBLIC</span>
                      </label>
                      <textarea
                        required
                        className="form-textarea"
                        placeholder="General appearance for owner recognition. Keep serial numbers out of this field."
                        value={foundForm.public_description}
                        onChange={(e) => setFoundForm({ ...foundForm, public_description: e.target.value })}
                      />
                    </div>

                    <div className="form-grid-2">
                      <div className="form-group">
                        <label className="form-label">Found Location</label>
                        <select
                          className="form-select"
                          value={foundForm.found_location}
                          onChange={(e) => setFoundForm({ ...foundForm, found_location: e.target.value })}
                        >
                          <option value="">Select Location</option>
                          {(Array.isArray(locations) ? locations : []).map((loc) => (
                            <option key={loc.id} value={loc.id}>{loc.name}</option>
                          ))}
                        </select>
                      </div>

                      <div className="form-group">
                        <label className="form-label">Holding Location</label>
                        <select
                          className="form-select"
                          value={foundForm.current_holding_location}
                          onChange={(e) => setFoundForm({ ...foundForm, current_holding_location: e.target.value })}
                        >
                          <option value="">Select Location</option>
                          {(Array.isArray(locations) ? locations : []).map((loc) => (
                            <option key={loc.id} value={loc.id}>{loc.name}</option>
                          ))}
                        </select>
                      </div>
                    </div>

                    <div style={{ marginTop: '1.5rem', padding: '1rem', border: '1px solid var(--border)', borderRadius: 'var(--radius)', background: 'var(--surface-muted)' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem', color: 'var(--accent-blue)', fontWeight: 600 }}>
                        <Lock size={16} /> Confidential Verification Details
                      </div>
                      <div className="form-group">
                        <label className="form-label">Distinguishing Attributes</label>
                        <textarea
                          className="form-textarea"
                          placeholder="e.g. Serial # or specific items inside a pouch used to test claimants."
                          value={foundForm.private_description}
                          onChange={(e) => setFoundForm({ ...foundForm, private_description: e.target.value })}
                        />
                      </div>
                    </div>

                    <div className="form-group" style={{ marginTop: '1.25rem' }}>
                      <label className="form-label">
                        <span style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}><ImageIcon size={14} /> Attach Item Photo (Optional)</span>
                        <span className="label-scope">EXIF-PURGED</span>
                      </label>
                      <input
                        type="file"
                        accept="image/png,image/jpeg,image/webp"
                        className="form-input"
                        onChange={(e) => {
                          if (e.target.files && e.target.files[0]) {
                            setFoundImage(e.target.files[0]);
                          }
                        }}
                      />
                      <span className="form-help">Max 5MB (JPEG, PNG, WEBP). Strips camera model and geolocation metadata before storing.</span>
                    </div>

                    <div style={{ marginTop: '1.5rem', display: 'flex', justifyContent: 'flex-end', gap: '0.75rem' }}>
                      <button type="button" className="btn btn-secondary" onClick={() => setActiveTab('browse')}>
                        Cancel
                      </button>
                      <button type="submit" className="btn btn-primary">
                        Register Found Item
                      </button>
                    </div>
                  </form>
                </div>
              </div>
            )}

            {/* SUB-TAB 2: CLAIMS REVIEW & HANDOVER */}
            {staffSubTab === 'claims' && (
              <div>
                {staffClaimsList.length === 0 ? (
                  <div className="state-box">
                    <CheckCircle size={32} />
                    <p>No claims waiting for review.</p>
                    <span style={{ fontSize: '0.85rem' }}>When claimants file ownership proofs on items held at your location, they appear here.</span>
                  </div>
                ) : (
                  <div className="report-list">
                    {staffClaimsList.map((claim) => (
                      <div key={claim.id} className="card">
                        <div className="report-item-header">
                          <div>
                            <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.35rem' }}>
                              <span className={`badge ${claim.status === 'APPROVED' ? 'badge-success' : claim.status === 'COMPLETED' ? 'badge-status' : 'badge-match'}`}>
                                {claim.status}
                              </span>
                            </div>
                            <h3>{claim.report_title}</h3>
                            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                              Claimant: <strong>{claim.claimant_email}</strong> • Filed: {new Date(claim.created_at).toLocaleDateString()}
                            </span>
                          </div>

                          <div className="report-actions">
                            {claim.status === 'PENDING' && (
                              <>
                                <button
                                  className="btn btn-primary"
                                  style={{ height: '34px', fontSize: '0.8rem' }}
                                  onClick={() => handleDecideClaim(claim.id, 'approve')}
                                >
                                  Approve Claim
                                </button>
                                <button
                                  className="btn btn-danger"
                                  style={{ height: '34px', fontSize: '0.8rem' }}
                                  onClick={() => handleDecideClaim(claim.id, 'reject')}
                                >
                                  Reject
                                </button>
                              </>
                            )}
                            {claim.status === 'APPROVED' && (
                              <button
                                className="btn btn-primary"
                                style={{ height: '34px', fontSize: '0.8rem', backgroundColor: 'var(--success)', borderColor: 'var(--success)' }}
                                onClick={() => handleCompleteHandover(claim.id)}
                              >
                                <CheckCircle size={14} /> Complete Handover
                              </button>
                            )}
                          </div>
                        </div>

                        <div style={{ marginTop: '0.85rem', padding: '0.75rem', background: 'var(--surface-muted)', borderRadius: 'var(--radius)' }}>
                          <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--accent-blue)', display: 'block', marginBottom: '0.25rem' }}>
                            CLAIMANT VERIFICATION STATEMENT:
                          </span>
                          <p style={{ fontSize: '0.9rem' }}>{claim.claimant_statement}</p>
                        </div>

                        {claim.review_note_private && (
                          <div style={{ marginTop: '0.5rem', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                            <strong>Staff Note:</strong> {claim.review_note_private}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* SUB-TAB 3: CUSTODY TRANSFERS */}
            {staffSubTab === 'transfers' && (
              <div>
                <h3 style={{ marginBottom: '1rem', fontSize: '1rem' }}>Pending Incoming Transfers</h3>
                {pendingTransfers.length === 0 ? (
                  <div className="state-box">
                    <Box size={32} />
                    <p>No incoming transfers waiting for acceptance.</p>
                    <span style={{ fontSize: '0.85rem' }}>Transfers initiated by other campus locations will appear here for acknowledgement.</span>
                  </div>
                ) : (
                  <div className="report-list">
                    {pendingTransfers.map((event) => (
                      <div key={event.id} className="card">
                        <div className="report-item-header">
                          <div>
                            <span className="badge badge-match" style={{ marginBottom: '0.35rem' }}>
                              TRANSFER REQUESTED
                            </span>
                            <h4>Transfer to {event.to_location_name || 'Your Location'}</h4>
                            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                              From: <strong>{event.from_location_name}</strong> • Initiated by: {event.actor_email}
                            </span>
                          </div>

                          <div className="report-actions">
                            <button
                              className="btn btn-primary"
                              style={{ height: '36px', fontSize: '0.85rem' }}
                              onClick={() => handleAcceptTransfer(event.id)}
                            >
                              <CheckCircle size={14} /> Accept & Take Custody
                            </button>
                          </div>
                        </div>
                        {event.note_private && (
                          <p style={{ fontSize: '0.85rem', marginTop: '0.5rem', color: 'var(--text-muted)' }}>
                            Note: {event.note_private}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                )}

                <div style={{ marginTop: '2rem' }}>
                  <h3 style={{ marginBottom: '1rem', fontSize: '1rem' }}>Active Found Belongings (Initiate Transfer)</h3>
                  {reports.filter(r => r.report_type === 'FOUND' && r.status === 'OPEN').length === 0 ? (
                    <div className="state-box">
                      <Box size={28} />
                      <p>No open found items currently in campus custody records.</p>
                    </div>
                  ) : (
                    <div className="report-list">
                      {reports.filter(r => r.report_type === 'FOUND' && r.status === 'OPEN').map((rep) => (
                        <div key={rep.id} className="card transfer-item-card">
                          <div>
                            <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.25rem' }}>
                              <span className="badge badge-found">{rep.category}</span>
                              <span className="badge badge-status">
                                At: {rep.current_holding_location?.name || 'Unassigned'}
                              </span>
                            </div>
                            <h4 style={{ fontSize: '1rem', fontWeight: 600 }}>{rep.title}</h4>
                            <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>{rep.public_description}</p>
                          </div>
                          <button
                            className="btn btn-secondary"
                            style={{ height: '34px', fontSize: '0.8rem' }}
                            onClick={() => {
                              setTransferModalReport(rep);
                              setTransferToLocation('');
                              setTransferNote('');
                            }}
                          >
                            <Box size={14} /> Request Transfer
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {/* TAB 4: MY CLAIMS */}
        {activeTab === 'claims' && (
          <div>
            <h2 style={{ marginBottom: '1rem' }}>My Ownership Claims</h2>
            {myClaims.length === 0 ? (
              <div className="state-box">
                <CheckCircle size={32} />
                <p>You have no active claims.</p>
                <span style={{ fontSize: '0.85rem' }}>If you discover your item in the feed, submit a claim with verification proof.</span>
              </div>
            ) : (
              <div className="report-list">
                {myClaims.map((claim) => (
                  <div key={claim.id} className="card">
                    <div className="report-item-header">
                      <div>
                        <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.35rem' }}>
                          <span className={`badge ${claim.status === 'APPROVED' ? 'badge-success' : 'badge-status'}`}>
                            {claim.status}
                          </span>
                        </div>
                        <h3>{claim.report_title}</h3>
                      </div>
                      <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                        Filed on {new Date(claim.created_at).toLocaleDateString()}
                      </span>
                    </div>

                    <div style={{ marginTop: '0.75rem', fontSize: '0.9rem' }}>
                      <strong>Your Statement:</strong> {claim.claimant_statement}
                    </div>

                    {claim.review_note_private && (
                      <div style={{ marginTop: '0.5rem', fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                        <strong>Staff Note:</strong> {claim.review_note_private}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </main>

      {/* MODAL 1: AI & KEYWORD MATCHES */}
      {matchesModalReport && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <div>
                <h3 style={{ fontSize: '1.15rem' }}>Possible Matches</h3>
                <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  For: <strong>{matchesModalReport.title}</strong>
                </span>
              </div>
              <button
                style={{ background: 'none', border: 'none', fontSize: '1.25rem', cursor: 'pointer', color: 'var(--text)' }}
                onClick={() => setMatchesModalReport(null)}
              >
                ×
              </button>
            </div>

            {matchingLoading ? (
              <div className="state-box">
                <RefreshCw size={24} className="animate-spin" />
                <p>Querying NVIDIA NIM vector index and keyword database...</p>
              </div>
            ) : matchResults && matchResults.matches.length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', display: 'flex', justifyContent: 'space-between' }}>
                  <span>Retrieval Pipeline: <strong>{matchResults.retrieval_mode.toUpperCase()}</strong></span>
                  <span>{matchResults.matches.length} candidates found</span>
                </div>

                {matchResults.matches.map((cand) => (
                  <div key={cand.candidate_report_id} className="card" style={{ padding: '0.85rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.35rem' }}>
                      <span className="badge badge-match">{cand.match_label}</span>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                        {new Date(cand.reported_at).toLocaleDateString()}
                      </span>
                    </div>

                    <h4 style={{ fontSize: '0.975rem', fontWeight: 600 }}>{cand.title}</h4>
                    <p style={{ fontSize: '0.85rem', color: 'var(--text)', margin: '0.35rem 0' }}>
                      {cand.public_description}
                    </p>

                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '0.5rem', fontSize: '0.8rem' }}>
                      <span style={{ color: 'var(--text-muted)' }}>
                        <MapPin size={12} style={{ display: 'inline', marginRight: '4px' }} />
                        {cand.safe_location_label}
                      </span>

                      <div style={{ display: 'flex', gap: '0.35rem' }}>
                        <button
                          className="btn btn-secondary"
                          style={{ height: '28px', padding: '0 0.5rem', fontSize: '0.75rem' }}
                          onClick={() => handleSendFeedback(cand.candidate_report_id, 'RELEVANT')}
                        >
                          Relevant
                        </button>
                        <button
                          className="btn btn-secondary"
                          style={{ height: '28px', padding: '0 0.5rem', fontSize: '0.75rem' }}
                          onClick={() => handleSendFeedback(cand.candidate_report_id, 'NOT_RELEVANT')}
                        >
                          Not Relevant
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="state-box">
                <Box size={24} />
                <p>No immediate candidates found.</p>
                <span style={{ fontSize: '0.8rem' }}>Our AI pipeline will continue evaluating newly registered items automatically.</span>
              </div>
            )}

            <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '1rem' }}>
              <button className="btn btn-secondary" onClick={() => setMatchesModalReport(null)}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL 2: CLAIM ITEM */}
      {claimModalReport && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h3>Claim Found Item</h3>
              <button
                style={{ background: 'none', border: 'none', fontSize: '1.25rem', cursor: 'pointer', color: 'var(--text)' }}
                onClick={() => setClaimModalReport(null)}
              >
                ×
              </button>
            </div>

            <form onSubmit={handleClaimSubmit}>
              <p style={{ fontSize: '0.875rem', marginBottom: '1rem' }}>
                You are submitting an ownership claim for: <strong>{claimModalReport.title}</strong>
              </p>

              <div className="notice notice-info" style={{ fontSize: '0.8rem' }}>
                <Lock size={16} />
                <span>
                  Your explanation is private and reviewed only by authorized campus staff. Provide distinguishing details that only the true owner would know.
                </span>
              </div>

              <div className="form-group">
                <label className="form-label">Proof of Ownership / Distinguishing Detail *</label>
                <textarea
                  required
                  className="form-textarea"
                  placeholder="Describe secret marks, contents, lock passcode pattern, or purchase receipts..."
                  value={claimStatement}
                  onChange={(e) => setClaimStatement(e.target.value)}
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '1rem' }}>
                <button type="button" className="btn btn-secondary" onClick={() => setClaimModalReport(null)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary">
                  Submit Claim
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 3: AUTH (SIGN IN / REGISTER) */}
      {authModalOpen && (
        <div className="modal-overlay">
          <div className="modal-content" style={{ maxWidth: '440px' }}>
            <div className="modal-header">
              <h3>{authForm.isRegister ? 'Create Pilot Account' : 'Sign in to UTN'}</h3>
              <button
                style={{ background: 'none', border: 'none', fontSize: '1.25rem', cursor: 'pointer', color: 'var(--text)' }}
                onClick={() => setAuthModalOpen(false)}
              >
                ×
              </button>
            </div>

            <form onSubmit={handleAuthSubmit}>
              {authForm.isRegister && (
                <div className="form-group">
                  <label className="form-label">Full Name</label>
                  <input
                    type="text"
                    required
                    className="form-input"
                    placeholder="e.g. Alice Sharma"
                    value={authForm.display_name}
                    onChange={(e) => setAuthForm({ ...authForm, display_name: e.target.value })}
                  />
                </div>
              )}

              <div className="form-group">
                <label className="form-label">Campus Email</label>
                <input
                  type="email"
                  required
                  className="form-input"
                  placeholder="name@campus.edu"
                  value={authForm.email}
                  onChange={(e) => setAuthForm({ ...authForm, email: e.target.value })}
                />
              </div>

              <div className="form-group">
                <label className="form-label">Password</label>
                <input
                  type="password"
                  required
                  className="form-input"
                  placeholder="••••••••"
                  value={authForm.password}
                  onChange={(e) => setAuthForm({ ...authForm, password: e.target.value })}
                />
              </div>

              {/* Quick test account buttons for pilot demo */}
              <div style={{ margin: '1rem 0', padding: '0.75rem', background: 'var(--surface-muted)', borderRadius: 'var(--radius)' }}>
                <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)' }}>QUICK PILOT LOGINS:</span>
                <div style={{ display: 'flex', gap: '0.35rem', marginTop: '0.35rem', flexWrap: 'wrap' }}>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    style={{ height: '28px', fontSize: '0.75rem', padding: '0 0.5rem' }}
                    onClick={() => setAuthForm({ ...authForm, email: 'student1@campus.edu', password: 'StudentPass123!' })}
                  >
                    Student (Alice)
                  </button>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    style={{ height: '28px', fontSize: '0.75rem', padding: '0 0.5rem' }}
                    onClick={() => setAuthForm({ ...authForm, email: 'library.staff@campus.edu', password: 'StaffPass123!' })}
                  >
                    Library Staff
                  </button>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    style={{ height: '28px', fontSize: '0.75rem', padding: '0 0.5rem' }}
                    onClick={() => setAuthForm({ ...authForm, email: 'admin@campus.edu', password: 'AdminPass123!' })}
                  >
                    Admin
                  </button>
                </div>
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '1rem' }}>
                <button
                  type="button"
                  className="btn btn-tertiary"
                  onClick={() => setAuthForm({ ...authForm, isRegister: !authForm.isRegister })}
                >
                  {authForm.isRegister ? 'Already have an account? Sign in' : 'New here? Register'}
                </button>
                <button type="submit" className="btn btn-primary">
                  {authForm.isRegister ? 'Register' : 'Sign in'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 4: TRANSFER ITEM */}
      {transferModalReport && (
        <div className="modal-overlay">
          <div className="modal-content" style={{ maxWidth: '480px' }}>
            <div className="modal-header">
              <h3>Transfer Item Custody</h3>
              <button
                style={{ background: 'none', border: 'none', fontSize: '1.25rem', cursor: 'pointer', color: 'var(--text)' }}
                onClick={() => setTransferModalReport(null)}
              >
                ×
              </button>
            </div>

            <form onSubmit={handleInitiateTransfer}>
              <p style={{ fontSize: '0.875rem', marginBottom: '1rem' }}>
                Initiate multi-location physical custody transfer for: <strong>{transferModalReport.title}</strong>
              </p>

              <div className="notice notice-info" style={{ fontSize: '0.8rem', marginBottom: '1rem' }}>
                <Box size={16} />
                <span>
                  The item remains marked at its current holding location until staff at the destination location accept and acknowledge physical receipt.
                </span>
              </div>

              <div className="form-group">
                <label className="form-label">Destination Campus Location *</label>
                <select
                  required
                  className="form-select"
                  value={transferToLocation}
                  onChange={(e) => setTransferToLocation(e.target.value)}
                >
                  <option value="">Select Destination Campus Location</option>
                  {(Array.isArray(locations) ? locations : [])
                    .filter((loc) => loc.id !== transferModalReport.current_holding_location?.id)
                    .map((loc) => (
                      <option key={loc.id} value={loc.id}>
                        {loc.name} ({loc.location_type})
                      </option>
                    ))}
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">Transfer Note / Tracking Reason</label>
                <textarea
                  className="form-textarea"
                  placeholder="e.g. Student requested retrieval at Security HQ; sending via campus dispatch"
                  value={transferNote}
                  onChange={(e) => setTransferNote(e.target.value)}
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '1rem' }}>
                <button type="button" className="btn btn-secondary" onClick={() => setTransferModalReport(null)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={!transferToLocation}>
                  Request Transfer
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
