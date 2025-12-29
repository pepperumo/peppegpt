#!/usr/bin/env python3
"""
Docker entrypoint for RAG Pipeline that supports both continuous and single-run modes.

This entrypoint integrates:
- Local file watching (Local_Files pipeline)
- Google Drive file watching (Google_Drive pipeline)
- Web sources processing (crawls pending URLs from web_sources table)
"""
import os
import sys
import argparse
import asyncio
import json
import time
from pathlib import Path
from typing import Dict, Any

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Add common directory to Python path for web sources processor
common_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'common')
sys.path.insert(0, common_dir)

def run_single_check(pipeline_type: str, **kwargs) -> Dict[str, Any]:
    """
    Run a single check cycle for the specified pipeline.
    
    Args:
        pipeline_type: 'local' or 'google_drive'
        **kwargs: Additional arguments for watcher initialization
        
    Returns:
        Dict containing run statistics
    """
    start_time = time.time()
    
    try:
        if pipeline_type == 'local':
            # Change to Local_Files directory for proper imports
            local_files_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Local_Files')
            os.chdir(local_files_dir)
            sys.path.insert(0, local_files_dir)
            
            from file_watcher import LocalFileWatcher
            
            watcher = LocalFileWatcher(
                watch_directory=kwargs.get('directory'),
                config_path=kwargs.get('config', 'config.json')
            )
            
            # Perform single check
            stats = watcher.check_for_changes()
            
        elif pipeline_type == 'google_drive':
            # Change to Google_Drive directory for proper imports
            google_drive_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Google_Drive')
            os.chdir(google_drive_dir)
            sys.path.insert(0, google_drive_dir)
            
            from drive_watcher import GoogleDriveWatcher
            
            watcher = GoogleDriveWatcher(
                config_path=kwargs.get('config', 'config.json')
            )
            
            # Perform single check
            stats = watcher.check_for_changes()
            
        else:
            raise ValueError(f"Unknown pipeline type: {pipeline_type}")
        
        # Add pipeline metadata to stats
        stats['pipeline_type'] = pipeline_type
        stats['run_mode'] = 'single'
        stats['total_duration'] = time.time() - start_time
        
        return stats
        
    except Exception as e:
        return {
            'pipeline_type': pipeline_type,
            'run_mode': 'single', 
            'files_processed': 0,
            'files_deleted': 0,
            'errors': 1,
            'duration': 0.0,
            'total_duration': time.time() - start_time,
            'error_message': str(e)
        }


async def process_web_sources() -> Dict[str, Any]:
    """
    Process pending web sources from the web_sources table.

    Returns:
        Dict containing web sources processing statistics
    """
    start_time = time.time()

    try:
        # Import the web sources processor
        from common.web_sources_processor import process_pending_web_sources

        print("\n--- Processing Web Sources ---")
        result = await process_pending_web_sources()

        stats = {
            'sources_processed': result.sources_processed,
            'sources_failed': result.sources_failed,
            'total_chunks_created': result.total_chunks_created,
            'errors': len(result.errors),
            'error_messages': result.errors[:5] if result.errors else [],  # Limit to first 5 errors
            'duration': result.duration_seconds,
            'total_duration': time.time() - start_time
        }

        print(f"Web sources processing completed: {result.sources_processed} processed, "
              f"{result.sources_failed} failed, {result.total_chunks_created} chunks created")

        return stats

    except ImportError as e:
        print(f"Warning: Could not import web sources processor: {e}")
        return {
            'sources_processed': 0,
            'sources_failed': 0,
            'total_chunks_created': 0,
            'errors': 1,
            'error_messages': [f"Import error: {str(e)}"],
            'duration': 0.0,
            'total_duration': time.time() - start_time
        }
    except Exception as e:
        print(f"Error processing web sources: {e}")
        return {
            'sources_processed': 0,
            'sources_failed': 0,
            'total_chunks_created': 0,
            'errors': 1,
            'error_messages': [str(e)],
            'duration': 0.0,
            'total_duration': time.time() - start_time
        }


def run_continuous_loop(pipeline_type: str, interval: int, **kwargs) -> None:
    """
    Run continuous loop that checks files and processes web sources.

    This replaces the delegation to main modules to allow web sources
    processing after each file check cycle.

    Args:
        pipeline_type: 'local' or 'google_drive'
        interval: Interval in seconds between checks
        **kwargs: Additional arguments for watcher initialization
    """
    print(f"Starting continuous mode for {pipeline_type} pipeline (interval: {interval}s)")
    print("Press Ctrl+C to stop")

    iteration = 0

    try:
        while True:
            iteration += 1
            print(f"\n{'='*60}")
            print(f"Iteration {iteration} - {time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'='*60}")

            # Run file check
            print(f"\n--- Processing {pipeline_type.replace('_', ' ').title()} Files ---")
            file_stats = run_single_check(pipeline_type, **kwargs)

            # Log file processing results
            if file_stats.get('error_message'):
                print(f"File processing error: {file_stats['error_message']}")
            else:
                print(f"Files processed: {file_stats.get('files_processed', 0)}, "
                      f"deleted: {file_stats.get('files_deleted', 0)}, "
                      f"errors: {file_stats.get('errors', 0)}")

            # Process web sources
            web_stats = asyncio.run(process_web_sources())

            # Combined summary
            print(f"\n--- Iteration {iteration} Summary ---")
            print(f"Files: {file_stats.get('files_processed', 0)} processed, "
                  f"{file_stats.get('files_deleted', 0)} deleted")
            print(f"Web sources: {web_stats.get('sources_processed', 0)} processed, "
                  f"{web_stats.get('sources_failed', 0)} failed, "
                  f"{web_stats.get('total_chunks_created', 0)} chunks")
            print(f"Total duration: {file_stats.get('total_duration', 0):.2f}s (files) + "
                  f"{web_stats.get('total_duration', 0):.2f}s (web)")

            # Wait for next iteration
            print(f"\nWaiting {interval} seconds until next check...")
            time.sleep(interval)

    except KeyboardInterrupt:
        print(f"\n\nStopping continuous mode after {iteration} iterations")


