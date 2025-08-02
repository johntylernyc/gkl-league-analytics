import React from 'react';

const Layout = ({ children }) => {
  return (
    <main className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
      {children}
    </main>
  );
};

export default Layout;