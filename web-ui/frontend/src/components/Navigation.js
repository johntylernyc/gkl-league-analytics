import React, { useState, useEffect, useRef } from 'react';
import { Link, useLocation } from 'react-router-dom';

const Navigation = () => {
  const location = useLocation();
  const [isDatabaseMenuOpen, setIsDatabaseMenuOpen] = useState(false);
  const dropdownRef = useRef(null);

  const navigation = [
    { name: 'Home', href: '/' },
    { name: 'Daily Lineups', href: '/lineups' },
    { name: 'Analytics', href: '/analytics' },
    { name: 'Managers', href: '/managers' },
  ];

  const databaseSearchItems = [
    { name: 'Transactions', href: '/transactions' },
    { name: 'Players', href: '/players' },
  ];

  const isActive = (href) => {
    if (href === '/') {
      return location.pathname === '/';
    }
    return location.pathname.startsWith(href);
  };

  const isDatabaseSearchActive = () => {
    return databaseSearchItems.some(item => location.pathname.startsWith(item.href));
  };

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsDatabaseMenuOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  return (
    <nav className="bg-white shadow-sm border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          <div className="flex">
            <div className="flex-shrink-0 flex items-center">
              <h1 className="text-xl font-bold text-gray-900">
                GKL League Analytics
              </h1>
            </div>
            <div className="hidden sm:ml-6 sm:flex sm:space-x-8">
              {navigation.map((item) => (
                <Link
                  key={item.name}
                  to={item.href}
                  className={`${
                    isActive(item.href)
                      ? 'border-primary-500 text-primary-600'
                      : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
                  } inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium transition-colors`}
                >
                  {item.name}
                </Link>
              ))}
              
              <div className="relative" ref={dropdownRef}>
                <button
                  onClick={() => setIsDatabaseMenuOpen(!isDatabaseMenuOpen)}
                  className={`${
                    isDatabaseSearchActive()
                      ? 'border-primary-500 text-primary-600'
                      : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
                  } inline-flex items-center px-1 pt-1 pb-1 border-b-2 text-sm font-medium transition-colors h-16`}
                >
                  Database Search
                  <svg
                    className={`ml-1 h-4 w-4 transition-transform ${isDatabaseMenuOpen ? 'rotate-180' : ''}`}
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </button>
                
                {isDatabaseMenuOpen && (
                  <div className="absolute top-full left-0 mt-1 w-48 bg-white shadow-lg border border-gray-200 rounded-md z-50">
                    {databaseSearchItems.map((item) => (
                      <Link
                        key={item.name}
                        to={item.href}
                        onClick={() => setIsDatabaseMenuOpen(false)}
                        className={`${
                          isActive(item.href)
                            ? 'bg-primary-50 text-primary-600'
                            : 'text-gray-700 hover:bg-gray-50'
                        } block px-4 py-2 text-sm transition-colors first:rounded-t-md last:rounded-b-md`}
                      >
                        {item.name}
                      </Link>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
          <div className="flex items-center">
            <div className="text-sm text-gray-500">
              Fantasy Baseball Analytics
            </div>
          </div>
        </div>
      </div>
    </nav>
  );
};

export default Navigation;