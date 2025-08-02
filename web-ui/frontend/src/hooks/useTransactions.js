import { useState, useEffect, useCallback } from 'react';
import apiService from '../services/api';

export const useTransactions = (initialFilters = {}) => {
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [pagination, setPagination] = useState({
    page: 1,
    limit: 50,
    total: 0,
    totalPages: 0
  });
  const [filters, setFilters] = useState(initialFilters);

  const fetchTransactions = useCallback(async (newFilters = {}) => {
    setLoading(true);
    setError(null);
    
    try {
      const params = {
        ...filters,
        ...newFilters,
        page: newFilters.page || pagination.page,
        limit: newFilters.limit || pagination.limit
      };
      
      const response = await apiService.getTransactions(params);
      
      setTransactions(response.transactions || []);
      setPagination({
        page: response.pagination?.page || 1,
        limit: response.pagination?.limit || 50,
        total: response.pagination?.total || 0,
        totalPages: response.pagination?.totalPages || 0
      });
    } catch (err) {
      setError(err.message);
      setTransactions([]);
    } finally {
      setLoading(false);
    }
  }, [filters, pagination.page, pagination.limit]);

  const updateFilters = useCallback((newFilters) => {
    setFilters(prev => ({ ...prev, ...newFilters }));
    fetchTransactions({ ...newFilters, page: 1 });
  }, [fetchTransactions]);

  const changePage = useCallback((page) => {
    setPagination(prev => ({ ...prev, page }));
    fetchTransactions({ page });
  }, [fetchTransactions]);

  const changeLimit = useCallback((limit) => {
    setPagination(prev => ({ ...prev, limit, page: 1 }));
    fetchTransactions({ limit, page: 1 });
  }, [fetchTransactions]);

  const resetFilters = useCallback(() => {
    setFilters(initialFilters);
    setPagination(prev => ({ ...prev, page: 1 }));
    fetchTransactions({ ...initialFilters, page: 1 });
  }, [initialFilters, fetchTransactions]);

  useEffect(() => {
    fetchTransactions();
  }, []);

  return {
    transactions,
    loading,
    error,
    pagination,
    filters,
    updateFilters,
    changePage,
    changeLimit,
    resetFilters,
    refetch: fetchTransactions
  };
};