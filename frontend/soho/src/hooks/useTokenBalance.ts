import { useState, useEffect } from 'react';
import { api, endpoints } from '../services/api';

export const useTokenBalance = () => {
  const [balance, setBalance] = useState<number>(0);
  const [loading, setLoading] = useState(true);

  const fetchBalance = async () => {
    try {
      const response = await api.get(endpoints.tokenBalance);
      setBalance(response.data.balance);
    } catch (error) {
      console.error('Failed to fetch token balance:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchBalance();
  }, []);

  const refreshBalance = () => {
    setLoading(true);
    fetchBalance();
  };

  return { balance, loading, refreshBalance };
};
