import React, { useEffect, useState } from 'react';
import { Bell, Check, CheckCheck, Filter, Search, AlertTriangle, ExternalLink } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { NotificationService } from '../services/api';
import { InAppNotification } from '../types/alerts';

export const NotificationCenter: React.FC = () => {
  const [notifications, setNotifications] = useState<InAppNotification[]>([]);
  const [totalCount, setTotalCount] = useState<number>(0);
  const [unreadCount, setUnreadCount] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(true);
  const [activeTab, setActiveTab] = useState<'ALL' | 'UNREAD' | 'CRITICAL'>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const navigate = useNavigate();

  const fetchNotifications = async () => {
    setLoading(true);
    try {
      const res = await NotificationService.listNotifications({
        unread_only: activeTab === 'UNREAD',
        limit: 100,
      });
      setNotifications(res.items || []);
      setTotalCount(res.total || 0);
      setUnreadCount(res.unread_count || 0);
    } catch (err) {
      console.error('Failed to load notifications', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchNotifications();
  }, [activeTab]);

  const handleMarkAsRead = async (id: string) => {
    try {
      await NotificationService.markAsRead(id);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: true } : n))
      );
      setUnreadCount((c) => Math.max(0, c - 1));
    } catch (err) {
      console.error('Failed to mark read', err);
    }
  };

  const handleMarkAsUnread = async (id: string) => {
    try {
      await NotificationService.markAsUnread(id);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: false } : n))
      );
      setUnreadCount((c) => c + 1);
    } catch (err) {
      console.error('Failed to mark unread', err);
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await NotificationService.markAllAsRead();
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
      setUnreadCount(0);
    } catch (err) {
      console.error('Failed to mark all read', err);
    }
  };

  const getSeverityBadgeClass = (severity: string) => {
    switch (severity?.toUpperCase()) {
      case 'CRITICAL':
        return 'bg-red-100 text-red-800 border-red-200';
      case 'HIGH':
        return 'bg-orange-100 text-orange-800 border-orange-200';
      case 'MEDIUM':
        return 'bg-amber-100 text-amber-800 border-amber-200';
      default:
        return 'bg-blue-100 text-blue-800 border-blue-200';
    }
  };

  const filteredNotifications = notifications.filter((notif) => {
    if (activeTab === 'CRITICAL' && notif.severity !== 'CRITICAL') return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      const matchTitle = notif.title.toLowerCase().includes(q);
      const matchMsg = notif.message.toLowerCase().includes(q);
      const matchService = notif.service_name.toLowerCase().includes(q);
      const matchProvider = notif.provider.toLowerCase().includes(q);
      return matchTitle || matchMsg || matchService || matchProvider;
    }
    return true;
  });

  return (
    <div className="p-6 space-y-6 max-w-6xl mx-auto">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
            <Bell className="w-5 h-5 text-blue-600" />
            In-App Notification Center
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Centralized hub for cost anomaly alerts, rule triggers, and FinOps delivery status.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {unreadCount > 0 && (
            <button
              onClick={handleMarkAllRead}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-700 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition shadow-xs cursor-pointer"
            >
              <CheckCheck className="w-3.5 h-3.5 text-blue-600" />
              Mark All as Read
            </button>
          )}
          <button
            onClick={() => navigate('/notification-preferences')}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-blue-700 bg-blue-50 border border-blue-200 rounded-lg hover:bg-blue-100 transition shadow-xs cursor-pointer"
          >
            Preferences
          </button>
        </div>
      </div>

      {/* Tabs & Search Filter */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs p-4 flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-2 w-full sm:w-auto">
          <button
            onClick={() => setActiveTab('ALL')}
            className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition cursor-pointer ${
              activeTab === 'ALL'
                ? 'bg-blue-600 text-white shadow-xs'
                : 'text-slate-600 hover:bg-slate-100'
            }`}
          >
            All ({totalCount})
          </button>
          <button
            onClick={() => setActiveTab('UNREAD')}
            className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition cursor-pointer flex items-center gap-1.5 ${
              activeTab === 'UNREAD'
                ? 'bg-blue-600 text-white shadow-xs'
                : 'text-slate-600 hover:bg-slate-100'
            }`}
          >
            Unread
            {unreadCount > 0 && (
              <span className="px-1.5 py-0.2 bg-red-500 text-white text-[10px] rounded-full">
                {unreadCount}
              </span>
            )}
          </button>
          <button
            onClick={() => setActiveTab('CRITICAL')}
            className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition cursor-pointer ${
              activeTab === 'CRITICAL'
                ? 'bg-blue-600 text-white shadow-xs'
                : 'text-slate-600 hover:bg-slate-100'
            }`}
          >
            Critical Only
          </button>
        </div>

        <div className="relative w-full sm:w-72">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Search notifications..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-500 text-slate-800"
          />
        </div>
      </div>

      {/* Notifications List */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs divide-y divide-slate-100 overflow-hidden">
        {loading ? (
          <div className="p-12 text-center text-slate-400 flex flex-col items-center gap-2">
            <div className="w-6 h-6 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
            <span className="text-xs">Loading notifications...</span>
          </div>
        ) : filteredNotifications.length === 0 ? (
          <div className="p-16 text-center text-slate-400 flex flex-col items-center gap-2">
            <Bell className="w-8 h-8 text-slate-300" />
            <span className="text-sm font-medium text-slate-600">No notifications found</span>
            <span className="text-xs text-slate-400">
              {activeTab === 'UNREAD' ? 'You have read all pending notifications.' : 'No alerts have triggered this view.'}
            </span>
          </div>
        ) : (
          filteredNotifications.map((notif) => (
            <div
              key={notif.id}
              className={`p-4 transition hover:bg-slate-50 flex items-start gap-4 ${
                !notif.is_read ? 'bg-blue-50/30' : ''
              }`}
            >
              {/* Severity Pill */}
              <div className="mt-0.5">
                <span
                  className={`inline-block px-2 py-0.5 text-[10px] font-bold uppercase rounded border ${getSeverityBadgeClass(
                    notif.severity
                  )}`}
                >
                  {notif.severity}
                </span>
              </div>

              {/* Main Content */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <h3 className="text-xs font-semibold text-slate-900 truncate">
                    {notif.title}
                  </h3>
                  {!notif.is_read && (
                    <span className="w-2 h-2 rounded-full bg-blue-600 shrink-0" />
                  )}
                </div>

                <p className="text-xs text-slate-600 mt-1 leading-relaxed">
                  {notif.message}
                </p>

                <div className="flex flex-wrap items-center gap-3 mt-2 text-[11px] text-slate-500">
                  <span className="font-semibold text-slate-700 bg-slate-100 px-2 py-0.5 rounded">
                    {notif.provider}
                  </span>
                  <span>Service: {notif.service_name}</span>
                  <span>Account: {notif.account_id}</span>
                  <span className="font-mono font-semibold text-rose-700">
                    Impact: ${Number(notif.excess_cost || 0).toLocaleString()}
                  </span>
                  <span className="text-slate-400">
                    {new Date(notif.created_at).toLocaleString()}
                  </span>
                </div>
              </div>

              {/* Actions */}
              <div className="flex items-center gap-2 shrink-0">
                <button
                  onClick={() =>
                    notif.is_read ? handleMarkAsUnread(notif.id) : handleMarkAsRead(notif.id)
                  }
                  className="px-2.5 py-1 text-xs font-medium text-slate-600 hover:text-slate-900 bg-white border border-slate-200 rounded hover:bg-slate-50 transition cursor-pointer"
                >
                  {notif.is_read ? 'Mark Unread' : 'Mark Read'}
                </button>

                {notif.alert_instance_id && (
                  <button
                    onClick={() => navigate(`/alerts/${notif.alert_instance_id}`)}
                    className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-semibold text-blue-700 bg-blue-50 border border-blue-200 rounded hover:bg-blue-100 transition cursor-pointer"
                  >
                    View Alert
                    <ExternalLink className="w-3 h-3" />
                  </button>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
