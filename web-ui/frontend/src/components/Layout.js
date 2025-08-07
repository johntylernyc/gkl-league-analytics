import React from 'react';

const Layout = ({ children }) => {
  return (
    <div className="min-h-screen flex flex-col">
      <main className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8 flex-grow w-full">
        {children}
      </main>
      <footer className="bg-gray-50 border-t border-gray-200 mt-auto">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="text-center text-gray-500 text-sm">
            <p>Questions or feedback? Let us know on GitHub.</p>
            <p className="mt-2">
              <a 
                href="https://github.com/johntylernyc/gkl-league-analytics/issues" 
                target="_blank" 
                rel="noopener noreferrer"
                className="text-blue-600 hover:text-blue-800 font-medium"
              >
                Report an Issue
              </a>
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default Layout;