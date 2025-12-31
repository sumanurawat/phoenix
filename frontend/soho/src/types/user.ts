// User type definition
export interface User {
  uid: string;
  username?: string;  // Optional - new users may not have a username yet
  needsUsername?: boolean;  // True if user needs to set up their username
  displayName?: string;
  bio?: string;
  profileImageUrl?: string;
  tokenBalance: number;
  totalTokensEarned: number;
  totalTokensPurchased: number;
}
