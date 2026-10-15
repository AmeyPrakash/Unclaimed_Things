import React, { useState, useEffect } from 'react';
import {
  Search, Shield, MapPin, Calendar,
  Moon, Sun, PlusCircle, CheckCircle, AlertCircle, ArrowRight,
  LogOut, LogIn, ExternalLink, RefreshCw, Box, Lock, Upload, Image as ImageIcon,
  Activity, Users, FileText, Ban, Eye, Flag
} from 'lucide-react';
import {
  api,
  type User,
  type Location,
  type ItemReport,
  type MatchResponse,
  type Claim,
  type CustodyEvent,
  type AdminOverview,
  type AuditEventItem,
  type AdminReportItem,
  type AdminUserItem
} from './api';

export function App() {
  const [theme, setTheme] = useState<'light' | 'dark'>('light');
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [activeTab, setActiveTab] = useState<'browse' | 'lost' | 'found' | 'claims' | 'admin'>('browse');
  const [staffSubTab, setStaffSubTab] = useState<'register' | 'claims' | 'transfers'>('register');
  const [adminSubTab, setAdminSubTab] = useState<'overview' | 'audit' | 'moderation' | 'users'>('overview');

  // Admin Data states
  const [adminOverview, setAdminOverview] = useState<AdminOverview | null>(null);
  const [adminAuditEvents, setAdminAuditEvents] = useState<AuditEventItem[]>([]);
  const [adminReports, setAdminReports] = useState<AdminReportItem[]>([]);
  const [adminUsers, setAdminUsers] = useState<AdminUserItem[]>([]);
  const [adminLoading, setAdminLoading] = useState(false);
  const [adminAuditSearch, setAdminAuditSearch] = useState('');
  const [adminAuditActionFilter, setAdminAuditActionFilter] = useState('');
  const [adminReportVisibility, setAdminReportVisibility] = useState('');
  const [adminReportSearch, setAdminReportSearch] = useState('');
  const [adminUserSearch, setAdminUserSearch] = useState('');
  const [adminUserFilter, setAdminUserFilter] = useState('');
  const [modModalReport, setModModalReport] = useState<AdminReportItem | null>(null);
  const [modVisibility, setModVisibility] = useState<'ACTIVE' | 'HIDDEN' | 'REMOVED'>('HIDDEN');
  const [modReason, setModReason] = useState('');
  const [suspendModalUser, setSuspendModalUser] = useState<AdminUserItem | null>(null);
  const [suspendReason, setSuspendReason] = useState('');

  // Flag / Abuse states
  const [flagModalReport, setFlagModalReport] = useState<ItemReport | null>(null);
  const [flagReason, setFlagReason] = useState<string>('SPAM_OR_FRAUD');
  const [flagDetails, setFlagDetails] = useState<string>('');
  const [flagSubmitting, setFlagSubmitting] = useState<boolean>(false);
  const [adminReportFlaggedFilter, setAdminReportFlaggedFilter] = useState<boolean>(false);
  const [inspectFlagReport, setInspectFlagReport] = useState<AdminReportItem | null>(null);

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
    if (activeTab === 'admin' && currentUser && (currentUser.is_staff || currentUser.is_superuser)) {
      if (adminSubTab === 'overview') loadAdminOverview();
      if (adminSubTab === 'audit') loadAdminAuditEvents();
      if (adminSubTab === 'moderation') loadAdminReports();
      if (adminSubTab === 'users') loadAdminUsers();
    }
  }, [activeTab, adminSubTab, currentUser, adminAuditActionFilter, adminReportVisibility, adminUserFilter]);

  const loadAdminOverview = async () => {
    setAdminLoading(true);
    try {
      const data = await api.admin.overview();
      setAdminOverview(data);
    } catch (err: any) {
      setErrorNotice(err?.message || 'Failed to load system overview');
    } finally {
      setAdminLoading(false);
    }
  };

  const loadAdminAuditEvents = async () => {
    setAdminLoading(true);
    try {
      const params: Record<string, string> = {};
      if (adminAuditActionFilter) params.action = adminAuditActionFilter;
      if (adminAuditSearch.trim()) params.search = adminAuditSearch.trim();
      const res = await api.admin.auditEvents(params);
      const items = Array.isArray(res) ? res : res?.results || [];
      setAdminAuditEvents(items);
    } catch (err: any) {
      setErrorNotice(err?.message || 'Failed to load audit trail');
    } finally {
      setAdminLoading(false);
    }
  };

  const loadAdminReports = async () => {
    setAdminLoading(true);
    try {
      const params: Record<string, string> = {};
      if (adminReportVisibility) params.visibility = adminReportVisibility;
      if (adminReportSearch.trim()) params.search = adminReportSearch.trim();
      if (adminReportFlaggedFilter) params.flagged = 'true';
      const res = await api.admin.reports(params);
      const items = Array.isArray(res) ? res : res?.results || [];
      setAdminReports(items);
    } catch (err: any) {
      setErrorNotice(err?.message || 'Failed to load moderation reports');
    } finally {
      setAdminLoading(false);
    }
  };

  const handleFlagSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!flagModalReport) return;
    if (!currentUser) {
      setAuthModalOpen(true);
      return;
    }
    setFlagSubmitting(true);
    try {
      await api.reports.flag(flagModalReport.id, flagReason, flagDetails);
      setSuccessNotice('Listing reported! Thank you for helping keep the campus community safe.');
      setFlagModalReport(null);
      setFlagReason('SPAM_OR_FRAUD');
      setFlagDetails('');
    } catch (err: unknown) {
      setErrorNotice(err instanceof Error ? err.message : 'Failed to report listing');
    } finally {
      setFlagSubmitting(false);
    }
  };

  const loadAdminUsers = async () => {
    setAdminLoading(true);
    try {
      const params: Record<string, string> = {};
      if (adminUserFilter) params.is_active = adminUserFilter;
      if (adminUserSearch.trim()) params.search = adminUserSearch.trim();
      const res = await api.admin.users(params);
      const items = Array.isArray(res) ? res : res?.results || [];
      setAdminUsers(items);
    } catch (err: any) {
      setErrorNotice(err?.message || 'Failed to load users');
    } finally {
      setAdminLoading(false);
    }
  };

  const handleModerateReport = async () => {
    if (!modModalReport) return;
    try {
      await api.admin.moderateReport(modModalReport.id, modVisibility, modReason.trim());
      setSuccessNotice(`Report "${modModalReport.title}" visibility updated to ${modVisibility}.`);
      setModModalReport(null);
      setModReason('');
      loadAdminReports();
      loadReports();
    } catch (err: any) {
      setErrorNotice(err?.message || 'Failed to moderate report');
    }
  };

  const handleSuspendUser = async () => {
    if (!suspendModalUser) return;
    const targetStatus = !suspendModalUser.is_active;
    try {
      await api.admin.suspendUser(suspendModalUser.id, targetStatus, suspendReason.trim());
      setSuccessNotice(`User ${suspendModalUser.email} ${targetStatus ? 'reactivated' : 'suspended'} successfully.`);
      setSuspendModalUser(null);
      setSuspendReason('');
      loadAdminUsers();
    } catch (err: any) {
      setErrorNotice(err?.message || 'Failed to update user status');
    }
  };

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
          {(currentUser?.is_staff || currentUser?.is_superuser) && (
            <button
              className={`nav-btn ${activeTab === 'admin' ? 'active' : ''}`}
              onClick={() => setActiveTab('admin')}
            >
              <Shield size={16} /> Admin Workspace
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
                          <button
                            className="btn btn-secondary"
                            style={{ height: '36px', fontSize: '0.85rem', color: 'var(--text-muted)' }}
                            onClick={() => {
                              if (!currentUser) setAuthModalOpen(true);
                              else {
                                setFlagModalReport(report);
                                setFlagReason('SPAM_OR_FRAUD');
                                setFlagDetails('');
                              }
                            }}
                            title="Report suspicious listing or policy violation"
                          >
                            <Flag size={14} /> Report
                          </button>
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

        {/* TAB 5: ADMIN WORKSPACE */}
        {activeTab === 'admin' && (currentUser?.is_staff || currentUser?.is_superuser) && (
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1.25rem', flexWrap: 'wrap', gap: '0.75rem' }}>
              <div>
                <h2 style={{ fontSize: '1.35rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <Shield size={20} color="var(--accent-red)" /> Campus Governance & Admin Workspace
                </h2>
                <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                  Operational metrics, immutable audit trail, report moderation, and user governance.
                </p>
              </div>

              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <button
                  className="btn btn-secondary"
                  style={{ height: '36px', fontSize: '0.8rem' }}
                  onClick={() => {
                    if (adminSubTab === 'overview') loadAdminOverview();
                    if (adminSubTab === 'audit') loadAdminAuditEvents();
                    if (adminSubTab === 'moderation') loadAdminReports();
                    if (adminSubTab === 'users') loadAdminUsers();
                  }}
                >
                  <RefreshCw size={14} className={adminLoading ? 'animate-spin' : ''} /> Refresh
                </button>
              </div>
            </div>

            {/* Admin Subtabs */}
            <div className="subtabs-bar" style={{ marginBottom: '1.5rem' }}>
              <button
                className={`subtab-btn ${adminSubTab === 'overview' ? 'active' : ''}`}
                onClick={() => setAdminSubTab('overview')}
              >
                <Activity size={16} /> System Overview
              </button>
              <button
                className={`subtab-btn ${adminSubTab === 'audit' ? 'active' : ''}`}
                onClick={() => setAdminSubTab('audit')}
              >
                <FileText size={16} /> Audit Trail ({adminOverview?.system.audit_events_count ?? '...'})
              </button>
              <button
                className={`subtab-btn ${adminSubTab === 'moderation' ? 'active' : ''}`}
                onClick={() => setAdminSubTab('moderation')}
              >
                <Eye size={16} /> Content Moderation
              </button>
              <button
                className={`subtab-btn ${adminSubTab === 'users' ? 'active' : ''}`}
                onClick={() => setAdminSubTab('users')}
              >
                <Users size={16} /> User Governance ({adminOverview?.users.total ?? '...'})
              </button>
            </div>

            {/* SUBTAB 1: SYSTEM OVERVIEW */}
            {adminSubTab === 'overview' && (
              <div>
                {adminLoading && !adminOverview ? (
                  <div className="state-box">
                    <RefreshCw size={24} className="animate-spin" />
                    <p>Loading administrative telemetry...</p>
                  </div>
                ) : adminOverview ? (
                  <div>
                    {/* Stat Cards Grid */}
                    <div className="stats-grid">
                      <div className="stat-card">
                        <span className="stat-title">Total Belongings</span>
                        <span className="stat-value">{adminOverview.reports.total}</span>
                        <span className="stat-subtext">
                          {adminOverview.reports.lost_open} Lost Open • {adminOverview.reports.found_open} Found Open
                        </span>
                        <span style={{ fontSize: '0.75rem', color: 'var(--success)', fontWeight: 600 }}>
                          ✓ {adminOverview.reports.returned} Recovered & Returned
                        </span>
                      </div>

                      <div className="stat-card">
                        <span className="stat-title">Claims Pipeline</span>
                        <span className="stat-value">{adminOverview.claims.total}</span>
                        <span className="stat-subtext">
                          <strong style={{ color: 'var(--accent-red)' }}>{adminOverview.claims.pending}</strong> Pending Review
                        </span>
                        <span style={{ fontSize: '0.75rem', color: 'var(--accent-blue)', fontWeight: 600 }}>
                          {adminOverview.claims.approved} Approved • {adminOverview.claims.completed} Handed Over
                        </span>
                      </div>

                      <div className="stat-card">
                        <span className="stat-title">Campus Custody</span>
                        <span className="stat-value">{adminOverview.custody.total_transfers}</span>
                        <span className="stat-subtext">
                          <strong style={{ color: 'var(--warning)' }}>{adminOverview.custody.pending_transfers}</strong> Awaiting Destination Receipt
                        </span>
                        <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                          Across {adminOverview.locations.active_count} Campus Facilities
                        </span>
                      </div>

                      <div className="stat-card">
                        <span className="stat-title">Campus Accounts</span>
                        <span className="stat-value">{adminOverview.users.total}</span>
                        <span className="stat-subtext">
                          {adminOverview.users.active} Active • {adminOverview.users.staff} Staff Accounts
                        </span>
                        {adminOverview.users.suspended > 0 ? (
                          <span style={{ fontSize: '0.75rem', color: 'var(--danger)', fontWeight: 600 }}>
                            ⚠ {adminOverview.users.suspended} Suspended
                          </span>
                        ) : (
                          <span style={{ fontSize: '0.75rem', color: 'var(--success)' }}>
                            ✓ Zero Accounts Suspended
                          </span>
                        )}
                      </div>
                    </div>

                    {/* System & AI Telemetry Banner */}
                    <div className="card" style={{ marginBottom: '1.5rem', background: 'var(--surface-muted)' }}>
                      <h3 style={{ fontSize: '1rem', marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <Activity size={18} color="var(--accent-blue)" /> NVIDIA NIM Vector Engine & pgvector Health
                      </h3>
                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', fontSize: '0.85rem' }}>
                        <div>
                          <span style={{ color: 'var(--text-muted)', display: 'block', marginBottom: '0.2rem' }}>Vector Embeddings API</span>
                          <span className={`badge ${adminOverview.system.nim_enabled ? 'badge-success' : 'badge-status'}`}>
                            {adminOverview.system.nim_enabled ? 'Active / Online' : 'Keyword Only'}
                          </span>
                        </div>
                        <div>
                          <span style={{ color: 'var(--text-muted)', display: 'block', marginBottom: '0.2rem' }}>Frontier NIM Model</span>
                          <strong style={{ fontFamily: 'monospace' }}>{adminOverview.system.nim_model}</strong>
                        </div>
                        <div>
                          <span style={{ color: 'var(--text-muted)', display: 'block', marginBottom: '0.2rem' }}>Indexed Embeddings (2048-dim)</span>
                          <strong>{adminOverview.system.embeddings_count} items embedded</strong>
                        </div>
                        <div>
                          <span style={{ color: 'var(--text-muted)', display: 'block', marginBottom: '0.2rem' }}>Immutable Audit Events</span>
                          <strong>{adminOverview.system.audit_events_count} events recorded</strong>
                        </div>
                      </div>
                    </div>
                  </div>
                ) : null}
              </div>
            )}

            {/* SUBTAB 2: AUDIT TRAIL */}
            {adminSubTab === 'audit' && (
              <div>
                {/* Search & Filters */}
                <div className="search-bar-wrap" style={{ marginBottom: '1rem' }}>
                  <div className="search-input-box" style={{ flex: 2 }}>
                    <Search size={16} />
                    <input
                      type="text"
                      className="form-input"
                      placeholder="Search audit trail by actor, action, request ID, or entity ID..."
                      value={adminAuditSearch}
                      onChange={(e) => setAdminAuditSearch(e.target.value)}
                    />
                  </div>

                  <select
                    className="form-select filter-select"
                    value={adminAuditActionFilter}
                    onChange={(e) => setAdminAuditActionFilter(e.target.value)}
                    style={{ flex: 1 }}
                  >
                    <option value="">All Audit Actions</option>
                    <option value="REPORT_MODERATED">Report Moderation</option>
                    <option value="USER_">User Governance (Suspend/Activate)</option>
                    <option value="CLAIM_">Claim Decisions</option>
                    <option value="HANDOVER_COMPLETED">Handover Completion</option>
                    <option value="CUSTODY_TRANSFER">Custody Transfers</option>
                  </select>

                  <button className="btn btn-secondary" onClick={loadAdminAuditEvents}>
                    Filter
                  </button>
                </div>

                {adminLoading ? (
                  <div className="state-box">
                    <RefreshCw size={24} className="animate-spin" />
                    <p>Fetching immutable audit ledger...</p>
                  </div>
                ) : adminAuditEvents.length === 0 ? (
                  <div className="state-box">
                    <FileText size={32} />
                    <p>No audit events match current criteria.</p>
                  </div>
                ) : (
                  <div className="admin-table-wrap">
                    <table className="admin-table">
                      <thead>
                        <tr>
                          <th>Timestamp</th>
                          <th>Action</th>
                          <th>Actor</th>
                          <th>Target Entity</th>
                          <th>Redacted Audit Metadata</th>
                        </tr>
                      </thead>
                      <tbody>
                        {adminAuditEvents.map((evt) => {
                          const isDestructive = evt.action.includes('REMOVED') || evt.action.includes('SUSPENDED') || evt.action.includes('REJECT');
                          const isSuccess = evt.action.includes('ACTIVE') || evt.action.includes('COMPLETED') || evt.action.includes('APPROVE') || evt.action.includes('ACTIVATED');
                          return (
                            <tr key={evt.id}>
                              <td style={{ whiteSpace: 'nowrap', color: 'var(--text-muted)' }}>
                                {new Date(evt.created_at).toLocaleString()}
                              </td>
                              <td>
                                <span className={`badge ${isDestructive ? 'badge-danger' : isSuccess ? 'badge-success' : 'badge-match'}`}>
                                  {evt.action}
                                </span>
                              </td>
                              <td>
                                <strong>{evt.actor_email || 'System'}</strong>
                                {evt.actor_name && <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block' }}>{evt.actor_name}</span>}
                              </td>
                              <td style={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>
                                <div>{evt.entity_type}</div>
                                <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>{evt.entity_id}</div>
                              </td>
                              <td style={{ maxWidth: '300px' }}>
                                <pre style={{ fontSize: '0.75rem', background: 'var(--surface-muted)', padding: '0.35rem 0.5rem', borderRadius: '4px', overflowX: 'auto', margin: 0 }}>
                                  {JSON.stringify(evt.metadata_redacted || {}, null, 1)}
                                </pre>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}

            {/* SUBTAB 3: CONTENT MODERATION */}
            {adminSubTab === 'moderation' && (
              <div>
                <div className="search-bar-wrap" style={{ marginBottom: '1rem' }}>
                  <div className="search-input-box" style={{ flex: 2 }}>
                    <Search size={16} />
                    <input
                      type="text"
                      className="form-input"
                      placeholder="Search reports by title, description, or author email..."
                      value={adminReportSearch}
                      onChange={(e) => setAdminReportSearch(e.target.value)}
                    />
                  </div>

                  <select
                    className="form-select filter-select"
                    value={adminReportVisibility}
                    onChange={(e) => setAdminReportVisibility(e.target.value)}
                    style={{ flex: 1 }}
                  >
                    <option value="">All Visibility States</option>
                    <option value="ACTIVE">Active (Publicly Visible)</option>
                    <option value="HIDDEN">Hidden (Suppressed)</option>
                    <option value="REMOVED">Removed (Takedown)</option>
                  </select>

                  <button
                    className={`btn ${adminReportFlaggedFilter ? 'btn-danger' : 'btn-secondary'}`}
                    onClick={() => {
                      setAdminReportFlaggedFilter(!adminReportFlaggedFilter);
                    }}
                    style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', height: '38px', fontSize: '0.85rem' }}
                  >
                    <Flag size={14} /> {adminReportFlaggedFilter ? 'Flagged Only (Active)' : 'Flagged Only'}
                  </button>

                  <button className="btn btn-secondary" onClick={loadAdminReports}>
                    Filter
                  </button>
                </div>

                {adminLoading ? (
                  <div className="state-box">
                    <RefreshCw size={24} className="animate-spin" />
                    <p>Loading reports moderation list...</p>
                  </div>
                ) : adminReports.length === 0 ? (
                  <div className="state-box">
                    <Eye size={32} />
                    <p>No reports match moderation filters.</p>
                  </div>
                ) : (
                  <div className="report-list">
                    {adminReports.map((item) => (
                      <div key={item.id} className="card" style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                        <div className="report-item-header">
                          <div>
                            <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.35rem', flexWrap: 'wrap' }}>
                              <span className={`badge ${item.report_type === 'LOST' ? 'badge-lost' : 'badge-found'}`}>
                                {item.report_type}
                              </span>
                              <span className="badge badge-status">{item.category}</span>
                              <span className={`badge ${item.visibility === 'ACTIVE' ? 'badge-success' : item.visibility === 'HIDDEN' ? 'badge-warning' : 'badge-danger'}`}>
                                Visibility: {item.visibility}
                              </span>
                              <span className="badge badge-status">Status: {item.status}</span>
                              {item.abuse_flags_count && item.abuse_flags_count > 0 ? (
                                <button
                                  className="badge badge-danger"
                                  style={{ cursor: 'pointer', border: 'none', display: 'inline-flex', alignItems: 'center', gap: '0.25rem', padding: '0.2rem 0.5rem' }}
                                  onClick={() => setInspectFlagReport(item)}
                                  title="Inspect community flags"
                                >
                                  <Flag size={11} /> {item.abuse_flags_count} Flags Reported
                                </button>
                              ) : null}
                            </div>

                            <h3 style={{ fontSize: '1.05rem', fontWeight: 600 }}>{item.title}</h3>
                            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                              Author: <strong>{item.created_by_email || 'Staff Recorded'}</strong> • Reported: {new Date(item.created_at).toLocaleDateString()}
                            </span>
                          </div>

                          <div className="report-actions">
                            {item.visibility !== 'ACTIVE' && (
                              <button
                                className="btn btn-secondary"
                                style={{ height: '34px', fontSize: '0.8rem', borderColor: 'var(--success)', color: 'var(--success)' }}
                                onClick={() => {
                                  setModModalReport(item);
                                  setModVisibility('ACTIVE');
                                  setModReason('Restored to public visibility');
                                }}
                              >
                                Restore Active
                              </button>
                            )}
                            {item.visibility !== 'HIDDEN' && (
                              <button
                                className="btn btn-secondary"
                                style={{ height: '34px', fontSize: '0.8rem', borderColor: 'var(--warning)', color: 'var(--warning)' }}
                                onClick={() => {
                                  setModModalReport(item);
                                  setModVisibility('HIDDEN');
                                  setModReason('Inappropriate content / under investigation');
                                }}
                              >
                                Hide
                              </button>
                            )}
                            {item.visibility !== 'REMOVED' && (
                              <button
                                className="btn btn-danger"
                                style={{ height: '34px', fontSize: '0.8rem' }}
                                onClick={() => {
                                  setModModalReport(item);
                                  setModVisibility('REMOVED');
                                  setModReason('Violates campus policy / fraud attempt');
                                }}
                              >
                                Remove
                              </button>
                            )}
                          </div>
                        </div>

                        <p style={{ fontSize: '0.9rem', color: 'var(--text)' }}>{item.public_description}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* SUBTAB 4: USER GOVERNANCE */}
            {adminSubTab === 'users' && (
              <div>
                <div className="search-bar-wrap" style={{ marginBottom: '1rem' }}>
                  <div className="search-input-box" style={{ flex: 2 }}>
                    <Search size={16} />
                    <input
                      type="text"
                      className="form-input"
                      placeholder="Search users by email or display name..."
                      value={adminUserSearch}
                      onChange={(e) => setAdminUserSearch(e.target.value)}
                    />
                  </div>

                  <select
                    className="form-select filter-select"
                    value={adminUserFilter}
                    onChange={(e) => setAdminUserFilter(e.target.value)}
                    style={{ flex: 1 }}
                  >
                    <option value="">All Accounts</option>
                    <option value="true">Active Only</option>
                    <option value="false">Suspended Only</option>
                  </select>

                  <button className="btn btn-secondary" onClick={loadAdminUsers}>
                    Filter
                  </button>
                </div>

                {adminLoading ? (
                  <div className="state-box">
                    <RefreshCw size={24} className="animate-spin" />
                    <p>Loading registered campus accounts...</p>
                  </div>
                ) : adminUsers.length === 0 ? (
                  <div className="state-box">
                    <Users size={32} />
                    <p>No user accounts match current criteria.</p>
                  </div>
                ) : (
                  <div className="admin-table-wrap">
                    <table className="admin-table">
                      <thead>
                        <tr>
                          <th>User</th>
                          <th>Role Badges</th>
                          <th>Facility Memberships</th>
                          <th>Account Status</th>
                          <th>Joined</th>
                          <th>Governance Action</th>
                        </tr>
                      </thead>
                      <tbody>
                        {adminUsers.map((u) => {
                          const isSelf = currentUser?.id === u.id;
                          return (
                            <tr key={u.id}>
                              <td>
                                <strong>{u.email}</strong>
                                {u.display_name && (
                                  <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', display: 'block' }}>
                                    {u.display_name}
                                  </span>
                                )}
                              </td>
                              <td>
                                <div style={{ display: 'flex', gap: '0.3rem', flexWrap: 'wrap' }}>
                                  {u.is_superuser && <span className="badge badge-lost">Admin</span>}
                                  {u.is_staff && !u.is_superuser && <span className="badge badge-match">Staff</span>}
                                  {!u.is_staff && !u.is_superuser && <span className="badge badge-status">Student</span>}
                                </div>
                              </td>
                              <td style={{ fontSize: '0.8rem' }}>
                                {u.memberships && u.memberships.length > 0 ? (
                                  u.memberships.map((m) => (
                                    <div key={m.id} style={{ color: 'var(--accent-blue)', fontWeight: 600 }}>
                                      {m.location_name} ({m.role})
                                    </div>
                                  ))
                                ) : (
                                  <span style={{ color: 'var(--text-muted)' }}>General User</span>
                                )}
                              </td>
                              <td>
                                <span className={`badge ${u.is_active ? 'badge-success' : 'badge-danger'}`}>
                                  {u.is_active ? 'Active' : 'Suspended'}
                                </span>
                              </td>
                              <td style={{ color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
                                {new Date(u.created_at).toLocaleDateString()}
                              </td>
                              <td>
                                {isSelf ? (
                                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Current User</span>
                                ) : u.is_active ? (
                                  <button
                                    className="btn btn-danger"
                                    style={{ height: '32px', fontSize: '0.75rem', padding: '0 0.6rem' }}
                                    onClick={() => {
                                      setSuspendModalUser(u);
                                      setSuspendReason('Administrative suspension for policy violation');
                                    }}
                                  >
                                    <Ban size={12} /> Suspend
                                  </button>
                                ) : (
                                  <button
                                    className="btn btn-secondary"
                                    style={{ height: '32px', fontSize: '0.75rem', padding: '0 0.6rem', borderColor: 'var(--success)', color: 'var(--success)' }}
                                    onClick={() => {
                                      setSuspendModalUser(u);
                                      setSuspendReason('Account appeal reviewed and accepted');
                                    }}
                                  >
                                    Reactivate
                                  </button>
                                )}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                )}
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

      {/* MODAL: MODERATE REPORT */}
      {modModalReport && (
        <div className="modal-overlay">
          <div className="modal-content" style={{ maxWidth: '480px' }}>
            <div className="modal-header">
              <h3>Moderate Report Visibility</h3>
              <button
                style={{ background: 'none', border: 'none', fontSize: '1.25rem', cursor: 'pointer', color: 'var(--text)' }}
                onClick={() => setModModalReport(null)}
              >
                ×
              </button>
            </div>
            <div style={{ marginBottom: '1rem', fontSize: '0.9rem' }}>
              Setting visibility of <strong>"{modModalReport.title}"</strong> to <strong style={{ color: modVisibility === 'ACTIVE' ? 'var(--success)' : modVisibility === 'HIDDEN' ? 'var(--warning)' : 'var(--danger)' }}>{modVisibility}</strong>.
            </div>
            <div className="form-group">
              <label className="form-label">Audit Reason for Action:</label>
              <textarea
                className="form-textarea"
                rows={3}
                placeholder="Enter audit explanation (e.g., spam link, duplicate, resolved dispute)..."
                value={modReason}
                onChange={(e) => setModReason(e.target.value)}
              />
            </div>
            <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'flex-end', marginTop: '1rem' }}>
              <button className="btn btn-secondary" onClick={() => setModModalReport(null)}>
                Cancel
              </button>
              <button className="btn btn-primary" onClick={handleModerateReport}>
                Confirm Moderation
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL: SUSPEND / REACTIVATE USER */}
      {suspendModalUser && (
        <div className="modal-overlay">
          <div className="modal-content" style={{ maxWidth: '480px' }}>
            <div className="modal-header">
              <h3>{suspendModalUser.is_active ? 'Suspend User Account' : 'Reactivate User Account'}</h3>
              <button
                style={{ background: 'none', border: 'none', fontSize: '1.25rem', cursor: 'pointer', color: 'var(--text)' }}
                onClick={() => setSuspendModalUser(null)}
              >
                ×
              </button>
            </div>
            <div style={{ marginBottom: '1rem', fontSize: '0.9rem' }}>
              {suspendModalUser.is_active ? (
                <span>Are you sure you want to suspend <strong>{suspendModalUser.email}</strong>? The user will be unable to sign in or submit reports and claims.</span>
              ) : (
                <span>Reactivating <strong>{suspendModalUser.email}</strong> will restore standard access privileges.</span>
              )}
            </div>
            <div className="form-group">
              <label className="form-label">Audit Reason:</label>
              <textarea
                className="form-textarea"
                rows={3}
                placeholder="Reason for suspension or reactivation..."
                value={suspendReason}
                onChange={(e) => setSuspendReason(e.target.value)}
              />
            </div>
            <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'flex-end', marginTop: '1rem' }}>
              <button className="btn btn-secondary" onClick={() => setSuspendModalUser(null)}>
                Cancel
              </button>
              <button
                className={`btn ${suspendModalUser.is_active ? 'btn-danger' : 'btn-primary'}`}
                onClick={handleSuspendUser}
              >
                Confirm {suspendModalUser.is_active ? 'Suspension' : 'Reactivation'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL: REPORT ABUSE / FLAG LISTING */}
      {flagModalReport && (
        <div className="modal-overlay">
          <div className="modal-content" style={{ maxWidth: '480px' }}>
            <div className="modal-header">
              <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--danger)' }}>
                <Flag size={18} /> Report Listing or Abuse
              </h3>
              <button
                style={{ background: 'none', border: 'none', fontSize: '1.25rem', cursor: 'pointer', color: 'var(--text)' }}
                onClick={() => setFlagModalReport(null)}
              >
                ×
              </button>
            </div>

            <div style={{ marginBottom: '1rem', fontSize: '0.88rem' }}>
              Reporting item: <strong>"{flagModalReport.title}"</strong>
              <p style={{ margin: '0.35rem 0 0 0', color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                Reports are sent directly to campus security and administrators for investigation.
              </p>
            </div>

            <form onSubmit={handleFlagSubmit}>
              <div className="form-group">
                <label className="form-label">Reason for Report *</label>
                <select
                  className="form-select"
                  value={flagReason}
                  onChange={(e) => setFlagReason(e.target.value)}
                  required
                >
                  <option value="SPAM_OR_FRAUD">Spam or Fraudulent Listing</option>
                  <option value="INAPPROPRIATE">Inappropriate or Offensive Content</option>
                  <option value="PRIVATE_INFO_LEAK">Personal Contact or Private Info Leak</option>
                  <option value="SUSPICIOUS_CLAIM">Suspicious Details / False Match</option>
                  <option value="OTHER">Other Abuse / Safety Concern</option>
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">Additional Details (Optional)</label>
                <textarea
                  className="form-textarea"
                  rows={3}
                  placeholder="Provide any observations to assist campus staff..."
                  value={flagDetails}
                  onChange={(e) => setFlagDetails(e.target.value)}
                />
              </div>

              <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'flex-end', marginTop: '1.25rem' }}>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setFlagModalReport(null)}
                  disabled={flagSubmitting}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn-danger"
                  disabled={flagSubmitting}
                >
                  {flagSubmitting ? 'Submitting...' : 'Submit Report'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: INSPECT COMMUNITY FLAGS (ADMIN) */}
      {inspectFlagReport && (
        <div className="modal-overlay">
          <div className="modal-content" style={{ maxWidth: '580px' }}>
            <div className="modal-header">
              <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--danger)' }}>
                <Flag size={18} /> Community Flags ({inspectFlagReport.abuse_flags_count || 0})
              </h3>
              <button
                style={{ background: 'none', border: 'none', fontSize: '1.25rem', cursor: 'pointer', color: 'var(--text)' }}
                onClick={() => setInspectFlagReport(null)}
              >
                ×
              </button>
            </div>

            <div style={{ marginBottom: '1rem', fontSize: '0.9rem' }}>
              Target Listing: <strong>"{inspectFlagReport.title}"</strong> ({inspectFlagReport.category})
            </div>

            <div style={{ maxHeight: '280px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '0.75rem', marginBottom: '1.25rem' }}>
              {inspectFlagReport.flag_details && inspectFlagReport.flag_details.length > 0 ? (
                inspectFlagReport.flag_details.map((flag) => (
                  <div key={flag.id} style={{ padding: '0.75rem', background: 'var(--surface-muted)', borderRadius: 'var(--radius)', border: '1px solid var(--border)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.35rem' }}>
                      <span className="badge badge-danger" style={{ fontSize: '0.75rem' }}>{flag.reason_display || flag.reason}</span>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{new Date(flag.created_at).toLocaleString()}</span>
                    </div>
                    <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)', marginBottom: '0.25rem' }}>
                      Reported by: <strong>{flag.reporter_email}</strong>
                    </div>
                    {flag.details && (
                      <p style={{ margin: '0.25rem 0 0 0', fontSize: '0.85rem' }}>
                        "{flag.details}"
                      </p>
                    )}
                  </div>
                ))
              ) : (
                <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>No flag details recorded.</p>
              )}
            </div>

            <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end', flexWrap: 'wrap' }}>
              <button
                className="btn btn-secondary"
                onClick={() => setInspectFlagReport(null)}
              >
                Close
              </button>
              <button
                className="btn btn-secondary"
                style={{ borderColor: 'var(--warning)', color: 'var(--warning)' }}
                onClick={() => {
                  setModModalReport(inspectFlagReport);
                  setModVisibility('HIDDEN');
                  setModReason('Hidden due to multiple community abuse flags');
                  setInspectFlagReport(null);
                }}
              >
                Hide Report
              </button>
              <button
                className="btn btn-danger"
                onClick={() => {
                  setModModalReport(inspectFlagReport);
                  setModVisibility('REMOVED');
                  setModReason('Removed following community abuse reports');
                  setInspectFlagReport(null);
                }}
              >
                Remove Listing
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
