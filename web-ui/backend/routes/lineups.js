const express = require('express');
const router = express.Router();
const lineupService = require('../services/lineupService');

// Get available dates with lineup data
router.get('/dates', async (req, res) => {
  try {
    const dates = await lineupService.getAvailableDates();
    res.json(dates);
  } catch (error) {
    console.error('Error fetching lineup dates:', error);
    res.status(500).json({ error: 'Failed to fetch lineup dates' });
  }
});

// Get all teams
router.get('/teams', async (req, res) => {
  try {
    const teams = await lineupService.getTeams();
    res.json(teams);
  } catch (error) {
    console.error('Error fetching teams:', error);
    res.status(500).json({ error: 'Failed to fetch teams' });
  }
});

// Get lineups for a specific date
router.get('/date/:date', async (req, res) => {
  try {
    const { date } = req.params;
    const { teamKey } = req.query;
    
    const lineups = await lineupService.getLineupsByDate(date, teamKey);
    res.json(lineups);
  } catch (error) {
    console.error('Error fetching lineups:', error);
    res.status(500).json({ error: 'Failed to fetch lineups' });
  }
});

// Get lineup for a specific team on a specific date
router.get('/date/:date/team/:teamKey', async (req, res) => {
  try {
    const { date, teamKey } = req.params;
    const lineup = await lineupService.getTeamLineup(date, teamKey);
    res.json(lineup);
  } catch (error) {
    console.error('Error fetching team lineup:', error);
    res.status(500).json({ error: 'Failed to fetch team lineup' });
  }
});

// Get player usage history
router.get('/player/:playerId', async (req, res) => {
  try {
    const { playerId } = req.params;
    const { startDate, endDate } = req.query;
    
    const history = await lineupService.getPlayerHistory(playerId, startDate, endDate);
    res.json(history);
  } catch (error) {
    console.error('Error fetching player history:', error);
    res.status(500).json({ error: 'Failed to fetch player history' });
  }
});

// Get lineup summary for a date
router.get('/summary/:date', async (req, res) => {
  try {
    const { date } = req.params;
    const summary = await lineupService.getDailySummary(date);
    res.json(summary);
  } catch (error) {
    console.error('Error fetching lineup summary:', error);
    res.status(500).json({ error: 'Failed to fetch lineup summary' });
  }
});

// Search players
router.get('/search', async (req, res) => {
  try {
    const { q } = req.query;
    
    if (!q || q.length < 2) {
      return res.json([]);
    }
    
    const players = await lineupService.searchPlayers(q);
    res.json(players);
  } catch (error) {
    console.error('Error searching players:', error);
    res.status(500).json({ error: 'Failed to search players' });
  }
});

module.exports = router;