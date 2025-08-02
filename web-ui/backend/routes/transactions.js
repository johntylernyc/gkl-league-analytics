const express = require('express');
const router = express.Router();
const transactionService = require('../services/transactionService');

// GET /api/transactions - Get all transactions with filtering and pagination
router.get('/', async (req, res) => {
  try {
    const options = {
      page: parseInt(req.query.page) || 1,
      limit: parseInt(req.query.limit) || 50,
      search: req.query.search || '',
      transactionType: req.query.transactionType || '',
      movementType: req.query.movementType || '',
      startDate: req.query.startDate || '',
      endDate: req.query.endDate || '',
      teamName: req.query.teamName || '',
      playerName: req.query.playerName || '',
      playerPosition: req.query.playerPosition || ''
    };

    const result = await transactionService.getTransactions(options);
    res.json(result);
  } catch (error) {
    console.error('Error fetching transactions:', error);
    res.status(500).json({ 
      error: 'Failed to fetch transactions',
      message: error.message 
    });
  }
});

// GET /api/transactions/stats - Get transaction statistics
router.get('/stats', async (req, res) => {
  try {
    const stats = await transactionService.getStatistics();
    res.json(stats);
  } catch (error) {
    console.error('Error fetching transaction statistics:', error);
    res.status(500).json({ 
      error: 'Failed to fetch statistics',
      message: error.message 
    });
  }
});

// GET /api/transactions/filters - Get filter options
router.get('/filters', async (req, res) => {
  try {
    const filters = await transactionService.getFilterOptions();
    res.json(filters);
  } catch (error) {
    console.error('Error fetching filter options:', error);
    res.status(500).json({ 
      error: 'Failed to fetch filter options',
      message: error.message 
    });
  }
});

// GET /api/transactions/players/search - Search players for autocomplete
router.get('/players/search', async (req, res) => {
  try {
    const query = req.query.q || '';
    const limit = parseInt(req.query.limit) || 10;
    
    if (!query) {
      return res.json([]);
    }

    const players = await transactionService.searchPlayers(query, limit);
    res.json(players);
  } catch (error) {
    console.error('Error searching players:', error);
    res.status(500).json({ 
      error: 'Failed to search players',
      message: error.message 
    });
  }
});

module.exports = router;