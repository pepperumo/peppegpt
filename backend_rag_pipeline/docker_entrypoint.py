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


async def cleanup_orphaned_neo4j_data() -> None:
    """
    Clean up orphaned Neo4j data on pipeline startup.
    Compares Neo4j source_ids with Supabase document_metadata and deletes orphans.

    Note: Web source orphan cleanup is handled every iteration in web_sources_processor.py
    """
    from common.db_handler import supabase

    try:
        print("\n--- Checking for orphaned Neo4j data ---")

        # Get valid file_ids from Supabase document_metadata
        result = supabase.table('document_metadata').select('id').execute()
        valid_file_ids = [row['id'] for row in result.data] if result.data else []
        print(f"Found {len(valid_file_ids)} valid documents in Supabase")

        # Import and run cleanup
        try:
            from common.graph_utils import cleanup_orphaned_graph_data
            cleanup_result = await cleanup_orphaned_graph_data(valid_file_ids)
            if cleanup_result:
                orphan_count = cleanup_result.get('orphaned_source_ids', 0)
                if orphan_count > 0:
                    print(f"✓ Cleaned up {orphan_count} orphaned source(s) from Neo4j")
                else:
                    print("✓ No orphaned Neo4j data found")
            else:
                print("ℹ Neo4j/Graph not available - skipping orphan cleanup")
        except ImportError:
            print("ℹ Graph utilities not available - skipping orphan cleanup")

    except Exception as e:
        print(f"Warning: Could not check for orphaned Neo4j data: {e}")


