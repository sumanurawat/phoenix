import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Layout } from '../components/layout/Layout';
import { useAuth } from '../hooks/useAuth';
import type { Transaction } from '../types/token';
import { api, endpoints } from '../services/api';

export const TransactionsPage = () => {
  const navigate = useNavigate();
  const { user, loading: authLoading } = useAuth();
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!authLoading && !user) {
      navigate('/login', { state: { from: '/transactions' } });
    }
  }, [authLoading, user, navigate]);

  useEffect(() => {
    // Only fetch if user is authenticated
    if (user) {
      fetchTransactions();
    }
  }, [user]);

  const fetchTransactions = async () => {
    try {
      const response = await api.get(endpoints.transactions);
      setTransactions(response.data.transactions || []);
    } catch (err) {
      console.error('Failed to fetch transactions:', err);
      setError('Failed to load transactions');
    } finally {
      setLoading(false);
    }
  };

  const formatTimestamp = (timestamp: number | string) => {
    // Handle both Unix timestamps (numbers) and ISO strings
    const date = typeof timestamp === 'string' ? new Date(timestamp) : new Date(timestamp);
    
    // Check if date is valid
    if (isNaN(date.getTime())) {
      return 'Invalid Date';
    }
    
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const getTransactionIcon = (type: string) => {
    switch (type) {
      case 'purchase':
        return (
          <div className="w-10 h-10 rounded-full bg-momo-green/20 flex items-center justify-center">
            <svg className="w-5 h-5 text-momo-green" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
            </svg>
          </div>
        );
      case 'creation':
        return (
          <div className="w-10 h-10 rounded-full bg-momo-purple/20 flex items-center justify-center">
            <svg className="w-5 h-5 text-momo-purple" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </div>
        );
      case 'refund':
        return (
          <div className="w-10 h-10 rounded-full bg-momo-blue/20 flex items-center justify-center">
            <svg className="w-5 h-5 text-momo-blue" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h10a8 8 0 018 8v2M3 10l6 6m-6-6l6-6" />
            </svg>
          </div>
        );
      default:
        return (
          <div className="w-10 h-10 rounded-full bg-momo-gray-700 flex items-center justify-center">
            <svg className="w-5 h-5 text-momo-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
        );
    }
  };

  const getTransactionLabel = (type: string) => {
    switch (type) {
      case 'purchase':
        return 'Token Purchase';
      case 'creation':
        return 'AI Generation';
      case 'refund':
        return 'Refund';
      default:
        return 'Transaction';
    }
  };

  // Show loading while checking auth
  if (authLoading) {
    return (
      <Layout>
        <div className="flex items-center justify-center min-h-[60vh]">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-momo-purple"></div>
        </div>
      </Layout>
    );
  }

  // Don't render if not authenticated (will redirect)
  if (!user) {
    return null;
  }

  return (
    <Layout>
      <div className="max-w-4xl mx-auto px-4 py-8 space-y-8">
        {/* Header */}
        <div className="text-center">
          <h1 className="text-3xl font-bold">Transaction History</h1>
          <p className="text-momo-gray-400 mt-2">
            View all your token transactions
          </p>
        </div>

        {/* Loading State */}
        {loading && (
          <div className="space-y-4">
            {[1, 2, 3, 4, 5].map(i => (
              <div key={i} className="bg-momo-gray-800 rounded-xl p-4 animate-pulse flex items-center gap-4">
                <div className="w-10 h-10 rounded-full bg-momo-gray-700"></div>
                <div className="flex-1 space-y-2">
                  <div className="h-4 bg-momo-gray-700 rounded w-1/3"></div>
                  <div className="h-3 bg-momo-gray-700 rounded w-1/4"></div>
                </div>
                <div className="h-6 w-16 bg-momo-gray-700 rounded"></div>
              </div>
            ))}
          </div>
        )}

        {/* Error State */}
        {error && !loading && (
          <div className="bg-momo-red/10 border border-momo-red/20 rounded-lg p-4 text-center">
            <p className="text-momo-red font-semibold">{error}</p>
            <button
              onClick={fetchTransactions}
              className="mt-3 px-4 py-2 bg-momo-red text-white rounded-lg hover:bg-momo-red/80 transition-colors"
            >
              Try Again
            </button>
          </div>
        )}

        {/* Empty State */}
        {!loading && !error && transactions.length === 0 && (
          <div className="text-center py-16">
            <svg className="w-20 h-20 mx-auto text-momo-gray-600 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
            </svg>
            <p className="text-momo-gray-400 text-lg mb-2">
              No transactions yet
            </p>
            <p className="text-momo-gray-500 text-sm">
              Your transaction history will appear here
            </p>
          </div>
        )}

        {/* Transactions List */}
        {!loading && !error && transactions.length > 0 && (
          <div className="space-y-3">
            {transactions.map(transaction => (
              <div
                key={transaction.id}
                className="bg-momo-gray-800 rounded-xl p-4 hover:bg-momo-gray-750 transition-colors"
              >
                <div className="flex items-center gap-4">
                  {/* Icon */}
                  {getTransactionIcon(transaction.type)}

                  {/* Details */}
                  <div className="flex-1 min-w-0">
                    <p className="font-semibold truncate">
                      {getTransactionLabel(transaction.type)}
                    </p>
                    <p className="text-sm text-momo-gray-400">
                      {formatTimestamp(transaction.timestamp)}
                    </p>
                    {transaction.description && (
                      <p className="text-xs text-momo-gray-500 mt-1">
                        {transaction.description}
                      </p>
                    )}
                  </div>

                  {/* Amount */}
                  <div className="text-right">
                    <p className={`text-lg font-bold ${
                      transaction.amount > 0 ? 'text-momo-green' : 'text-momo-red'
                    }`}>
                      {transaction.amount > 0 ? '+' : ''}{transaction.amount}
                    </p>
                    <p className="text-xs text-momo-gray-500">tokens</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Summary Card */}
        {!loading && !error && transactions.length > 0 && (
          <div className="bg-momo-gray-800 rounded-xl p-6">
            <h2 className="text-lg font-bold mb-4">Summary</h2>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-momo-gray-400">Total Purchases</span>
                <span className="font-semibold text-momo-green">
                  +{transactions.filter(t => t.type === 'purchase').reduce((sum, t) => sum + t.amount, 0)} tokens
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-momo-gray-400">Total Spent</span>
                <span className="font-semibold text-momo-red">
                  -{transactions.filter(t => t.type === 'creation').reduce((sum, t) => sum + Math.abs(t.amount), 0)} tokens
                </span>
              </div>
              <div className="flex justify-between pt-3 border-t border-momo-gray-700">
                <span className="font-semibold">Net Change</span>
                <span className="font-bold text-momo-white">
                  {transactions.reduce((sum, t) => sum + t.amount, 0)} tokens
                </span>
              </div>
            </div>
          </div>
        )}
      </div>
    </Layout>
  );
};
