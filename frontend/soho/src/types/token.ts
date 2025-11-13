export interface TokenPackage {
  id: string;
  name: string;
  tokens: number;
  price: number;
  bonus: number;
  description?: string;
  badge?: string | null;
  available?: boolean;
}

export interface Transaction {
  id: string;
  type: 'purchase' | 'creation' | 'refund' | 'generation_spend' | 'generation_refund' | 'signup_bonus' | 'tip_sent' | 'tip_received' | 'admin_credit';
  amount: number;
  description?: string;
  timestamp: string;  // ISO date string from backend
  details?: {
    [key: string]: unknown;
  };
  balanceAfter?: number;
}

export interface TokenBalance {
  balance: number;
}