def cleanup_incomplete_processing() -> list:
    """
    Check for and clean up files with incomplete processing (interrupted mid-chunking).

    Detects two scenarios:
    1. Metadata exists but no chunks (interrupted after metadata insert)
    2. Orphan chunks exist without metadata (interrupted before metadata or metadata deleted)

    Returns:
        List of file_ids that need reprocessing
    """
    from common.db_handler import supabase, delete_document_by_file_id

    files_to_reprocess = []

    try:
        print("\n--- Checking for incomplete file processing ---")

        # === Scenario 1: Metadata exists but no/few chunks ===
        # Get all file_ids from document_metadata
        metadata_result = supabase.table('document_metadata').select('id, title').execute()
        metadata_files = {row['id']: row['title'] for row in (metadata_result.data or [])}

        if metadata_files:
            # Get chunk counts per file_id
            docs_result = supabase.table('documents').select('metadata').execute()
            chunk_counts = {}
            for doc in docs_result.data or []:
                file_id = doc.get('metadata', {}).get('file_id')
                if file_id:
                    chunk_counts[file_id] = chunk_counts.get(file_id, 0) + 1

            # Find files with metadata but no chunks (incomplete processing)
            for file_id, title in metadata_files.items():
                if file_id not in chunk_counts or chunk_counts[file_id] == 0:
                    print(f"  ⚠ Found incomplete file: '{title}' (metadata exists, 0 chunks)")
                    # DON'T delete metadata - the file still exists in Drive
                    # Just mark for reprocessing by adding to list
                    # The reprocessing flow will handle cleanup and re-creation
                    files_to_reprocess.append(file_id)

                    # Delete any partial graph data that might exist
                    try:
                        from common.graph_utils import delete_document_from_graph
                        import asyncio
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        try:
                            loop.run_until_complete(delete_document_from_graph(file_id))
                            print(f"    ✓ Cleaned up any partial graph data for: {file_id}")
                        finally:
                            loop.close()
                    except ImportError:
                        pass  # Graph not available
                    except Exception as e:
                        print(f"    Note: Graph cleanup skipped: {e}")

        # === Scenario 2: Orphan chunks without metadata ===
        # Get all unique file_ids from chunks (excluding web sources)
        docs_result = supabase.table('documents').select('metadata').execute()
        chunk_file_ids = set()
        for doc in docs_result.data or []:
            metadata = doc.get('metadata', {})
            # Only check file-based chunks, not web sources
            if metadata.get('source_type') != 'web' and metadata.get('file_id'):
                chunk_file_ids.add(metadata['file_id'])

        # Find orphan chunks (file_id in chunks but not in metadata)
        orphan_file_ids = chunk_file_ids - set(metadata_files.keys())

        if orphan_file_ids:
            print(f"  ⚠ Found {len(orphan_file_ids)} orphan chunk group(s) without metadata")
            for file_id in orphan_file_ids:
                try:
                    # Delete orphan chunks
                    deleted_count = 0
                    while True:
                        select_resp = supabase.table("documents").select("id").eq(
                            "metadata->>file_id", file_id
                        ).limit(50).execute()

                        if not select_resp.data:
                            break

                        chunk_ids = [doc['id'] for doc in select_resp.data]
                        supabase.table("documents").delete().in_("id", chunk_ids).execute()
                        deleted_count += len(chunk_ids)

                    print(f"    ✓ Deleted {deleted_count} orphan chunks for: {file_id[:20]}...")
                    files_to_reprocess.append(file_id)
                except Exception as e:
                    print(f"    Warning: Could not delete orphan chunks for {file_id}: {e}")

        # === Scenario 3: Files in known_files but not in document_metadata ===
        # This can happen if cleanup ran but didn't update known_files (edge case)
        try:
            pipeline_id = os.getenv('RAG_PIPELINE_ID', 'prod-drive-pipeline')
            state_result = supabase.table('rag_pipeline_state').select('known_files').eq('pipeline_id', pipeline_id).execute()
            if state_result.data:
                known_files = state_result.data[0].get('known_files', {})
                # Get current metadata file_ids
                current_metadata_ids = set(metadata_files.keys())

                # Find files in known_files that aren't folders and aren't in metadata
                orphaned_known = []
                for file_id in list(known_files.keys()):
                    # Skip folder entries (they have specific modifiedTime patterns or we can check mime type)
                    # For now, check if it's NOT in metadata and NOT a folder by seeing if it was ever in metadata
                    if file_id not in current_metadata_ids and file_id not in chunk_file_ids:
                        # This file_id is tracked but has no data - might be orphaned or a folder
                        # Only remove non-folder file_ids (folders don't have chunks)
                        # We'll be conservative: only remove if there WERE chunks at some point (it was a real file)
                        pass  # Can't easily distinguish folders here, will rely on unknown file detection

                # Remove files_to_reprocess from known_files
                updated = False
                for file_id in files_to_reprocess:
                    if file_id in known_files:
                        del known_files[file_id]
                        updated = True

                # Also check for files in known_files that have no metadata and no chunks
                # These are orphaned entries that should be removed
                all_file_ids_with_data = current_metadata_ids | chunk_file_ids
                for file_id in list(known_files.keys()):
                    if file_id not in all_file_ids_with_data:
                        # Check if this looks like a file (not a folder) by checking if it was ever processed
                        # For safety, we'll remove it so it can be re-detected
                        del known_files[file_id]
                        files_to_reprocess.append(file_id)
                        updated = True
                        print(f"  ⚠ Found orphaned known_files entry: {file_id[:30]}... - removing for reprocessing")

                if updated:
                    supabase.table('rag_pipeline_state').update({
                        'known_files': known_files
                    }).eq('pipeline_id', pipeline_id).execute()
                    print(f"    ✓ Updated known_files state")
        except Exception as e:
            print(f"    Warning: Could not update known_files: {e}")

        if not files_to_reprocess:
            print("✓ No incomplete processing found")
        else:

            print(f"✓ Cleaned up {len(files_to_reprocess)} incomplete file(s) - will reprocess on next iteration")

        return files_to_reprocess

    except Exception as e:
        print(f"Warning: Could not check for incomplete processing: {e}")
        return []


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

    # Cleanup orphaned Neo4j data on startup (web sources cleaned every iteration)
    asyncio.run(cleanup_orphaned_neo4j_data())

    # Cleanup incomplete file processing on startup (interrupted mid-chunking)
    cleanup_incomplete_processing()

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

            # Process web sources (includes orphan cleanup)
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

            # Startup cleanups
            asyncio.run(cleanup_orphaned_neo4j_data())
            cleanup_incomplete_processing()

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

            # Startup cleanups
            asyncio.run(cleanup_orphaned_neo4j_data())
            cleanup_incomplete_processing()

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