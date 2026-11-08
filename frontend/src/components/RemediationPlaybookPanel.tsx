import React, { useState, useEffect } from 'react';
import { RemediationPlaybook } from '../types/workspace';
import { WorkspaceService } from '../services/api';

interface RemediationPlaybookPanelProps {
  recommendationId?: string;
  wasteFindingId?: string;
  defaultFormat?: 'terraform' | 'cloudformation' | 'aws_cli' | 'azure_cli' | 'gcp_cli' | 'bicep' | 'markdown';
}

export const RemediationPlaybookPanel: React.FC<RemediationPlaybookPanelProps> = ({
  recommendationId,
  wasteFindingId,
  defaultFormat = 'terraform',
}) => {
  const [format, setFormat] = useState<string>(defaultFormat);
  const [playbook, setPlaybook] = useState<RemediationPlaybook | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [copied, setCopied] = useState<boolean>(false);

  useEffect(() => {
    let isMounted = true;
    setLoading(true);

    const loadPlaybook = async () => {
      try {
        let res: RemediationPlaybook;
        if (recommendationId) {
          res = await WorkspaceService.getRecommendationPlaybook(recommendationId, format);
        } else if (wasteFindingId) {
          res = await WorkspaceService.getFindingPlaybook(wasteFindingId, format);
        } else {
          setLoading(false);
          return;
        }

        if (isMounted) setPlaybook(res);
      } catch (err) {
        console.error('Failed to generate playbook', err);
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    loadPlaybook();
    return () => {
      isMounted = false;
    };
  }, [recommendationId, wasteFindingId, format]);

  const handleCopy = () => {
    if (playbook?.content) {
      navigator.clipboard.writeText(playbook.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const getDownloadUrl = () => {
    if (recommendationId) {
      return WorkspaceService.getRecommendationPlaybookDownloadUrl(recommendationId, format);
    }
    if (wasteFindingId) {
      return WorkspaceService.getFindingPlaybookDownloadUrl(wasteFindingId, format);
    }
    return '#';
  };

  const formats = [
    { id: 'terraform', label: 'Terraform (.tf)' },
    { id: 'cloudformation', label: 'CloudFormation (.yaml)' },
    { id: 'aws_cli', label: 'AWS CLI (.sh)' },
    { id: 'azure_cli', label: 'Azure CLI (.sh)' },
    { id: 'bicep', label: 'Azure Bicep (.bicep)' },
    { id: 'gcp_cli', label: 'GCP CLI (.sh)' },
    { id: 'markdown', label: 'Markdown (.md)' },
  ];

  return (
    <div className="bg-slate-800/60 rounded-xl p-5 border border-slate-700/60">
      {/* Non-destructive Advisory Banner */}
      <div className="mb-4 p-3 bg-amber-500/10 border border-amber-500/20 rounded-lg flex items-start space-x-2 text-xs text-amber-300">
        <svg className="w-4 h-4 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
        <span>
          <strong>Advisory Only:</strong> CloudSage provides copy-pasteable remediation templates for authorized review. Zero cloud mutation commands are executed automatically.
        </span>
      </div>

      {/* Format Selector Tabs */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-700 pb-3 mb-3">
        <div className="flex flex-wrap gap-1">
          {formats.map((f) => (
            <button
              key={f.id}
              onClick={() => setFormat(f.id)}
              className={`px-2.5 py-1 text-xs rounded-lg font-mono transition ${
                format === f.id
                  ? 'bg-indigo-600 text-white font-semibold'
                  : 'bg-slate-900/60 text-slate-400 hover:text-slate-200'
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={handleCopy}
            className="flex items-center space-x-1 px-2.5 py-1 bg-slate-700 hover:bg-slate-600 text-slate-200 text-xs font-medium rounded-lg transition"
          >
            {copied ? (
              <>
                <svg className="w-3.5 h-3.5 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                <span>Copied!</span>
              </>
            ) : (
              <>
                <svg className="w-3.5 h-3.5 text-slate-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
                <span>Copy</span>
              </>
            )}
          </button>

          <a
            href={getDownloadUrl()}
            download
            className="flex items-center space-x-1 px-2.5 py-1 bg-indigo-600/30 hover:bg-indigo-600/50 text-indigo-300 text-xs font-medium rounded-lg transition"
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            <span>Download</span>
          </a>
        </div>
      </div>

      {/* Code Viewer */}
      {loading ? (
        <div className="flex items-center justify-center p-8 text-slate-400 text-xs font-mono">
          Generating {format} playbook...
        </div>
      ) : (
        <div className="bg-slate-950 rounded-lg p-4 font-mono text-xs text-slate-300 overflow-x-auto border border-slate-800 leading-relaxed max-h-96">
          <pre>{playbook?.content}</pre>
        </div>
      )}
    </div>
  );
};
