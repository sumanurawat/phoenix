// User type definition
export interface User {
  uid: string;
  username: string;
  displayName?: string;
  bio?: string;
  profileImageUrl?: string;
  tokenBalance: number;
  totalTokensEarned: number;
  totalTokensPurchased: number;
}
