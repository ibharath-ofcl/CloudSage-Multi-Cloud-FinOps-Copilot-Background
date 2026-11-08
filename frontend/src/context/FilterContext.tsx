import React, { createContext, useContext, useState, ReactNode } from 'react';
import { DashboardFilterParams } from '../types/dashboard';

interface FilterContextType {
  filters: DashboardFilterParams;
  setFilters: React.Dispatch<React.SetStateAction<DashboardFilterParams>>;
  resetFilters: () => void;
  updateFilter: (key: keyof DashboardFilterParams, value: any) => void;
}

const defaultFilters: DashboardFilterParams = {
  startDate: null,
  endDate: null,
  provider: 'ALL',
  service: null,
  accountId: null,
  region: null,
  environment: null,
  owner: null,
  costCenter: null,
};

const FilterContext = createContext<FilterContextType | undefined>(undefined);

export const FilterProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [filters, setFilters] = useState<DashboardFilterParams>(defaultFilters);

  const resetFilters = () => {
    setFilters(defaultFilters);
  };

  const updateFilter = (key: keyof DashboardFilterParams, value: any) => {
    setFilters((prev) => ({
      ...prev,
      [key]: value === '' ? null : value,
    }));
  };

  return (
    <FilterContext.Provider value={{ filters, setFilters, resetFilters, updateFilter }}>
      {children}
    </FilterContext.Provider>
  );
};

export const useFilters = (): FilterContextType => {
  const context = useContext(FilterContext);
  if (!context) {
    throw new Error('useFilters must be used within a FilterProvider');
  }
  return context;
};
