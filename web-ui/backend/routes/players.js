const express = require('express');
const router = express.Router();
const playerService = require('../services/playerService');

// GET /api/player-search/search - Search players with filters
router.get('/search', async (req, res) => {
  try {
    const result = await playerService.searchPlayers(req.query);
    res.json(result);
  } catch (error) {
    console.error('Error searching players:', error);
    res.status(500).json({ 
      error: 'Failed to search players',
      message: error.message 
    });
  }
});

// GET /api/player-search/positions - Get available positions
router.get('/positions', async (req, res) => {
  try {
    const positions = await playerService.getPositions();
    res.json(positions);
  } catch (error) {
    console.error('Error fetching positions:', error);
    res.status(500).json({ 
      error: 'Failed to fetch positions',
      message: error.message 
    });
  }
});

// GET /api/player-search/teams - Get MLB teams
router.get('/teams', async (req, res) => {
  try {
    const teams = await playerService.getMlbTeams();
    res.json(teams);
  } catch (error) {
    console.error('Error fetching MLB teams:', error);
    res.status(500).json({ 
      error: 'Failed to fetch MLB teams',
      message: error.message 
    });
  }
});

// GET /api/player-search/gkl-teams - Get GKL fantasy teams
router.get('/gkl-teams', async (req, res) => {
  try {
    const teams = await playerService.getGklTeams();
    res.json(teams);
  } catch (error) {
    console.error('Error fetching GKL teams:', error);
    res.status(500).json({ 
      error: 'Failed to fetch GKL teams',
      message: error.message 
    });
  }
});

// GET /api/player-search/:id - Get player details by ID
router.get('/:id', async (req, res) => {
  try {
    const player = await playerService.getPlayerById(req.params.id);
    if (!player) {
      return res.status(404).json({ error: 'Player not found' });
    }
    res.json(player);
  } catch (error) {
    console.error('Error fetching player details:', error);
    res.status(500).json({ 
      error: 'Failed to fetch player details',
      message: error.message 
    });
  }
});

module.exports = router;