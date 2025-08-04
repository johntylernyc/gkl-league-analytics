-- ============================================
-- Add Progress Tracking to Job Log Table
-- ============================================
-- 
-- This migration adds a progress_pct field to the job_log table
-- to support real-time progress tracking for long-running jobs
--
-- Created: 2025-08-03
-- ============================================

-- Add progress_pct column to job_log table
-- This column tracks the completion percentage (0-100) of a job
ALTER TABLE job_log ADD COLUMN progress_pct REAL DEFAULT 0.0;

-- Add constraint to ensure progress_pct is between 0 and 100
-- Note: SQLite doesn't support adding CHECK constraints to existing columns,
-- so this is for documentation purposes. The application layer should validate.
-- CHECK (progress_pct >= 0.0 AND progress_pct <= 100.0)

-- Update existing completed jobs to have 100% progress
UPDATE job_log 
SET progress_pct = 100.0 
WHERE status = 'completed';

-- Update existing failed jobs to retain their last progress value
-- (no action needed as they'll keep their default 0.0 or last updated value)

-- ============================================
-- Optional: Add additional tracking fields
-- ============================================

-- Add last_checkpoint column for tracking checkpoint timestamps
ALTER TABLE job_log ADD COLUMN last_checkpoint TIMESTAMP;

-- Add estimated_completion column for ETA calculations
ALTER TABLE job_log ADD COLUMN estimated_completion TIMESTAMP;

-- Create index on progress_pct for efficient progress queries
CREATE INDEX IF NOT EXISTS idx_job_log_progress ON job_log(progress_pct);

-- Create index on status and progress for monitoring queries
CREATE INDEX IF NOT EXISTS idx_job_log_status_progress ON job_log(status, progress_pct);

-- ============================================
-- Verification Query
-- ============================================
-- Run this to verify the migration:
-- SELECT name, type, sql FROM sqlite_master WHERE type='table' AND name='job_log';