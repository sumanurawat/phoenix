/**
 * Re-export useTokenBalance from the global context
 *
 * This ensures all components share the same token balance state.
 * The TokenBalanceProvider in App.tsx manages the actual state.
 */
export { useTokenBalance } from '../contexts/TokenBalanceContext';
