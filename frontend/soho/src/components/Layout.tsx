import { ReactNode } from 'react';
import { Header } from './Header';
import { User } from '../types';

interface LayoutProps {
  children: ReactNode;
  user: User | null;
}

export function Layout({ children, user }: LayoutProps) {
  return (
    <div className="min-h-screen bg-dark-bg">
      <Header user={user} />
      <main className="max-w-7xl mx-auto">
        {children}
      </main>
    </div>
  );
}
