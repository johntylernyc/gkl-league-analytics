import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Navigation from './components/Navigation';
import Layout from './components/Layout';
import TransactionExplorer from './pages/TransactionExplorer';
import Analytics from './pages/Analytics';
import Managers from './pages/Managers';
import Home from './pages/Home';
import './App.css';

function App() {
  return (
    <Router>
      <div className="App bg-gray-50 min-h-screen">
        <Navigation />
        <Layout>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/transactions" element={<TransactionExplorer />} />
            <Route path="/analytics" element={<Analytics />} />
            <Route path="/managers" element={<Managers />} />
          </Routes>
        </Layout>
      </div>
    </Router>
  );
}

export default App;