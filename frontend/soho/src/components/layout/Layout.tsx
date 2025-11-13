import type { ReactNode } from 'react';
import { Header } from './Header';

interface LayoutProps {
  children: ReactNode;
}

export const Layout = ({ children }: LayoutProps) => {
  return (
    <div className="min-h-screen bg-momo-gray-900 text-momo-white">
      <Header />
      <main className="pb-12">
        {children}
      </main>
    </div>
  );
};
