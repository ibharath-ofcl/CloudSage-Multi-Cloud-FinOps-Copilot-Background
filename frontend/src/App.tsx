import React, { useState } from 'react';
import { Routes, Route } from 'react-router-dom';
import { FilterProvider } from './context/FilterContext';
import { Sidebar } from './components/Sidebar';
import { Header } from './components/Header';
import { CopilotDrawer } from './components/CopilotDrawer';
import { OverviewPage } from './pages/OverviewPage';
import { CostAnalyticsPage } from './pages/CostAnalyticsPage';
import { AnomalyPage } from './pages/AnomalyPage';
import { WastePage } from './pages/WastePage';
import { RecommendationsPage } from './pages/RecommendationsPage';
import { SavingsPage } from './pages/SavingsPage';
import { InventoryPage } from './pages/InventoryPage';
import { QualityPage } from './pages/QualityPage';

export const App: React.FC = () => {
  const [isCopilotOpen, setIsCopilotOpen] = useState(false);
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  const handleRefresh = () => {
    setRefreshTrigger((prev) => prev + 1);
  };

  return (
    <FilterProvider>
      <div className="flex min-h-screen bg-slate-50 font-sans text-slate-900 antialiased">
        {/* Left Sidebar */}
        <Sidebar />

        {/* Main Content Area */}
        <div className="flex-1 flex flex-col min-w-0">
          <Header
            onRefresh={handleRefresh}
            onToggleCopilot={() => setIsCopilotOpen((prev) => !prev)}
          />

          <main className="flex-1 overflow-y-auto">
            <Routes>
              <Route path="/" element={<OverviewPage key={refreshTrigger} />} />
              <Route path="/costs" element={<CostAnalyticsPage key={refreshTrigger} />} />
              <Route path="/anomalies" element={<AnomalyPage key={refreshTrigger} />} />
              <Route path="/waste" element={<WastePage key={refreshTrigger} />} />
              <Route path="/recommendations" element={<RecommendationsPage key={refreshTrigger} />} />
              <Route path="/savings" element={<SavingsPage key={refreshTrigger} />} />
              <Route path="/inventory" element={<InventoryPage key={refreshTrigger} />} />
              <Route path="/quality" element={<QualityPage key={refreshTrigger} />} />
            </Routes>
          </main>
        </div>

        {/* AI Copilot Slide-Out Drawer */}
        <CopilotDrawer
          isOpen={isCopilotOpen}
          onClose={() => setIsCopilotOpen(false)}
        />
      </div>
    </FilterProvider>
  );
};

export default App;
