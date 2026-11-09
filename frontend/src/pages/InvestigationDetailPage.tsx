import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  ArrowLeft,
  RefreshCw,
  AlertTriangle,
  CheckCircle2,
  Clock,
  UserCheck,
  Tag,
  DollarSign,
  TrendingUp,
  FileText,
  Activity,
  Layers,
  BarChart2,
  PieChart,
  Calendar,
  Share2,
  MessageSquare,
  Shield,
  Send,
  PlusCircle,
  HelpCircle,
  Sparkles,
  Link2,
} from 'lucide-react';
import { InvestigationService } from '../services/api';
import {
  InvestigationCaseDetail,
  MultiDimensionalAnalysis,
  ContributionRankingResponse,
  UsagePriceAnalysis,
  TimelineAnalysis,
  ResourceInvestigationResponse,
  CrossSignalCorrelation,
  InvestigationFinding,
  FindingType,
  ConfidenceCategory,
} from '../types/investigation';

export const InvestigationDetailPage: React.FC = () => {
  const { investigationId } = useParams<{ investigationId: string }>();

  const [caseDetail, setCaseDetail] = useState<InvestigationCaseDetail | null>(null);
  const [dimensions, setDimensions] = useState<MultiDimensionalAnalysis | null>(null);
  const [contributions, setContributions] = useState<ContributionRankingResponse | null>(null);
  const [usagePrice, setUsagePrice] = useState<UsagePriceAnalysis | null>(null);
  const [timeline, setTimeline] = useState<TimelineAnalysis | null>(null);
  const [resources, setResources] = useState<ResourceInvestigationResponse | null>(null);
  const [correlations, setCorrelations] = useState<CrossSignalCorrelation | null>(null);

  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<string>('overview');
  const [selectedDimension, setSelectedDimension] = useState<string>('SERVICE');

  // Modals state
  const [showAssignModal, setShowAssignModal] = useState<boolean>(false);
  const [showTransitionModal, setShowTransitionModal] = useState<boolean>(false);
  const [showNoteModal, setShowNoteModal] = useState<boolean>(false);
  const [showFindingModal, setShowFindingModal] = useState<boolean>(false);

  // Form states
  const [assigneeEmail, setAssigneeEmail] = useState<string>('');
  const [assignNotes, setAssignNotes] = useState<string>('');
  const [targetStatus, setTargetStatus] = useState<string>('INVESTIGATING');
  const [statusNotes, setStatusNotes] = useState<string>('');
  const [verifiedRootCause, setVerifiedRootCause] = useState<string>('');
  const [newNoteContent, setNewNoteContent] = useState<string>('');

  // Finding form
  const [newFindingType, setNewFindingType] = useState<FindingType>('HYPOTHESIS');
  const [newFindingTitle, setNewFindingTitle] = useState<string>('');
  const [newFindingExp, setNewFindingExp] = useState<string>('');
  const [newFindingImpact, setNewFindingImpact] = useState<number>(0);
  const [newFindingConf, setNewFindingConf] = useState<ConfidenceCategory>('MEDIUM');

  const loadCase = async () => {
    if (!investigationId) return;
    try {
      setLoading(true);
      setError(null);
      const [
        caseData,
        dimData,
        contribData,
        upData,
        timeData,
        resData,
        corrData,
      ] = await Promise.all([
        InvestigationService.getInvestigationDetail(investigationId),
        InvestigationService.getDimensions(investigationId),
        InvestigationService.getContributions(investigationId),
        InvestigationService.getUsagePriceAnalysis(investigationId),
        InvestigationService.getTimeline(investigationId),
        InvestigationService.getResources(investigationId),
        InvestigationService.getCorrelations(investigationId),
      ]);

      setCaseDetail(caseData);
      setDimensions(dimData);
      setSelectedDimension(dimData.dominant_dimension || 'SERVICE');
      setContributions(contribData);
      setUsagePrice(upData);
      setTimeline(timeData);
      setResources(resData);
      setCorrelations(corrData);
    } catch (err: any) {
      setError(err?.message || 'Failed to load investigation details');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCase();
  }, [investigationId]);

  const handleAssignSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!investigationId || !assigneeEmail.trim()) return;
    try {
      await InvestigationService.assignCase(investigationId, assigneeEmail.trim(), assignNotes);
      setShowAssignModal(false);
      setAssigneeEmail('');
      setAssignNotes('');
      await loadCase();
    } catch (err: any) {
      alert(`Assignment failed: ${err?.message || err}`);
    }
  };

  const handleTransitionSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!investigationId) return;
    try {
      await InvestigationService.transitionStatus(
        investigationId,
        targetStatus,
        statusNotes,
        verifiedRootCause.trim() || undefined
      );
      setShowTransitionModal(false);
      setStatusNotes('');
      setVerifiedRootCause('');
      await loadCase();
    } catch (err: any) {
      alert(`Status transition failed: ${err?.response?.data?.detail || err?.message || err}`);
    }
  };

  const handleNoteSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!investigationId || !newNoteContent.trim()) return;
    try {
      await InvestigationService.addNote(investigationId, newNoteContent.trim());
      setShowNoteModal(false);
      setNewNoteContent('');
      await loadCase();
    } catch (err: any) {
      alert(`Failed to add note: ${err?.message || err}`);
    }
  };

  const handleFindingSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!investigationId || !newFindingTitle.trim() || !newFindingExp.trim()) return;
    try {
      await InvestigationService.addFinding(investigationId, {
        finding_type: newFindingType,
        title: newFindingTitle.trim(),
        explanation: newFindingExp.trim(),
        financial_impact: Number(newFindingImpact || 0),
        contribution_percentage: caseDetail?.excess_cost ? (Number(newFindingImpact) / Number(caseDetail.excess_cost)) * 100 : 0,
        confidence_category: newFindingConf,
        confidence_score: newFindingConf === 'HIGH' ? 1.0 : newFindingConf === 'MEDIUM' ? 0.75 : 0.4,
        evidence_source: 'MANUAL_ANALYST',
      });
      setShowFindingModal(false);
      setNewFindingTitle('');
      setNewFindingExp('');
      setNewFindingImpact(0);
      await loadCase();
    } catch (err: any) {
      alert(`Failed to add finding: ${err?.message || err}`);
    }
  };

  if (loading) {
    return (
      <div className="py-24 flex flex-col items-center justify-center text-slate-400 gap-3">
        <RefreshCw className="w-8 h-8 animate-spin text-blue-500" />
        <span className="text-sm font-medium">Loading root cause investigation workspace...</span>
      </div>
    );
  }

  if (error || !caseDetail) {
    return (
      <div className="p-8 max-w-4xl mx-auto">
        <div className="bg-red-50 border border-red-200 text-red-700 p-6 rounded-xl text-center space-y-3">
          <AlertTriangle className="w-10 h-10 mx-auto text-red-500" />
          <h2 className="text-base font-bold">Investigation Not Found</h2>
          <p className="text-xs text-red-600">{error || 'Unable to retrieve case details.'}</p>
          <Link
            to="/investigations"
            className="inline-flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg text-xs font-semibold hover:bg-red-700 transition"
          >
            <ArrowLeft className="w-4 h-4" /> Back to Investigations
          </Link>
        </div>
      </div>
    );
  }

  const getFindingBadge = (type: FindingType) => {
    switch (type) {
      case 'FACT':
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-100 text-blue-800 border border-blue-200">FACT</span>;
      case 'CORRELATION':
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-teal-100 text-teal-800 border border-teal-200">CORRELATION</span>;
      case 'HYPOTHESIS':
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-800 border border-amber-200">HYPOTHESIS</span>;
      case 'VERIFIED_CAUSE':
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-purple-100 text-purple-800 border border-purple-200">VERIFIED CAUSE</span>;
      default:
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-100 text-slate-700">{type}</span>;
    }
  };

  const getConfidenceBadge = (cat: ConfidenceCategory) => {
    switch (cat) {
      case 'HIGH':
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-200">HIGH CONFIDENCE</span>;
      case 'MEDIUM':
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-100 text-blue-800 border border-blue-200">MEDIUM CONFIDENCE</span>;
      case 'LOW':
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-orange-100 text-orange-800 border border-orange-200">LOW CONFIDENCE</span>;
      case 'INSUFFICIENT_EVIDENCE':
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-100 text-slate-700 border border-slate-300">INSUFFICIENT EVIDENCE</span>;
      default:
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-100 text-slate-700">{cat}</span>;
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Top Bar Navigation */}
      <div className="flex items-center justify-between">
        <Link
          to="/investigations"
          className="inline-flex items-center gap-2 text-xs font-semibold text-slate-500 hover:text-slate-800 transition"
        >
          <ArrowLeft className="w-4 h-4" /> Back to Investigations List
        </Link>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowNoteModal(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 rounded-lg text-xs font-semibold shadow-sm transition"
          >
            <MessageSquare className="w-3.5 h-3.5" /> Add Note
          </button>
          <button
            onClick={() => setShowFindingModal(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 rounded-lg text-xs font-semibold shadow-sm transition"
          >
            <PlusCircle className="w-3.5 h-3.5 text-blue-600" /> Record Finding
          </button>
          <button
            onClick={() => setShowAssignModal(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 rounded-lg text-xs font-semibold shadow-sm transition"
          >
            <UserCheck className="w-3.5 h-3.5 text-indigo-600" /> Assign
          </button>
          <button
            onClick={() => {
              setTargetStatus(caseDetail.status === 'RESOLVED' ? 'CLOSED' : 'RESOLVED');
              setShowTransitionModal(true);
            }}
            className="flex items-center gap-1.5 px-3.5 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold shadow transition"
          >
            <CheckCircle2 className="w-3.5 h-3.5" /> Transition Status
          </button>
        </div>
      </div>

      {/* Case Header Card */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-4">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b border-slate-100 pb-4">
          <div>
            <div className="flex items-center gap-2.5">
              <span className="font-mono text-sm font-bold bg-blue-50 text-blue-700 px-2.5 py-1 rounded-lg border border-blue-200">
                {caseDetail.case_number}
              </span>
              <h1 className="text-xl font-bold text-slate-900 tracking-tight">{caseDetail.title}</h1>
            </div>
            <div className="text-xs text-slate-500 mt-1 flex flex-wrap items-center gap-2">
              <span className="font-semibold text-slate-700">{caseDetail.provider}</span>
              <span>•</span>
              <span>{caseDetail.service_name}</span>
              {caseDetail.region && <span>• {caseDetail.region}</span>}
              {caseDetail.account_id && <span>• Acct: {caseDetail.account_id}</span>}
              <span>• Opened: {new Date(caseDetail.created_at).toLocaleDateString()}</span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span className="px-2.5 py-1 rounded-lg text-xs font-bold bg-purple-100 text-purple-800 border border-purple-200">
              {caseDetail.status}
            </span>
            <span className="px-2.5 py-1 rounded-lg text-xs font-bold bg-red-100 text-red-800 border border-red-200">
              {caseDetail.priority} PRIORITY
            </span>
          </div>
        </div>

        {/* Financial KPI Summary */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-red-50/60 border border-red-200 p-3.5 rounded-xl">
            <div className="text-[11px] font-semibold text-red-700 uppercase tracking-wide">Excess Spend (Anomalous)</div>
            <div className="text-2xl font-black text-red-700 mt-1">
              ${Number(caseDetail.excess_cost || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </div>
            <div className="text-[10px] text-red-500 mt-0.5">Unbudgeted variance</div>
          </div>
          <div className="bg-slate-50 border border-slate-200 p-3.5 rounded-xl">
            <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wide">Actual Observed Cost</div>
            <div className="text-2xl font-bold text-slate-900 mt-1">
              ${Number(caseDetail.actual_cost || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </div>
            <div className="text-[10px] text-slate-400 mt-0.5">Recorded spend on anomaly date</div>
          </div>
          <div className="bg-slate-50 border border-slate-200 p-3.5 rounded-xl">
            <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wide">Baseline Expected Cost</div>
            <div className="text-2xl font-bold text-slate-900 mt-1">
              ${Number(caseDetail.expected_cost || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </div>
            <div className="text-[10px] text-slate-400 mt-0.5">Statistical rolling baseline</div>
          </div>
          <div className="bg-indigo-50/60 border border-indigo-200 p-3.5 rounded-xl">
            <div className="text-[11px] font-semibold text-indigo-700 uppercase tracking-wide">Assigned Owner</div>
            <div className="text-lg font-bold text-indigo-900 mt-1 truncate">
              {caseDetail.assigned_to || 'Unassigned'}
            </div>
            <div className="text-[10px] text-indigo-500 mt-0.5">
              {caseDetail.assigned_at ? `Assigned on ${new Date(caseDetail.assigned_at).toLocaleDateString()}` : 'Click Assign above'}
            </div>
          </div>
        </div>

        {/* Root Cause Banner */}
        <div className="bg-purple-50/70 border border-purple-200 p-4 rounded-xl flex items-start gap-3">
          <Sparkles className="w-5 h-5 text-purple-600 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <div className="text-xs font-bold text-purple-900 uppercase tracking-wider">
              {caseDetail.verified_root_cause ? 'Verified Root Cause' : 'Diagnostic Hypothesis Summary'}
            </div>
            <p className="text-xs text-purple-950 leading-relaxed">
              {caseDetail.verified_root_cause || caseDetail.root_cause_summary || 'Multi-dimensional analysis underway.'}
            </p>
          </div>
        </div>
      </div>

      {/* Tabs Navigation */}
      <div className="border-b border-slate-200">
        <nav className="flex space-x-6 overflow-x-auto text-xs font-semibold">
          {[
            { id: 'overview', label: 'Findings & Overview', icon: FileText },
            { id: 'dimensions', label: '10-Dimension Slices', icon: Layers },
            { id: 'pareto', label: 'Pareto 80/20 Contributors', icon: BarChart2 },
            { id: 'usage-price', label: 'Usage vs. Price', icon: DollarSign },
            { id: 'timeline', label: 'Timeline & Baseline', icon: Calendar },
            { id: 'resources', label: 'Resource Topology', icon: Activity },
            { id: 'correlations', label: 'Cross-Signal Correlations', icon: Share2 },
            { id: 'ledger', label: 'Evidence & Notes', icon: Shield },
          ].map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`py-3 px-1 border-b-2 font-medium flex items-center gap-2 whitespace-nowrap transition ${
                  isActive
                    ? 'border-blue-600 text-blue-600 font-bold'
                    : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
                }`}
              >
                <Icon className="w-4 h-4" />
                {tab.label}
              </button>
            );
          })}
        </nav>
      </div>

      {/* TAB 1: OVERVIEW & FINDINGS */}
      {activeTab === 'overview' && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="text-sm font-bold text-slate-800">
              Synthesized Findings & Hypotheses ({caseDetail.findings.length})
            </h3>
            <button
              onClick={() => setShowFindingModal(true)}
              className="text-xs text-blue-600 font-semibold hover:underline flex items-center gap-1"
            >
              <PlusCircle className="w-3.5 h-3.5" /> Add Custom Finding
            </button>
          </div>

          <div className="grid grid-cols-1 gap-3">
            {caseDetail.findings.map((f) => (
              <div
                key={f.id}
                className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm hover:border-blue-300 transition space-y-2"
              >
                <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2">
                  <div className="flex items-center gap-2">
                    {getFindingBadge(f.finding_type)}
                    <span className="font-bold text-slate-900 text-xs">{f.title}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    {getConfidenceBadge(f.confidence_category)}
                    <span className="font-mono font-bold text-slate-900 text-xs">
                      ${Number(f.financial_impact || 0).toFixed(2)} ({Number(f.contribution_percentage || 0).toFixed(1)}%)
                    </span>
                  </div>
                </div>

                <p className="text-xs text-slate-600 leading-relaxed">{f.explanation}</p>

                {f.supporting_observations && f.supporting_observations.length > 0 && (
                  <div className="bg-emerald-50/60 border border-emerald-100 rounded-lg p-2.5 text-[11px] text-emerald-800 space-y-1">
                    <span className="font-bold">Supporting Observations:</span>
                    <ul className="list-disc list-inside space-y-0.5 text-emerald-900">
                      {f.supporting_observations.map((obs, idx) => (
                        <li key={idx}>{obs}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {f.contradictory_observations && f.contradictory_observations.length > 0 && (
                  <div className="bg-amber-50/60 border border-amber-100 rounded-lg p-2.5 text-[11px] text-amber-800 space-y-1">
                    <span className="font-bold">Contradictory / Discrepancy Signals:</span>
                    <ul className="list-disc list-inside space-y-0.5 text-amber-900">
                      {f.contradictory_observations.map((obs, idx) => (
                        <li key={idx}>{obs}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {f.suggested_next_step && (
                  <div className="text-[11px] text-blue-700 bg-blue-50 border border-blue-100 rounded-lg px-2.5 py-1.5 flex items-center gap-1.5">
                    <span className="font-bold">Recommended Step:</span>
                    <span>{f.suggested_next_step}</span>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* TAB 2: 10-DIMENSIONAL DECOMPOSITION */}
      {activeTab === 'dimensions' && dimensions && (
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
            <div>
              <h3 className="text-sm font-bold text-slate-900">10-Dimensional Cost Slices</h3>
              <p className="text-xs text-slate-500">
                Independent decomposition across 10 hyperscaler architectural axes without double-counting.
              </p>
            </div>
            <div className="text-xs bg-purple-50 text-purple-700 border border-purple-200 px-3 py-1 rounded-lg font-bold">
              Dominant Axis: {dimensions.dominant_dimension}
            </div>
          </div>

          {/* Dimension Selector Pills */}
          <div className="flex flex-wrap gap-1.5 p-1.5 bg-slate-100 rounded-xl">
            {Object.keys(dimensions.dimensions).map((dimKey) => (
              <button
                key={dimKey}
                onClick={() => setSelectedDimension(dimKey)}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                  selectedDimension === dimKey
                    ? 'bg-white text-blue-700 shadow-sm border border-slate-200'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                {dimKey}
              </button>
            ))}
          </div>

          {/* Contributor Table for Dimension */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="p-3 border-b border-slate-100 bg-slate-50/50 flex justify-between items-center text-xs">
              <span className="font-bold text-slate-700">Contributors along {selectedDimension}</span>
              <span className="text-slate-400">Sorted by anomalous excess spend</span>
            </div>
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-slate-50 text-slate-500 font-semibold border-b border-slate-200 text-[10px] uppercase">
                  <th className="py-2.5 px-4">Dimension Value</th>
                  <th className="py-2.5 px-4 text-right">Actual Cost</th>
                  <th className="py-2.5 px-4 text-right">Expected Cost</th>
                  <th className="py-2.5 px-4 text-right">Excess Spend</th>
                  <th className="py-2.5 px-4 text-right">% Deviation</th>
                  <th className="py-2.5 px-4 text-right">Share of Excess</th>
                  <th className="py-2.5 px-4 text-center">Resources</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {(dimensions.dimensions[selectedDimension] || []).map((contrib, idx) => (
                  <tr key={idx} className="hover:bg-slate-50 transition">
                    <td className="py-2.5 px-4 font-mono font-medium text-slate-900 max-w-xs truncate">
                      {contrib.dimension_value}
                    </td>
                    <td className="py-2.5 px-4 text-right font-medium text-slate-800">
                      ${Number(contrib.actual_cost).toFixed(2)}
                    </td>
                    <td className="py-2.5 px-4 text-right text-slate-500">
                      ${Number(contrib.expected_cost).toFixed(2)}
                    </td>
                    <td className="py-2.5 px-4 text-right font-bold text-red-600">
                      ${Number(contrib.excess_cost).toFixed(2)}
                    </td>
                    <td className="py-2.5 px-4 text-right font-semibold text-slate-700">
                      +{Number(contrib.percentage_deviation).toFixed(1)}%
                    </td>
                    <td className="py-2.5 px-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <div className="w-16 bg-slate-100 rounded-full h-1.5 overflow-hidden">
                          <div
                            className="bg-blue-600 h-1.5 rounded-full"
                            style={{ width: `${Math.min(100, contrib.contribution_share)}%` }}
                          />
                        </div>
                        <span className="font-bold text-slate-900 w-12 text-right">
                          {Number(contrib.contribution_share).toFixed(1)}%
                        </span>
                      </div>
                    </td>
                    <td className="py-2.5 px-4 text-center text-slate-500">
                      {contrib.resource_count}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 3: PARETO 80/20 CONTRIBUTORS */}
      {activeTab === 'pareto' && contributions && (
        <div className="space-y-4">
          <div className="bg-blue-50 border border-blue-200 p-4 rounded-xl flex items-center justify-between">
            <div>
              <h3 className="text-sm font-bold text-blue-900">Pareto 80/20 Contribution Analysis</h3>
              <p className="text-xs text-blue-700 mt-0.5">
                Top <span className="font-bold underline">{contributions.pareto_80_count} contributor(s)</span> drive 80% of the entire anomalous excess expenditure.
              </p>
            </div>
            <div className="text-right">
              <span className="text-[10px] text-blue-600 font-semibold uppercase">Pareto Threshold Count</span>
              <div className="text-2xl font-black text-blue-900">{contributions.pareto_80_count}</div>
            </div>
          </div>

          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-slate-50 text-slate-500 font-semibold border-b border-slate-200 text-[10px] uppercase">
                  <th className="py-2.5 px-4">Rank</th>
                  <th className="py-2.5 px-4">Entity & Resource</th>
                  <th className="py-2.5 px-4">Provider / Service</th>
                  <th className="py-2.5 px-4 text-right">Excess Cost</th>
                  <th className="py-2.5 px-4 text-right">Individual Share</th>
                  <th className="py-2.5 px-4 text-right">Cumulative Share</th>
                  <th className="py-2.5 px-4 text-center">Confidence</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {contributions.top_contributors.map((item) => (
                  <tr key={item.rank} className="hover:bg-slate-50 transition">
                    <td className="py-2.5 px-4 font-bold text-slate-700">#{item.rank}</td>
                    <td className="py-2.5 px-4 font-mono font-medium text-slate-900 max-w-sm truncate">
                      {item.entity_name || item.entity_id}
                    </td>
                    <td className="py-2.5 px-4 text-slate-600">
                      {item.provider} • {item.service_name}
                    </td>
                    <td className="py-2.5 px-4 text-right font-bold text-red-600">
                      ${Number(item.excess_cost).toFixed(2)}
                    </td>
                    <td className="py-2.5 px-4 text-right font-medium text-slate-800">
                      {Number(item.contribution_share).toFixed(1)}%
                    </td>
                    <td className="py-2.5 px-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <div className="w-20 bg-slate-100 rounded-full h-1.5 overflow-hidden">
                          <div
                            className={`h-1.5 rounded-full ${
                              item.cumulative_share <= 80 ? 'bg-blue-600' : 'bg-slate-400'
                            }`}
                            style={{ width: `${Math.min(100, item.cumulative_share)}%` }}
                          />
                        </div>
                        <span className="font-bold text-slate-900 w-12 text-right">
                          {Number(item.cumulative_share).toFixed(1)}%
                        </span>
                      </div>
                    </td>
                    <td className="py-2.5 px-4 text-center">
                      {getConfidenceBadge(item.confidence_category)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 4: USAGE VS PRICE DECOMPOSITION */}
      {activeTab === 'usage-price' && usagePrice && (
        <div className="space-y-4">
          <div className="bg-white border border-slate-200 p-5 rounded-2xl shadow-sm space-y-4">
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2">
              <div>
                <h3 className="text-base font-bold text-slate-900">Economic Growth Accounting Decomposition</h3>
                <p className="text-xs text-slate-500">
                  Separating volumetric consumption changes (ΔQ·P₀) from unit rate escalations (ΔP·Q₀).
                </p>
              </div>
              <span className="px-3 py-1 rounded-full text-xs font-bold bg-indigo-100 text-indigo-800 border border-indigo-200">
                Primary Driver: {usagePrice.primary_cost_driver}
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="bg-blue-50/70 border border-blue-200 p-4 rounded-xl">
                <div className="text-xs font-semibold text-blue-700 uppercase">Usage Volume Effect (ΔQ · P₀)</div>
                <div className="text-2xl font-black text-blue-900 mt-1">
                  ${Number(usagePrice.usage_effect).toFixed(2)}
                </div>
                <div className="text-[11px] text-blue-600 mt-1">
                  Share: {((Number(usagePrice.usage_effect) / (Number(usagePrice.total_excess_cost) || 1)) * 100).toFixed(1)}%
                </div>
              </div>

              <div className="bg-amber-50/70 border border-amber-200 p-4 rounded-xl">
                <div className="text-xs font-semibold text-amber-700 uppercase">Unit Price Rate Effect (ΔP · Q₀)</div>
                <div className="text-2xl font-black text-amber-900 mt-1">
                  ${Number(usagePrice.price_effect).toFixed(2)}
                </div>
                <div className="text-[11px] text-amber-600 mt-1">
                  Share: {((Number(usagePrice.price_effect) / (Number(usagePrice.total_excess_cost) || 1)) * 100).toFixed(1)}%
                </div>
              </div>

              <div className="bg-slate-50 border border-slate-200 p-4 rounded-xl">
                <div className="text-xs font-semibold text-slate-500 uppercase">Interaction / Mix Effect (ΔQ · ΔP)</div>
                <div className="text-2xl font-bold text-slate-800 mt-1">
                  ${Number(usagePrice.mix_or_quantity_effect).toFixed(2)}
                </div>
                <div className="text-[11px] text-slate-400 mt-1">
                  Simultaneous volume and rate variation
                </div>
              </div>
            </div>

            <div className="bg-slate-50 p-3.5 rounded-xl text-xs text-slate-600 border border-slate-200">
              <span className="font-bold text-slate-800">Methodology Notes: </span>
              {usagePrice.methodology_notes}
            </div>
          </div>
        </div>
      )}

      {/* TAB 5: TIMELINE & BASELINE */}
      {activeTab === 'timeline' && timeline && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-sm">
              <div className="text-[11px] text-slate-500 font-semibold">Day-over-Day Variance</div>
              <div className="text-xl font-bold text-red-600 mt-1">
                +{Number(timeline.day_over_day_change_pct).toFixed(1)}%
              </div>
            </div>
            <div className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-sm">
              <div className="text-[11px] text-slate-500 font-semibold">Week-over-Week Variance</div>
              <div className="text-xl font-bold text-red-600 mt-1">
                +{Number(timeline.week_over_week_change_pct).toFixed(1)}%
              </div>
            </div>
            <div className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-sm">
              <div className="text-[11px] text-slate-500 font-semibold">Month-over-Month Variance</div>
              <div className="text-xl font-bold text-red-600 mt-1">
                +{Number(timeline.month_over_month_change_pct).toFixed(1)}%
              </div>
            </div>
          </div>

          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-slate-50 text-slate-500 font-semibold border-b border-slate-200 text-[10px] uppercase">
                  <th className="py-2.5 px-4">Date</th>
                  <th className="py-2.5 px-4 text-right">Actual Cost</th>
                  <th className="py-2.5 px-4 text-right">Baseline Expected</th>
                  <th className="py-2.5 px-4 text-right">Excess Spend</th>
                  <th className="py-2.5 px-4 text-right">7-Day Moving Avg</th>
                  <th className="py-2.5 px-4 text-center">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {timeline.data_points.map((pt) => (
                  <tr
                    key={pt.date}
                    className={`hover:bg-slate-50 transition ${
                      pt.is_anomaly_period ? 'bg-red-50/40 font-bold' : ''
                    }`}
                  >
                    <td className="py-2 px-4 font-mono">{pt.date}</td>
                    <td className="py-2 px-4 text-right font-medium text-slate-900">
                      ${Number(pt.actual_cost).toFixed(2)}
                    </td>
                    <td className="py-2 px-4 text-right text-slate-500">
                      ${Number(pt.baseline_expected_cost).toFixed(2)}
                    </td>
                    <td className="py-2 px-4 text-right text-red-600 font-bold">
                      ${Number(pt.excess_cost).toFixed(2)}
                    </td>
                    <td className="py-2 px-4 text-right text-slate-600">
                      {pt.seven_day_moving_avg ? `$${Number(pt.seven_day_moving_avg).toFixed(2)}` : 'N/A'}
                    </td>
                    <td className="py-2 px-4 text-center">
                      {pt.is_anomaly_period ? (
                        <span className="px-2 py-0.5 rounded text-[10px] bg-red-100 text-red-800 font-bold">
                          SPIKE DATE
                        </span>
                      ) : (
                        <span className="text-slate-400 text-[10px]">BASELINE</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 6: RESOURCE TOPOLOGY */}
      {activeTab === 'resources' && resources && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 gap-4">
            {resources.resources.map((res) => (
              <div key={res.resource_id} className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-3">
                <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 border-b border-slate-100 pb-3">
                  <div>
                    <div className="font-mono text-xs font-bold text-slate-900">{res.resource_id}</div>
                    <div className="text-[11px] text-slate-500 mt-0.5">
                      {res.provider} • {res.resource_type} • {res.region}
                    </div>
                  </div>
                  <span className="px-2.5 py-1 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-200">
                    Status: {res.status}
                  </span>
                </div>

                <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
                  <div>
                    <span className="text-slate-400 text-[10px]">Environment</span>
                    <div className="font-semibold text-slate-800">{res.environment}</div>
                  </div>
                  <div>
                    <span className="text-slate-400 text-[10px]">Owner</span>
                    <div className="font-semibold text-slate-800">{res.owner || 'Unassigned'}</div>
                  </div>
                  <div>
                    <span className="text-slate-400 text-[10px]">Cost Center</span>
                    <div className="font-semibold text-slate-800">{res.cost_center || 'Unallocated'}</div>
                  </div>
                  <div>
                    <span className="text-slate-400 text-[10px]">Attributed Spend</span>
                    <div className="font-bold text-red-600">${Number(res.actual_cost).toFixed(2)}</div>
                  </div>
                </div>

                {/* Telemetry Summary */}
                {res.metrics_summary && Object.keys(res.metrics_summary).length > 0 && (
                  <div className="bg-slate-50 p-3 rounded-lg border border-slate-200 text-xs space-y-1">
                    <span className="font-bold text-slate-700">Telemetry Summary:</span>
                    <div className="flex flex-wrap gap-4 text-slate-600 text-[11px] mt-1">
                      {res.metrics_summary.avg_cpu_percent !== undefined && (
                        <span>Avg CPU: <strong>{res.metrics_summary.avg_cpu_percent.toFixed(1)}%</strong></span>
                      )}
                      {res.metrics_summary.max_cpu_percent !== undefined && (
                        <span>Max CPU: <strong>{res.metrics_summary.max_cpu_percent.toFixed(1)}%</strong></span>
                      )}
                      {res.metrics_summary.sample_count !== undefined && (
                        <span>Samples: <strong>{res.metrics_summary.sample_count}</strong></span>
                      )}
                    </div>
                  </div>
                )}

                {/* Topology Edges */}
                {res.relationships && res.relationships.length > 0 && (
                  <div className="text-xs space-y-1.5">
                    <span className="font-bold text-slate-700">Topology Relationships:</span>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-1">
                      {res.relationships.map((rel, idx) => (
                        <div key={idx} className="bg-slate-50 border border-slate-200 rounded-lg p-2 font-mono text-[11px] flex items-center justify-between">
                          <span className="text-slate-700 truncate">{rel.target}</span>
                          <span className="text-[10px] bg-blue-100 text-blue-800 font-bold px-1.5 py-0.5 rounded ml-2">
                            {rel.type}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* TAB 7: CROSS-SIGNAL CORRELATIONS */}
      {activeTab === 'correlations' && correlations && (
        <div className="space-y-4">
          <div className="bg-white border border-slate-200 p-4 rounded-xl shadow-sm flex items-center justify-between">
            <div>
              <h3 className="text-sm font-bold text-slate-900">Multi-Signal Cross-Engine Correlation</h3>
              <p className="text-xs text-slate-500 mt-0.5">{correlations.correlation_summary}</p>
            </div>
            {getConfidenceBadge(correlations.correlation_confidence)}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Waste Detections */}
            <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm space-y-3">
              <div className="font-bold text-xs text-slate-800 flex items-center gap-1.5">
                <AlertTriangle className="w-4 h-4 text-amber-500" />
                Active Waste Findings ({correlations.correlated_waste_detections.length})
              </div>
              {correlations.correlated_waste_detections.length === 0 ? (
                <div className="text-slate-400 text-xs italic py-4 text-center">No matching waste detections</div>
              ) : (
                <div className="space-y-2">
                  {correlations.correlated_waste_detections.map((w) => (
                    <div key={w.id} className="p-2.5 bg-amber-50/50 border border-amber-200 rounded-lg text-xs space-y-1">
                      <div className="font-bold text-amber-900">{w.rule_name}</div>
                      <div className="text-[11px] text-amber-700">Waste: ${w.wasted_cost.toFixed(2)}/mo</div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Recommendations */}
            <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm space-y-3">
              <div className="font-bold text-xs text-slate-800 flex items-center gap-1.5">
                <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                FinOps Recommendations ({correlations.correlated_recommendations.length})
              </div>
              {correlations.correlated_recommendations.length === 0 ? (
                <div className="text-slate-400 text-xs italic py-4 text-center">No matching recommendations</div>
              ) : (
                <div className="space-y-2">
                  {correlations.correlated_recommendations.map((r) => (
                    <div key={r.id} className="p-2.5 bg-emerald-50/50 border border-emerald-200 rounded-lg text-xs space-y-1">
                      <div className="font-bold text-emerald-900">{r.title}</div>
                      <div className="text-[11px] text-emerald-700">Savings: ${r.estimated_monthly_savings.toFixed(2)}/mo</div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Alerts */}
            <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm space-y-3">
              <div className="font-bold text-xs text-slate-800 flex items-center gap-1.5">
                <Activity className="w-4 h-4 text-blue-500" />
                Enterprise Alerts ({correlations.correlated_alerts.length})
              </div>
              {correlations.correlated_alerts.length === 0 ? (
                <div className="text-slate-400 text-xs italic py-4 text-center">No matching alerts</div>
              ) : (
                <div className="space-y-2">
                  {correlations.correlated_alerts.map((a) => (
                    <div key={a.id} className="p-2.5 bg-blue-50/50 border border-blue-200 rounded-lg text-xs space-y-1">
                      <div className="font-bold text-blue-900">{a.rule_name}</div>
                      <div className="text-[11px] text-blue-700">Trigger: ${a.trigger_value.toFixed(2)}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* TAB 8: EVIDENCE & NOTES LEDGER */}
      {activeTab === 'ledger' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Notes Thread */}
          <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm space-y-4">
            <div className="flex justify-between items-center">
              <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <MessageSquare className="w-4 h-4 text-blue-600" /> Analyst Notes & Collaboration
              </h3>
              <button
                onClick={() => setShowNoteModal(true)}
                className="text-xs text-blue-600 font-semibold hover:underline"
              >
                + Add Note
              </button>
            </div>

            <div className="space-y-3 max-h-96 overflow-y-auto">
              {caseDetail.notes.length === 0 ? (
                <div className="text-slate-400 text-xs italic py-8 text-center">No notes recorded yet</div>
              ) : (
                caseDetail.notes.map((n) => (
                  <div key={n.id} className="p-3 bg-slate-50 border border-slate-200 rounded-xl text-xs space-y-1">
                    <div className="flex justify-between items-center text-[10px] text-slate-400">
                      <span className="font-bold text-slate-700">{n.author}</span>
                      <span>{new Date(n.created_at).toLocaleString()}</span>
                    </div>
                    <p className="text-slate-800 leading-relaxed">{n.content}</p>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Audit History Timeline */}
          <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm space-y-4">
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <Shield className="w-4 h-4 text-purple-600" /> Immutable State Transition Audit
            </h3>

            <div className="space-y-3 max-h-96 overflow-y-auto">
              {caseDetail.history.map((h) => (
                <div key={h.id} className="flex items-start gap-3 text-xs border-l-2 border-blue-500 pl-3 py-1">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-slate-800">{h.action}</span>
                      <span className="text-[10px] text-slate-400">by {h.actor}</span>
                    </div>
                    {h.notes && <p className="text-slate-600 text-[11px] mt-0.5">{h.notes}</p>}
                    <span className="text-[10px] text-slate-400">{new Date(h.created_at).toLocaleString()}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* --- MODALS --- */}

      {/* Assign Modal */}
      {showAssignModal && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-xl max-w-md w-full p-6 space-y-4">
            <h3 className="text-base font-bold text-slate-900">Assign Investigation Case</h3>
            <form onSubmit={handleAssignSubmit} className="space-y-3">
              <div>
                <label className="text-xs font-semibold text-slate-700">Assignee Email / Principal ID</label>
                <input
                  type="email"
                  required
                  placeholder="analyst@cloudsage.internal"
                  value={assigneeEmail}
                  onChange={(e) => setAssigneeEmail(e.target.value)}
                  className="w-full mt-1 p-2 bg-slate-50 border border-slate-300 rounded-lg text-xs"
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-slate-700">Handover Notes (Optional)</label>
                <textarea
                  rows={3}
                  placeholder="Reason for assignment..."
                  value={assignNotes}
                  onChange={(e) => setAssignNotes(e.target.value)}
                  className="w-full mt-1 p-2 bg-slate-50 border border-slate-300 rounded-lg text-xs"
                />
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowAssignModal(false)}
                  className="px-3 py-1.5 bg-slate-100 text-slate-700 rounded-lg text-xs font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 bg-blue-600 text-white rounded-lg text-xs font-semibold hover:bg-blue-700"
                >
                  Save Assignment
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Transition Modal */}
      {showTransitionModal && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-xl max-w-md w-full p-6 space-y-4">
            <h3 className="text-base font-bold text-slate-900">Transition Lifecycle Status</h3>
            <form onSubmit={handleTransitionSubmit} className="space-y-3">
              <div>
                <label className="text-xs font-semibold text-slate-700">Target Status</label>
                <select
                  value={targetStatus}
                  onChange={(e) => setTargetStatus(e.target.value)}
                  className="w-full mt-1 p-2 bg-slate-50 border border-slate-300 rounded-lg text-xs font-medium"
                >
                  <option value="ASSIGNED">ASSIGNED</option>
                  <option value="INVESTIGATING">INVESTIGATING</option>
                  <option value="ROOT_CAUSE_IDENTIFIED">ROOT_CAUSE_IDENTIFIED</option>
                  <option value="ACTION_RECOMMENDED">ACTION_RECOMMENDED</option>
                  <option value="RESOLVED">RESOLVED</option>
                  <option value="CLOSED">CLOSED</option>
                </select>
              </div>

              {(targetStatus === 'ROOT_CAUSE_IDENTIFIED' || targetStatus === 'RESOLVED') && (
                <div>
                  <label className="text-xs font-semibold text-purple-800">
                    Verified Root Cause Explanation (Mandatory)
                  </label>
                  <textarea
                    rows={2}
                    required
                    placeholder="Provide definitive root cause reason..."
                    value={verifiedRootCause}
                    onChange={(e) => setVerifiedRootCause(e.target.value)}
                    className="w-full mt-1 p-2 bg-purple-50/50 border border-purple-200 rounded-lg text-xs"
                  />
                </div>
              )}

              <div>
                <label className="text-xs font-semibold text-slate-700">Resolution / Transition Notes</label>
                <textarea
                  rows={3}
                  placeholder="Document review notes..."
                  value={statusNotes}
                  onChange={(e) => setStatusNotes(e.target.value)}
                  className="w-full mt-1 p-2 bg-slate-50 border border-slate-300 rounded-lg text-xs"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowTransitionModal(false)}
                  className="px-3 py-1.5 bg-slate-100 text-slate-700 rounded-lg text-xs font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 bg-blue-600 text-white rounded-lg text-xs font-semibold hover:bg-blue-700"
                >
                  Confirm Transition
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Add Note Modal */}
      {showNoteModal && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-xl max-w-md w-full p-6 space-y-4">
            <h3 className="text-base font-bold text-slate-900">Add Analyst Note</h3>
            <form onSubmit={handleNoteSubmit} className="space-y-3">
              <div>
                <label className="text-xs font-semibold text-slate-700">Note Content</label>
                <textarea
                  rows={4}
                  required
                  placeholder="Record diagnostic observations, ticket links, or owner feedback..."
                  value={newNoteContent}
                  onChange={(e) => setNewNoteContent(e.target.value)}
                  className="w-full mt-1 p-2.5 bg-slate-50 border border-slate-300 rounded-lg text-xs"
                />
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowNoteModal(false)}
                  className="px-3 py-1.5 bg-slate-100 text-slate-700 rounded-lg text-xs font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 bg-blue-600 text-white rounded-lg text-xs font-semibold hover:bg-blue-700"
                >
                  Save Note
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Add Finding Modal */}
      {showFindingModal && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-xl max-w-lg w-full p-6 space-y-4">
            <h3 className="text-base font-bold text-slate-900">Record Root Cause Finding</h3>
            <form onSubmit={handleFindingSubmit} className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-semibold text-slate-700">Finding Type</label>
                  <select
                    value={newFindingType}
                    onChange={(e) => setNewFindingType(e.target.value as FindingType)}
                    className="w-full mt-1 p-2 bg-slate-50 border border-slate-300 rounded-lg text-xs"
                  >
                    <option value="FACT">FACT</option>
                    <option value="CORRELATION">CORRELATION</option>
                    <option value="HYPOTHESIS">HYPOTHESIS</option>
                    <option value="VERIFIED_CAUSE">VERIFIED_CAUSE</option>
                  </select>
                </div>
                <div>
                  <label className="text-xs font-semibold text-slate-700">Confidence Tier</label>
                  <select
                    value={newFindingConf}
                    onChange={(e) => setNewFindingConf(e.target.value as ConfidenceCategory)}
                    className="w-full mt-1 p-2 bg-slate-50 border border-slate-300 rounded-lg text-xs"
                  >
                    <option value="HIGH">HIGH</option>
                    <option value="MEDIUM">MEDIUM</option>
                    <option value="LOW">LOW</option>
                    <option value="INSUFFICIENT_EVIDENCE">INSUFFICIENT_EVIDENCE</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-700">Finding Title</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. EC2 autoscaling triggered by traffic surge"
                  value={newFindingTitle}
                  onChange={(e) => setNewFindingTitle(e.target.value)}
                  className="w-full mt-1 p-2 bg-slate-50 border border-slate-300 rounded-lg text-xs"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-700">Financial Impact (USD)</label>
                <input
                  type="number"
                  step="0.01"
                  placeholder="0.00"
                  value={newFindingImpact}
                  onChange={(e) => setNewFindingImpact(parseFloat(e.target.value) || 0)}
                  className="w-full mt-1 p-2 bg-slate-50 border border-slate-300 rounded-lg text-xs"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-700">Detailed Explanation</label>
                <textarea
                  rows={3}
                  required
                  placeholder="Document telemetry evidence and rationale..."
                  value={newFindingExp}
                  onChange={(e) => setNewFindingExp(e.target.value)}
                  className="w-full mt-1 p-2 bg-slate-50 border border-slate-300 rounded-lg text-xs"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowFindingModal(false)}
                  className="px-3 py-1.5 bg-slate-100 text-slate-700 rounded-lg text-xs font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 bg-blue-600 text-white rounded-lg text-xs font-semibold hover:bg-blue-700"
                >
                  Save Finding
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
