const express = require('express');
const router = express.Router();
const playerSpotlightService = require('../services/playerSpotlightService');

// GET /api/players/:playerId/spotlight - Get comprehensive player spotlight data
router.get('/:playerId/spotlight', async (req, res) => {
  try {
    const { playerId } = req.params;
    const { season = 2025 } = req.query;

    console.log(`Fetching player spotlight for player ${playerId}, season ${season}`);

    const spotlightData = await playerSpotlightService.getPlayerSpotlight(playerId, parseInt(season));
    
    res.json(spotlightData);
  } catch (error) {
    console.error('Error fetching player spotlight:', error);
    res.status(500).json({
      error: 'Failed to fetch player spotlight data',
      message: error.message
    });
  }
});

// GET /api/players/:playerId/timeline - Get player timeline data
router.get('/:playerId/timeline', async (req, res) => {
  try {
    const { playerId } = req.params;
    const { season = 2025, granularity = 'day' } = req.query;

    console.log(`Fetching player timeline for player ${playerId}, season ${season}, granularity ${granularity}`);

    const timelineData = await playerSpotlightService.getPlayerTimeline(
      playerId, 
      parseInt(season), 
      granularity
    );
    
    res.json({
      player_id: playerId,
      season: parseInt(season),
      granularity: granularity,
      timeline: timelineData
    });
  } catch (error) {
    console.error('Error fetching player timeline:', error);
    res.status(500).json({
      error: 'Failed to fetch player timeline data',
      message: error.message
    });
  }
});

// GET /api/players/:playerId/seasons - Get available seasons for player
router.get('/:playerId/seasons', async (req, res) => {
  try {
    const { playerId } = req.params;

    console.log(`Fetching available seasons for player ${playerId}`);

    const seasons = await playerSpotlightService.getAvailableSeasons(playerId);
    
    res.json({
      player_id: playerId,
      seasons: seasons
    });
  } catch (error) {
    console.error('Error fetching player seasons:', error);
    res.status(500).json({
      error: 'Failed to fetch player seasons',
      message: error.message
    });
  }
});

// GET /api/players/search - Search players for autocomplete
router.get('/search', async (req, res) => {
  try {
    const { q: query, limit = 10 } = req.query;

    if (!query || query.trim().length < 2) {
      return res.json({ players: [] });
    }

    console.log(`Searching players with query: ${query}`);

    const players = await playerSpotlightService.searchPlayers(query.trim(), parseInt(limit));
    
    res.json({
      query: query,
      players: players
    });
  } catch (error) {
    console.error('Error searching players:', error);
    res.status(500).json({
      error: 'Failed to search players',
      message: error.message
    });
  }
});

module.exports = router;