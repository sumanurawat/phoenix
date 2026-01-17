import { useState } from 'react';
import { api, endpoints } from '../../services/api';
import { useTokenBalance } from '../../hooks/useTokenBalance';

type SendTokensProps = {
  recipientUsername: string;
  onSuccess?: (newBalance: number) => void;
};

/**
 * SendTokens - Component for sending tokens to another user
 *
 * After a successful transfer, it updates the global token balance
 * so the Header and other components reflect the new balance immediately.
 */
export const SendTokens = ({ recipientUsername, onSuccess }: SendTokensProps) => {
  const { updateBalance } = useTokenBalance();
  const [amount, setAmount] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const handleIncrement = () => {
    setAmount((prev) => Math.min(prev + 1, 10000));
    setError(null);
    setSuccess(null);
  };

  const handleDecrement = () => {
    setAmount((prev) => Math.max(prev - 1, 0));
    setError(null);
    setSuccess(null);
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    // Allow empty string for clearing
    if (value === '') {
      setAmount(0);
      return;
    }
    // Parse and validate
    const parsed = parseInt(value, 10);
    if (!isNaN(parsed) && parsed >= 0 && parsed <= 10000) {
      setAmount(parsed);
    }
    setError(null);
    setSuccess(null);
  };

  const handleSend = async () => {
    // Validate amount
    if (amount <= 0) {
      setError('Please enter an amount greater than 0');
      return;
    }

    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      const response = await api.post(endpoints.transferTokens, {
        recipientUsername,
        amount,
      });

      if (response.data.success) {
        setSuccess(response.data.message || `Sent ${amount} tokens to @${recipientUsername}`);
        setAmount(0);

        // Update global token balance so Header reflects the change immediately
        if (typeof response.data.newBalance === 'number') {
          updateBalance(response.data.newBalance);
        }

        if (onSuccess) {
          onSuccess(response.data.newBalance);
        }
      } else {
        setError(response.data.error || 'Transfer failed');
      }
    } catch (err: any) {
      const errorMessage = err.response?.data?.error || 'Failed to send tokens. Please try again.';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col gap-3">
      {/* Token Amount Selector */}
      <div className="flex items-center gap-3">
        {/* Decrement Button */}
        <button
          type="button"
          onClick={handleDecrement}
          disabled={amount <= 0 || loading}
          className="w-10 h-10 rounded-full bg-momo-gray-700 hover:bg-momo-gray-600 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center transition-colors"
          aria-label="Decrease amount"
        >
          <svg className="w-5 h-5 text-momo-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 12H4" />
          </svg>
        </button>

        {/* Amount Input */}
        <div className="relative flex-1 max-w-[120px]">
          <input
            type="number"
            min="0"
            max="10000"
            value={amount}
            onChange={handleInputChange}
            disabled={loading}
            className="w-full px-3 py-2 bg-momo-gray-800 border border-momo-gray-600 rounded-lg text-center text-lg font-bold text-momo-white focus:outline-none focus:ring-2 focus:ring-momo-purple focus:border-transparent disabled:opacity-50 [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
            aria-label="Token amount"
          />
          <div className="absolute inset-y-0 right-3 flex items-center pointer-events-none">
            <svg className="w-4 h-4 text-momo-gold" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 2L2 7v10c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V7l-10-5z"/>
            </svg>
          </div>
        </div>

        {/* Increment Button */}
        <button
          type="button"
          onClick={handleIncrement}
          disabled={amount >= 10000 || loading}
          className="w-10 h-10 rounded-full bg-momo-gray-700 hover:bg-momo-gray-600 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center transition-colors"
          aria-label="Increase amount"
        >
          <svg className="w-5 h-5 text-momo-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
        </button>

        {/* Send Button */}
        <button
          type="button"
          onClick={handleSend}
          disabled={amount <= 0 || loading}
          className="px-4 py-2 bg-momo-purple hover:bg-momo-purple/80 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg font-semibold text-white transition-colors flex items-center gap-2"
        >
          {loading ? (
            <>
              <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Sending...
            </>
          ) : (
            <>
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              Send Tokens
            </>
          )}
        </button>
      </div>

      {/* Error Message */}
      {error && (
        <div className="px-3 py-2 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm">
          {error}
        </div>
      )}

      {/* Success Message */}
      {success && (
        <div className="px-3 py-2 bg-green-500/10 border border-green-500/30 rounded-lg text-green-400 text-sm">
          {success}
        </div>
      )}
    </div>
  );
};
