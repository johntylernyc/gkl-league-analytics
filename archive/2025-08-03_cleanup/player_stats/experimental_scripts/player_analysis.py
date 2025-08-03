#!/usr/bin/env python3
"""
Player Analysis and ID Mapping Preparation

Analyzes unique players across daily_lineups and daily_gkl_player_stats tables
to understand the current state and prepare for comprehensive ID mapping.

Key Functions:
- Extract all unique players from both data sources
- Analyze name patterns and team affiliations
- Identify potential matches for mapping
- Prepare data for pybaseball playerid_lookup integration
"""

import sys
import sqlite3
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import re

# Add parent directories to path
parent_dir = Path(__file__).parent
root_dir = parent_dir.parent
sys.path.insert(0, str(root_dir))


class PlayerAnalyzer:
    """Analyzes players across different data sources for ID mapping preparation."""
    
    def __init__(self, db_path: str = None):
        """Initialize analyzer with database connection."""
        if db_path is None:
            db_path = root_dir / "database" / "league_analytics.db"
        
        self.db_path = str(db_path)
        print(f"Initialized PlayerAnalyzer with database: {self.db_path}")
    
    def extract_lineup_players(self) -> pd.DataFrame:
        """Extract unique players from daily_lineups table."""
        conn = sqlite3.connect(self.db_path)
        
        query = """
        SELECT DISTINCT 
            player_id as yahoo_player_id,
            player_name as yahoo_player_name,
            player_team as team_code,
            eligible_positions as position_codes,
            COUNT(*) as lineup_appearances
        FROM daily_lineups 
        GROUP BY player_id, player_name, player_team, eligible_positions
        ORDER BY player_name
        """
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        print(f"Extracted {len(df)} unique players from daily_lineups")
        return df
    
    def extract_stats_players(self) -> pd.DataFrame:
        """Extract unique players from daily_gkl_player_stats table."""
        conn = sqlite3.connect(self.db_path)
        
        query = """
        SELECT DISTINCT 
            mlb_player_id,
            player_name as stats_player_name,
            team_code,
            position_codes,
            COUNT(*) as stats_appearances
        FROM daily_gkl_player_stats 
        GROUP BY mlb_player_id, player_name, team_code, position_codes
        ORDER BY player_name
        """
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        print(f"Extracted {len(df)} unique players from daily_gkl_player_stats")
        return df
    
    def standardize_name(self, name: str) -> str:
        """Standardize player names for better matching."""
        if not name:
            return ""
        
        # Remove common suffixes and prefixes
        name = re.sub(r'\s+(Jr\.?|Sr\.?|III|II|IV)$', '', name, flags=re.IGNORECASE)
        
        # Handle special characters and accents (basic cleanup)
        name = name.replace('á', 'a').replace('é', 'e').replace('í', 'i')
        name = name.replace('ó', 'o').replace('ú', 'u').replace('ñ', 'n')
        name = name.replace('ü', 'u').replace('ç', 'c')
        
        # Convert to lowercase and clean up spacing
        name = ' '.join(name.lower().split())
        
        return name
    
    def analyze_name_overlap(self, lineup_df: pd.DataFrame, stats_df: pd.DataFrame) -> pd.DataFrame:
        """Analyze potential name-based matches between the two datasets."""
        
        # Standardize names for matching
        lineup_df['standardized_name'] = lineup_df['yahoo_player_name'].apply(self.standardize_name)
        stats_df['standardized_name'] = stats_df['stats_player_name'].apply(self.standardize_name)
        
        # Find exact name matches
        exact_matches = lineup_df.merge(
            stats_df, 
            on='standardized_name', 
            how='inner',
            suffixes=('_lineup', '_stats')
        )
        
        print(f"Found {len(exact_matches)} exact name matches")
        
        return exact_matches
    
    def analyze_team_patterns(self, lineup_df: pd.DataFrame, stats_df: pd.DataFrame) -> Dict:
        """Analyze team code patterns across both datasets."""
        
        lineup_teams = set(lineup_df['team_code'].dropna().unique())
        stats_teams = set(stats_df['team_code'].dropna().unique())
        
        analysis = {
            'lineup_teams': sorted(lineup_teams),
            'stats_teams': sorted(stats_teams),
            'common_teams': sorted(lineup_teams.intersection(stats_teams)),
            'lineup_only': sorted(lineup_teams - stats_teams),
            'stats_only': sorted(stats_teams - lineup_teams)
        }
        
        print(f"Team analysis:")
        print(f"  Lineup teams: {len(analysis['lineup_teams'])}")
        print(f"  Stats teams: {len(analysis['stats_teams'])}")
        print(f"  Common teams: {len(analysis['common_teams'])}")
        print(f"  Lineup-only teams: {len(analysis['lineup_only'])}")
        print(f"  Stats-only teams: {len(analysis['stats_only'])}")
        
        return analysis
    
    def generate_mapping_candidates(self) -> pd.DataFrame:
        """Generate comprehensive mapping candidates for player ID resolution."""
        
        print("=== PLAYER ANALYSIS AND MAPPING PREPARATION ===")
        
        # Extract players from both sources
        lineup_players = self.extract_lineup_players()
        stats_players = self.extract_stats_players()
        
        # Analyze overlaps
        name_matches = self.analyze_name_overlap(lineup_players, stats_players)
        team_analysis = self.analyze_team_patterns(lineup_players, stats_players)
        
        # Prepare comprehensive mapping dataset
        mapping_candidates = []
        
        # Add exact name matches with high confidence
        for _, match in name_matches.iterrows():
            candidate = {
                'yahoo_player_id': match['yahoo_player_id'],
                'yahoo_player_name': match['yahoo_player_name'],
                'mlb_player_id': str(match['mlb_player_id']),
                'standardized_name': match['standardized_name'],
                'team_code': match['team_code_lineup'] or match['team_code_stats'],
                'position_codes': match['position_codes_lineup'] or match['position_codes_stats'],
                'confidence_score': 0.95,  # High confidence for exact name match
                'mapping_method': 'exact_name_match',
                'needs_validation': False
            }
            mapping_candidates.append(candidate)
        
        # Add lineup players without matches (need pybaseball lookup)
        matched_yahoo_ids = set(name_matches['yahoo_player_id'])
        unmatched_lineup = lineup_players[~lineup_players['yahoo_player_id'].isin(matched_yahoo_ids)]
        
        for _, player in unmatched_lineup.iterrows():
            candidate = {
                'yahoo_player_id': player['yahoo_player_id'],
                'yahoo_player_name': player['yahoo_player_name'],
                'mlb_player_id': None,
                'standardized_name': self.standardize_name(player['yahoo_player_name']),
                'team_code': player['team_code'],
                'position_codes': player['position_codes'],
                'confidence_score': 0.0,
                'mapping_method': 'needs_pybaseball_lookup',
                'needs_validation': True
            }
            mapping_candidates.append(candidate)
        
        # Add stats players without matches (may be bench/prospects)
        matched_mlb_ids = set(name_matches['mlb_player_id'].astype(str))
        unmatched_stats = stats_players[~stats_players['mlb_player_id'].astype(str).isin(matched_mlb_ids)]
        
        for _, player in unmatched_stats.iterrows():
            candidate = {
                'yahoo_player_id': None,
                'yahoo_player_name': None,
                'mlb_player_id': str(player['mlb_player_id']),
                'standardized_name': self.standardize_name(player['stats_player_name']),
                'team_code': player['team_code'],
                'position_codes': player['position_codes'],
                'confidence_score': 0.0,
                'mapping_method': 'stats_only_player',
                'needs_validation': True,
                'stats_player_name': player['stats_player_name']
            }
            mapping_candidates.append(candidate)
        
        candidates_df = pd.DataFrame(mapping_candidates)
        
        print(f"\n=== MAPPING CANDIDATES SUMMARY ===")
        print(f"Total candidates: {len(candidates_df)}")
        print(f"Exact matches: {len(candidates_df[candidates_df['mapping_method'] == 'exact_name_match'])}")
        print(f"Need pybaseball lookup: {len(candidates_df[candidates_df['mapping_method'] == 'needs_pybaseball_lookup'])}")
        print(f"Stats-only players: {len(candidates_df[candidates_df['mapping_method'] == 'stats_only_player'])}")
        
        return candidates_df
    
    def save_analysis_results(self, candidates_df: pd.DataFrame, output_path: str = None):
        """Save analysis results for further processing."""
        if output_path is None:
            output_path = root_dir / "player_stats" / "mapping_candidates.csv"
        
        candidates_df.to_csv(output_path, index=False)
        print(f"Saved mapping candidates to: {output_path}")
        
        # Also save summary statistics
        summary_path = str(output_path).replace('.csv', '_summary.txt')
        with open(summary_path, 'w') as f:
            f.write("=== PLAYER ID MAPPING ANALYSIS SUMMARY ===\n\n")
            f.write(f"Total mapping candidates: {len(candidates_df)}\n")
            f.write(f"High-confidence matches: {len(candidates_df[candidates_df['confidence_score'] >= 0.9])}\n")
            f.write(f"Need manual validation: {len(candidates_df[candidates_df['needs_validation']])}\n\n")
            
            f.write("Mapping Methods:\n")
            method_counts = candidates_df['mapping_method'].value_counts()
            for method, count in method_counts.items():
                f.write(f"  {method}: {count}\n")
        
        print(f"Saved analysis summary to: {summary_path}")


def main():
    """Run player analysis and generate mapping candidates."""
    analyzer = PlayerAnalyzer()
    candidates = analyzer.generate_mapping_candidates()
    analyzer.save_analysis_results(candidates)


if __name__ == "__main__":
    main()