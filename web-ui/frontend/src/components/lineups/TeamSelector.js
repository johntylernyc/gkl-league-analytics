import React from 'react';

const TeamSelector = ({ teams, selectedTeam, onTeamChange }) => {
  return (
    <div className="bg-white rounded-lg shadow px-4 py-3">
      <div className="flex items-center space-x-3">
        <svg className="h-5 w-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
        </svg>
        <label htmlFor="team-select" className="text-sm font-medium text-gray-700">
          Team:
        </label>
        <select
          id="team-select"
          value={selectedTeam || ''}
          onChange={(e) => onTeamChange(e.target.value || null)}
          className="flex-1 block px-3 py-1.5 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
        >
          <option value="">All Teams</option>
          {teams.map(team => (
            <option key={team.team_key} value={team.team_key}>
              {team.team_name}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
};

export default TeamSelector;