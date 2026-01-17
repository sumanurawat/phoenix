import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import type { ReactNode } from 'react';
import { api, endpoints } from '../services/api';
import { useAuth } from '../hooks/useAuth';

/**
 * TokenBalanceContext - Global state for user's token balance
 *
 * This context ensures the token balance stays synchronized across all components.
 * When tokens are sent, received, or spent, call refreshBalance() or updateBalance()
 * and all components (Header, ProfilePage, TokensPage, etc.) update automatically.
 */

type TokenBalanceContextType = {
  balance: number;
  loading: boolean;
  refreshBalance: () => Promise<void>;
  updateBalance: (newBalance: number) => void;
  deductTokens: (amount: number) => void;
};

const TokenBalanceContext = createContext<TokenBalanceContextType | null>(null);

export const TokenBalanceProvider = ({ children }: { children: ReactNode }) => {
  const [balance, setBalance] = useState<number>(0);
  const [loading, setLoading] = useState(true);
  const { user } = useAuth();

  const fetchBalance = useCallback(async () => {
    if (!user) {
      setBalance(0);
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      const response = await api.get(endpoints.tokenBalance);
      setBalance(response.data.balance ?? 0);
    } catch (error) {
      console.error('Failed to fetch token balance:', error);
    } finally {
      setLoading(false);
    }
  }, [user]);

  // Fetch balance when user changes (login/logout)
  useEffect(() => {
    fetchBalance();
  }, [fetchBalance]);

  // Refresh balance from server
  const refreshBalance = useCallback(async () => {
    await fetchBalance();
  }, [fetchBalance]);

  // Immediately update balance (optimistic update)
  const updateBalance = useCallback((newBalance: number) => {
    setBalance(newBalance);
  }, []);

  // Deduct tokens locally (for optimistic UI updates)
  const deductTokens = useCallback((amount: number) => {
    setBalance((prev) => Math.max(0, prev - amount));
  }, []);

  return (
    <TokenBalanceContext.Provider
      value={{
        balance,
        loading,
        refreshBalance,
        updateBalance,
        deductTokens,
      }}
    >
      {children}
    </TokenBalanceContext.Provider>
  );
};

/**
 * Hook to access the global token balance
 *
 * Usage:
 *   const { balance, refreshBalance, updateBalance } = useTokenBalance();
 *
 * - balance: Current token count
 * - loading: True while fetching from server
 * - refreshBalance(): Fetch latest balance from server
 * - updateBalance(n): Set balance to specific value (after API confirms)
 * - deductTokens(n): Subtract tokens (optimistic update before API)
 */
export const useTokenBalance = () => {
  const context = useContext(TokenBalanceContext);

  // Fallback for components rendered outside the provider
  if (!context) {
    console.warn('useTokenBalance must be used within TokenBalanceProvider');
    return {
      balance: 0,
      loading: false,
      refreshBalance: async () => {},
      updateBalance: () => {},
      deductTokens: () => {},
    };
  }

  return context;
};
