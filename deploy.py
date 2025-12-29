#!/usr/bin/env python3
"""
deploy.py

This script deploys the PeppeGPT AI Agent stack with different configurations:
- Local: Integrates with existing AI stack (no Caddy, uses overrides for existing Caddy)
- Cloud: Standalone deployment with its own Caddy reverse proxy
- Remote: Deploy to production server (Hostinger)

Usage:
  python deploy.py --type local --project localai    # Join existing AI stack
  python deploy.py --type cloud                       # Standalone cloud deployment
  python deploy.py --type remote                      # Deploy to production server
  python deploy.py --down --type local --project localai  # Stop services
"""

import argparse
import subprocess
import sys
import os

# Remote server configuration
REMOTE_HOST = "root@srv1189800.hstgr.cloud"
REMOTE_PATH = "/root/peppegpt"

def run_command(cmd, cwd=None):
    """Run a shell command and print it."""
    print("Running:", " ".join(cmd))
    try:
        subprocess.run(cmd, cwd=cwd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Command failed with exit code {e.returncode}")
        sys.exit(1)

def validate_environment(deployment_type="local"):
    """Check that required files exist."""
    required_files = ["docker-compose.yml"]

    if deployment_type == "remote":
        required_files.append(".env.prod")

    for file in required_files:
        if not os.path.exists(file):
            print(f"Error: Required file '{file}' not found in current directory")
            sys.exit(1)

def deploy_remote(action="up", services=None):
    """Deploy to production server (Hostinger).

    Args:
        action: "up" or "down"
        services: List of services to deploy. Options: frontend, agent-api, rag-pipeline, neo4j
                  If None, deploys all services.
    """

    if action == "up":
        service_str = ', '.join(services) if services else "ALL"
        print(f"🚀 Deploying [{service_str}] to: {REMOTE_HOST}")

        # Step 1: Copy .env.prod as .env to server
        print("\n📦 Copying .env.prod → server .env")
        run_command(["scp", ".env.prod", f"{REMOTE_HOST}:{REMOTE_PATH}/.env"])

        # Step 2: Sync project files (excluding .env files, node_modules, venv, etc.)
        print("\n📦 Syncing project files...")
        run_command([
            "rsync", "-avz", "--delete",
            "--exclude", ".env",
            "--exclude", ".env.local",
            "--exclude", ".env.prod",
            "--exclude", ".env.local.auradb",
            "--exclude", "node_modules",
            "--exclude", "venv",
            "--exclude", ".venv",
            "--exclude", "__pycache__",
            "--exclude", ".git",
            "--exclude", "*.pyc",
            "--exclude", ".DS_Store",
            "./", f"{REMOTE_HOST}:{REMOTE_PATH}/"
        ])

        # Step 3: Rebuild and restart services on server
        if services:
            # Only rebuild specific services
            services_arg = " ".join(services)
            print(f"\n🔄 Rebuilding services: {services_arg}")
            run_command(["ssh", REMOTE_HOST, f"cd {REMOTE_PATH} && docker compose up -d --build {services_arg}"])
        else:
            # Full deployment - stop all, rebuild all
            print("\n🔄 Rebuilding ALL services...")
            run_command(["ssh", REMOTE_HOST, f"cd {REMOTE_PATH} && docker compose down && docker compose up -d --build"])

        # Step 4: Show status
        print("\n📊 Checking service status...")
        run_command(["ssh", REMOTE_HOST, "docker ps --format 'table {{.Names}}\t{{.Status}}'"])

        print(f"\n✅ Production deployment completed!")
        print(f"   Server: {REMOTE_HOST}")
        print(f"   Path: {REMOTE_PATH}")
        if services:
            print(f"   Services: {', '.join(services)}")

    elif action == "down":
        print(f"🛑 Stopping services on production server: {REMOTE_HOST}")
        run_command(["ssh", REMOTE_HOST, f"cd {REMOTE_PATH} && docker compose down"])
        print(f"\n✅ Production services stopped!")

def deploy_agent_stack(deployment_type, project_name, action="up"):
    """Deploy or stop the agent stack based on deployment type."""
    
    # Build base command
    cmd = ["docker", "compose", "-p", project_name, "-f", "docker-compose.yml"]
    
    # Add deployment-specific compose files
    if deployment_type == "cloud":
        if not os.path.exists("docker-compose.caddy.yml"):
            print("Error: docker-compose.caddy.yml not found for cloud deployment")
            sys.exit(1)
        cmd.extend(["-f", "docker-compose.caddy.yml"])
        print(f"Cloud deployment: Including Caddy service")
        
    elif deployment_type == "local":
        print(f"Local deployment: Deploying agent services to join AI stack network")
    
    else:
        print(f"Error: Invalid deployment type '{deployment_type}'")
        sys.exit(1)
    
    # Add action (up/down)
    if action == "up":
        cmd.extend(["up", "-d", "--build"])
        print(f"Starting {deployment_type} deployment with project name '{project_name}' (rebuilding containers)...")
    elif action == "down":
        cmd.extend(["down"])
        print(f"Stopping {deployment_type} deployment with project name '{project_name}'...")
    
    # Execute command
    run_command(cmd)
    
    if action == "up":
        print(f"\n✅ {deployment_type.title()} deployment completed successfully!")
        
        if deployment_type == "local":
            print("\n📝 Local Deployment Notes:")
            print("- Agent services joined your existing AI stack network")
            print("- To enable reverse proxy routes in your Local AI Package:")
            print("  1. Copy caddy-addon.conf to your Local AI Package's caddy-addon folder")
            print("  2. Edit lines 2 and 21 in caddy-addon.conf to set your subdomains")
            print("  3. Restart Caddy: docker compose -p localai restart caddy")
            print(f"- Services running under project: {project_name}")
            
        elif deployment_type == "cloud":
            print("\n📝 Cloud Deployment Notes:")
            print("- Standalone deployment with integrated Caddy")
            print("- Configure AGENT_API_HOSTNAME and FRONTEND_HOSTNAME in .env")
            print("- Caddy will automatically provision SSL certificates")
            print("- Services accessible via configured hostnames")
    else:
        print(f"\n✅ {deployment_type.title()} deployment stopped successfully!")

def main():
    parser = argparse.ArgumentParser(
        description='Deploy the PeppeGPT AI Agent stack',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Local deployment (join existing AI stack)
  python deploy.py --type local --project localai

  # Cloud deployment (standalone with Caddy)
  python deploy.py --type cloud

  # Remote deployment - ALL services
  python deploy.py --type remote

  # Remote deployment - frontend only (faster!)
  python deploy.py --type remote -s frontend

  # Remote deployment - backend only
  python deploy.py --type remote -s agent-api

  # Remote deployment - multiple services
  python deploy.py --type remote -s frontend -s agent-api

  # Stop remote deployment
  python deploy.py --down --type remote
        """
    )
    
    parser.add_argument(
        '--type',
        choices=['local', 'cloud', 'remote'],
        required=True,
        help='Deployment type: local (join AI stack), cloud (standalone), or remote (production server)'
    )
    
    parser.add_argument(
        '--project', 
        default='peppegpt-agent',
        help='Docker Compose project name (default: peppegpt-agent)'
    )
    
    parser.add_argument(
        '--down',
        action='store_true',
        help='Stop and remove containers instead of starting them'
    )

    parser.add_argument(
        '--service', '-s',
        action='append',
        choices=['frontend', 'agent-api', 'rag-pipeline', 'neo4j'],
        help='Specific service(s) to deploy (can use multiple times). If not specified, deploys all.'
    )

    parser.add_argument(
        '--sync-env',
        action='store_true',
        help='Only sync .env.prod to server (no code deployment or container restart)'
    )

    parser.add_argument(
        '--update-env-secret',
        action='store_true',
        help='Update ENV_PROD_BASE64 GitHub secret with current .env.prod'
    )

    args = parser.parse_args()

    # Handle --update-env-secret
    if args.update_env_secret:
        import base64
        print("📦 Updating GitHub secret ENV_PROD_BASE64...")
        with open(".env.prod", "rb") as f:
            encoded = base64.b64encode(f.read()).decode()
        # Use gh CLI to update secret
        process = subprocess.run(
            ["gh", "secret", "set", "ENV_PROD_BASE64", "--body", encoded],
            capture_output=True,
            text=True
        )
        if process.returncode == 0:
            print("✅ GitHub secret updated!")
            print("💡 Push any change to main to deploy with new env, or run: gh workflow run deploy.yml")
        else:
            print(f"❌ Failed to update secret: {process.stderr}")
            sys.exit(1)
        sys.exit(0)

    # Handle --sync-env (only for remote)
    if args.sync_env:
        if args.type != "remote":
            print("Error: --sync-env only works with --type remote")
            sys.exit(1)
        print("📦 Syncing .env.prod → server .env")
        run_command(["scp", ".env.prod", f"{REMOTE_HOST}:{REMOTE_PATH}/.env"])
        print("✅ Environment file synced!")
        print("💡 Run 'python deploy.py --type remote' to restart containers with new env")
        sys.exit(0)

    # Validate environment
    validate_environment(args.type)

    # Determine action
    action = "down" if args.down else "up"

    # Deploy based on type
    if args.type == "remote":
        deploy_remote(action, services=args.service)
    else:
        deploy_agent_stack(args.type, args.project, action)

if __name__ == "__main__":
    main()