def main():
    parser = argparse.ArgumentParser(description='RAG Pipeline Docker Entrypoint')
    parser.add_argument('--pipeline', type=str, choices=['local', 'google_drive'], 
                        default=os.getenv('RAG_PIPELINE_TYPE', 'local'), 
                        help='Which pipeline to run (can be overridden with RAG_PIPELINE_TYPE env var)')
    parser.add_argument('--mode', type=str, choices=['continuous', 'single'], 
                        default=os.getenv('RUN_MODE', 'continuous'), 
                        help='Run mode: continuous or single check (can be overridden with RUN_MODE env var)')
    parser.add_argument('--config', type=str, help='Path to configuration file')
    parser.add_argument('--directory', type=str, 
                        default=os.getenv('RAG_WATCH_DIRECTORY'), 
                        help='Directory to watch (for local pipeline, can be overridden with RAG_WATCH_DIRECTORY env var)')
    parser.add_argument('--interval', type=int, default=60, 
                        help='Interval in seconds between checks (continuous mode only)')
    
    args = parser.parse_args()
    
    # Set default config paths if not provided
    if not args.config:
        if args.pipeline == 'local':
            args.config = 'config.json'  # Will be relative to Local_Files directory
        elif args.pipeline == 'google_drive':
            args.config = 'config.json'  # Will be relative to Google_Drive directory
    
    # Import the appropriate pipeline
    if args.pipeline == 'local':
        # Change to Local_Files directory for proper imports
        local_files_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Local_Files')
        os.chdir(local_files_dir)
        sys.path.insert(0, local_files_dir)

        from file_watcher import LocalFileWatcher

        if args.mode == 'single':
            # Single run mode - perform one check and exit
            print(f"Running {args.pipeline} pipeline in single-run mode...")

            # Process files
            file_stats = run_single_check(
                'local',
                directory=args.directory,
                config=args.config
            )

            # Process web sources
            print("\n--- Processing Web Sources (Single Run) ---")
            web_stats = asyncio.run(process_web_sources())

            # Combine statistics
            combined_stats = {
                'files': file_stats,
                'web_sources': web_stats,
                'pipeline_type': args.pipeline,
                'run_mode': 'single'
            }

            # Output statistics as JSON for monitoring
            print(f"\nRun Statistics:")
            print(json.dumps(combined_stats, indent=2))

            # Determine exit code based on file processing errors
            # (web sources errors are logged but don't fail the pipeline)
            if file_stats['errors'] > 0:
                if 'error_message' in file_stats and ('auth' in file_stats['error_message'].lower() or 'credential' in file_stats['error_message'].lower()):
                    print("\nExiting with code 3: Authentication error")
                    sys.exit(3)
                elif 'config' in file_stats.get('error_message', '').lower():
                    print("\nExiting with code 2: Configuration error")
                    sys.exit(2)
                else:
                    print("\nExiting with code 1: Runtime error (retry recommended)")
                    sys.exit(1)
            else:
                print("\nExiting with code 0: Success")
                sys.exit(0)
        else:
            # Continuous mode - run custom loop with web sources processing
            run_continuous_loop(
                'local',
                interval=args.interval,
                directory=args.directory,
                config=args.config
            )

    elif args.pipeline == 'google_drive':
        # Change to Google_Drive directory for proper imports
        google_drive_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Google_Drive')
        os.chdir(google_drive_dir)
        sys.path.insert(0, google_drive_dir)

        from drive_watcher import GoogleDriveWatcher

        if args.mode == 'single':
            # Single run mode - perform one check and exit
            print(f"Running {args.pipeline} pipeline in single-run mode...")

            # Process files
            file_stats = run_single_check(
                'google_drive',
                config=args.config
            )

            # Process web sources
            print("\n--- Processing Web Sources (Single Run) ---")
            web_stats = asyncio.run(process_web_sources())

            # Combine statistics
            combined_stats = {
                'files': file_stats,
                'web_sources': web_stats,
                'pipeline_type': args.pipeline,
                'run_mode': 'single'
            }

            # Output statistics as JSON for monitoring
            print(f"\nRun Statistics:")
            print(json.dumps(combined_stats, indent=2))

            # Determine exit code based on file processing errors
            # (web sources errors are logged but don't fail the pipeline)
            if file_stats['errors'] > 0:
                if 'error_message' in file_stats and ('auth' in file_stats['error_message'].lower() or 'credential' in file_stats['error_message'].lower()):
                    print("\nExiting with code 3: Authentication error")
                    sys.exit(3)
                elif 'config' in file_stats.get('error_message', '').lower():
                    print("\nExiting with code 2: Configuration error")
                    sys.exit(2)
                else:
                    print("\nExiting with code 1: Runtime error (retry recommended)")
                    sys.exit(1)
            else:
                print("\nExiting with code 0: Success")
                sys.exit(0)
        else:
            # Continuous mode - run custom loop with web sources processing
            run_continuous_loop(
                'google_drive',
                interval=args.interval,
                config=args.config
            )

if __name__ == "__main__":
    main()