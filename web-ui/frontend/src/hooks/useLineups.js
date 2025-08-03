import { useState, useEffect, useCallback } from 'react';
import apiService from '../services/api';

export const useLineups = () => {
  const [lineups, setLineups] = useState([]);
  const [teams, setTeams] = useState([]);
  const [availableDates, setAvailableDates] = useState([]);
  const [selectedDate, setSelectedDate] = useState(null);
  const [selectedTeam, setSelectedTeam] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [summary, setSummary] = useState(null);

  // Fetch available dates on mount
  useEffect(() => {
    const fetchDates = async () => {
      try {
        const dates = await apiService.getLineupDates();
        setAvailableDates(dates);
        // Set current date as default, or most recent if current date not available
        if (dates && dates.length > 0) {
          const today = new Date().toISOString().split('T')[0];
          const hasToday = dates.includes(today);
          setSelectedDate(hasToday ? today : dates[0]);
        }
      } catch (err) {
        console.error('Failed to fetch dates:', err);
        setError('Failed to load available dates');
      }
    };

    fetchDates();
  }, []);

  // Fetch teams on mount
  useEffect(() => {
    const fetchTeams = async () => {
      try {
        const teamsData = await apiService.getTeams();
        setTeams(teamsData);
        // Set "All Teams" as default (null value)
        setSelectedTeam(null);
      } catch (err) {
        console.error('Failed to fetch teams:', err);
        setError('Failed to load teams');
      }
    };

    fetchTeams();
  }, []);

  // Fetch lineups when date or team changes
  useEffect(() => {
    if (!selectedDate) return;

    const fetchLineups = async () => {
      setLoading(true);
      setError(null);
      
      try {
        const [lineupsData, summaryData] = await Promise.all([
          selectedTeam 
            ? apiService.getTeamLineup(selectedDate, selectedTeam)
            : apiService.getLineupsByDate(selectedDate),
          apiService.getLineupSummary(selectedDate)
        ]);
        
        setLineups(selectedTeam ? [lineupsData] : lineupsData);
        setSummary(summaryData);
      } catch (err) {
        console.error('Failed to fetch lineups:', err);
        setError('Failed to load lineup data');
      } finally {
        setLoading(false);
      }
    };

    fetchLineups();
  }, [selectedDate, selectedTeam]);

  // Navigate to previous date
  const goToPreviousDate = useCallback(() => {
    const currentIndex = availableDates.indexOf(selectedDate);
    if (currentIndex < availableDates.length - 1) {
      setSelectedDate(availableDates[currentIndex + 1]);
    }
  }, [availableDates, selectedDate]);

  // Navigate to next date
  const goToNextDate = useCallback(() => {
    const currentIndex = availableDates.indexOf(selectedDate);
    if (currentIndex > 0) {
      setSelectedDate(availableDates[currentIndex - 1]);
    }
  }, [availableDates, selectedDate]);

  // Check if navigation is possible
  const canGoNext = selectedDate && availableDates.indexOf(selectedDate) > 0;
  const canGoPrevious = selectedDate && availableDates.indexOf(selectedDate) < availableDates.length - 1;

  // Search players
  const searchPlayers = useCallback(async (query) => {
    if (!query || query.length < 2) return [];
    
    try {
      return await apiService.searchLineupPlayers(query);
    } catch (err) {
      console.error('Failed to search players:', err);
      return [];
    }
  }, []);

  // Get player history
  const getPlayerHistory = useCallback(async (playerId, startDate, endDate) => {
    try {
      return await apiService.getPlayerHistory(playerId, startDate, endDate);
    } catch (err) {
      console.error('Failed to fetch player history:', err);
      throw err;
    }
  }, []);

  return {
    lineups,
    teams,
    availableDates,
    selectedDate,
    selectedTeam,
    loading,
    error,
    summary,
    setSelectedDate,
    setSelectedTeam,
    goToPreviousDate,
    goToNextDate,
    canGoNext,
    canGoPrevious,
    searchPlayers,
    getPlayerHistory
  };
};