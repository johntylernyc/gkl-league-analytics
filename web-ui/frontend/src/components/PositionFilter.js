import React from 'react';

const PositionFilter = ({ selectedPositions = [], availablePositions = [], onChange }) => {
  // Define position groups
  const batterPositions = ['C', '1B', '2B', '3B', 'SS', 'LF', 'CF', 'RF'];
  const pitcherPositions = ['SP', 'RP'];
  
  // Convert selectedPositions string to array if needed
  const selectedArray = typeof selectedPositions === 'string' 
    ? selectedPositions.split(',').filter(p => p) 
    : selectedPositions;

  const handlePositionToggle = (position) => {
    let newSelected;
    if (selectedArray.includes(position)) {
      // Remove position
      newSelected = selectedArray.filter(p => p !== position);
    } else {
      // Add position
      newSelected = [...selectedArray, position];
    }
    onChange(newSelected.join(','));
  };

  const handleGroupToggle = (groupPositions, groupName) => {
    const allGroupSelected = groupPositions.every(pos => selectedArray.includes(pos));
    
    let newSelected;
    if (allGroupSelected) {
      // Remove all group positions
      newSelected = selectedArray.filter(pos => !groupPositions.includes(pos));
    } else {
      // Add all group positions (but don't duplicate existing ones)
      const positionsToAdd = groupPositions.filter(pos => !selectedArray.includes(pos));
      newSelected = [...selectedArray, ...positionsToAdd];
    }
    onChange(newSelected.join(','));
  };

  const isPositionSelected = (position) => selectedArray.includes(position);
  
  const isGroupSelected = (groupPositions) => 
    groupPositions.length > 0 && groupPositions.every(pos => selectedArray.includes(pos));
  
  const isGroupPartiallySelected = (groupPositions) => 
    groupPositions.some(pos => selectedArray.includes(pos)) && 
    !groupPositions.every(pos => selectedArray.includes(pos));

  const getButtonClass = (isSelected, isPartial = false) => {
    const baseClass = "px-3 py-2 text-sm font-medium rounded-md border transition-colors duration-200";
    if (isSelected) {
      return `${baseClass} bg-blue-600 text-white border-blue-600 hover:bg-blue-700`;
    } else if (isPartial) {
      return `${baseClass} bg-blue-100 text-blue-800 border-blue-300 hover:bg-blue-200`;
    } else {
      return `${baseClass} bg-white text-gray-700 border-gray-300 hover:bg-gray-50`;
    }
  };

  // Filter available positions to only show those that exist in the data
  const visibleBatterPositions = batterPositions.filter(pos => availablePositions.includes(pos));
  const visiblePitcherPositions = pitcherPositions.filter(pos => availablePositions.includes(pos));

  return (
    <div className="space-y-3">
      {/* Group filters */}
      <div className="flex flex-wrap gap-2">
        {visibleBatterPositions.length > 0 && (
          <button
            type="button"
            onClick={() => handleGroupToggle(visibleBatterPositions, 'All Batters')}
            className={getButtonClass(
              isGroupSelected(visibleBatterPositions),
              isGroupPartiallySelected(visibleBatterPositions)
            )}
          >
            All Batters
          </button>
        )}
        {visiblePitcherPositions.length > 0 && (
          <button
            type="button"
            onClick={() => handleGroupToggle(visiblePitcherPositions, 'All Pitchers')}
            className={getButtonClass(
              isGroupSelected(visiblePitcherPositions),
              isGroupPartiallySelected(visiblePitcherPositions)
            )}
          >
            All Pitchers
          </button>
        )}
      </div>

      {/* Individual position filters */}
      <div className="flex flex-wrap gap-2">
        {availablePositions.map(position => (
          <button
            key={position}
            type="button"
            onClick={() => handlePositionToggle(position)}
            className={getButtonClass(isPositionSelected(position))}
          >
            {position}
          </button>
        ))}
      </div>

    </div>
  );
};

export default PositionFilter;