import os
import subprocess
import logging
import argparse
import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("git_diagnostic.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("git_diagnostic")

# Repository configuration
REPO_NAME = "bookish-octo-fortnight"
GITHUB_USERNAME = "klevermonicker"
REPO_SSH_URL = f"git@github.com:{GITHUB_USERNAME}/{REPO_NAME}.git"
REPO_PATH = os.path.expanduser(f"~/projects/{REPO_NAME}")

def run_command(command, cwd=None, env=None):
    """Run a command and return the output."""
    logger.info(f"Running: {' '.join(command)}")
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False  # Don't raise exception on error
        )
        if result.returncode == 0:
            logger.info("Command succeeded")
            if result.stdout.strip():
                logger.info(f"Output: {result.stdout.strip()}")
            return True, result.stdout.strip()
        else:
            logger.error(f"Command failed with exit code {result.returncode}")
            if result.stderr.strip():
                logger.error(f"Error: {result.stderr.strip()}")
            return False, result.stderr.strip()
    except Exception as e:
        logger.error(f"Exception running command: {e}")
        return False, str(e)

def check_repo_exists():
    """Check if the repository directory exists."""
    if os.path.exists(REPO_PATH):
        logger.info(f"Repository directory exists at {REPO_PATH}")
        return True
    else:
        logger.error(f"Repository directory does not exist at {REPO_PATH}")
        return False

def check_git_repo():
    """Check if the directory is a git repository."""
    if not check_repo_exists():
        return False
    
    success, _ = run_command(["git", "rev-parse", "--is-inside-work-tree"], cwd=REPO_PATH)
    return success

def check_remote():
    """Check the repository remote configuration."""
    if not check_git_repo():
        return False
    
    success, output = run_command(["git", "remote", "-v"], cwd=REPO_PATH)
    if not success:
        return False
    
    if "origin" in output and GITHUB_USERNAME in output:
        logger.info("Remote 'origin' is correctly configured")
        return True
    else:
        logger.error("Remote 'origin' is not correctly configured")
        logger.info(f"Expected: {REPO_SSH_URL}")
        logger.info(f"Actual: {output}")
        return False

def check_branches():
    """Check what branches exist locally and remotely."""
    if not check_git_repo():
        return False
    
    logger.info("Checking local branches:")
    run_command(["git", "branch"], cwd=REPO_PATH)
    
    logger.info("Checking remote branches:")
    run_command(["git", "branch", "-r"], cwd=REPO_PATH)
    
    # Get current branch
    success, current_branch = run_command(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=REPO_PATH)
    if success:
        logger.info(f"Current branch: {current_branch}")
    else:
        logger.error("Failed to get current branch")
    
    return True

def check_log():
    """Check the git log."""
    if not check_git_repo():
        return False
    
    logger.info("Checking git log (last 10 commits):")
    success, output = run_command(["git", "log", "-n", "10", "--oneline"], cwd=REPO_PATH)
    
    if not success or not output.strip():
        logger.warning("No commits found in the git log!")
        return False
    
    return True

def create_test_commit():
    """Create a test commit to ensure everything is working."""
    if not check_git_repo():
        return False
    
    # Create a test file
    test_file = os.path.join(REPO_PATH, "test_commit.txt")
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        with open(test_file, "w") as f:
            f.write(f"Test commit at {timestamp}\n")
        
        logger.info(f"Created test file: {test_file}")
        
        # Get current Git email
        success, email = run_command(["git", "config", "user.email"], cwd=REPO_PATH)
        if success:
            logger.info(f"Current Git email: {email}")
        else:
            logger.warning("Could not get current Git email")
        
        # Add and commit the file
        run_command(["git", "add", test_file], cwd=REPO_PATH)
        run_command(["git", "commit", "-m", f"Test commit at {timestamp}"], cwd=REPO_PATH)
        
        # Check the log again
        logger.info("Checking git log after test commit:")
        run_command(["git", "log", "-n", "1"], cwd=REPO_PATH)
        
        # Push the commit
        success, output = run_command(["git", "push"], cwd=REPO_PATH)
        if not success:
            logger.error("Failed to push test commit")
            # Try to determine which branch to push to
            success, default_branch = run_command(["git", "remote", "show", "origin"], cwd=REPO_PATH)
            if success and "HEAD branch" in default_branch:
                for line in default_branch.split("\n"):
                    if "HEAD branch" in line:
                        branch = line.split(":")[-1].strip()
                        logger.info(f"Attempting to push to detected default branch: {branch}")
                        run_command(["git", "push", "origin", branch], cwd=REPO_PATH)
                        break
        
        return True
    except Exception as e:
        logger.error(f"Error creating test commit: {e}")
        return False

def reset_repository():
    """Reset the repository to a clean state."""
    if not check_repo_exists():
        logger.info(f"Repository directory doesn't exist. Will clone it fresh.")
        os.makedirs(os.path.dirname(REPO_PATH), exist_ok=True)
        run_command(["git", "clone", REPO_SSH_URL, REPO_PATH])
        return check_git_repo()
    
    if not check_git_repo():
        logger.error(f"Directory exists but is not a git repository: {REPO_PATH}")
        response = input(f"Delete {REPO_PATH} and clone fresh? (y/n): ").strip().lower()
        if response == 'y':
            import shutil
            shutil.rmtree(REPO_PATH)
            os.makedirs(REPO_PATH)
            run_command(["git", "clone", REPO_SSH_URL, REPO_PATH])
            return check_git_repo()
        return False
    
    # Fetch the latest from remote
    logger.info("Fetching latest changes from remote")
    run_command(["git", "fetch", "--all"], cwd=REPO_PATH)
    
    # Check available branches
    success, branches = run_command(["git", "branch", "-a"], cwd=REPO_PATH)
    
    if not success:
        logger.error("Failed to list branches")
        return False
    
    # Try to identify the default branch
    default_branch = None
    remote_main = "remotes/origin/main" in branches
    remote_master = "remotes/origin/master" in branches
    
    if remote_main:
        default_branch = "main"
    elif remote_master:
        default_branch = "master"
    
    if not default_branch:
        logger.error("Could not identify default branch")
        default_branch = input("Enter the default branch name (main or master): ").strip()
        if not default_branch:
            default_branch = "main"
    
    logger.info(f"Using default branch: {default_branch}")
    
    # Reset to the remote branch
    success, _ = run_command(["git", "reset", "--hard", f"origin/{default_branch}"], cwd=REPO_PATH)
    if not success:
        logger.error(f"Failed to reset to origin/{default_branch}")
        return False
    
    # Switch to the default branch
    success, _ = run_command(["git", "checkout", default_branch], cwd=REPO_PATH)
    if not success:
        logger.error(f"Failed to switch to {default_branch}")
        # Try to create the branch from remote
        run_command(["git", "checkout", "-b", default_branch, f"origin/{default_branch}"], cwd=REPO_PATH)
    
    # Clean untracked files
    run_command(["git", "clean", "-fd"], cwd=REPO_PATH)
    
    logger.info("Repository reset successfully")
    return True

def fix_repository():
    """Fix common repository issues."""
    logger.info("Starting repository diagnostics and fixes...")
    
    if not check_repo_exists():
        logger.info("Repository doesn't exist, cloning fresh")
        os.makedirs(os.path.dirname(REPO_PATH), exist_ok=True)
        success, _ = run_command(["git", "clone", REPO_SSH_URL, REPO_PATH])
        if not success:
            logger.error("Failed to clone repository")
            return False
    
    if not check_git_repo():
        logger.error(f"{REPO_PATH} exists but is not a git repository")
        return False
    
    # Check and fix remote
    if not check_remote():
        logger.info("Fixing remote configuration")
        run_command(["git", "remote", "set-url", "origin", REPO_SSH_URL], cwd=REPO_PATH)
    
    # Check branches
    check_branches()
    
    # Check log
    if not check_log():
        logger.warning("No commits found in log, this might be a new repository or incorrect branch")
    
    # Create a test commit
    success = create_test_commit()
    if not success:
        logger.error("Failed to create test commit")
        return False
    
    logger.info("Repository diagnostics and fixes completed")
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Git Repository Diagnostic Tool")
    parser.add_argument("--check", action="store_true", help="Check repository status")
    parser.add_argument("--fix", action="store_true", help="Fix repository issues")
    parser.add_argument("--reset", action="store_true", help="Reset repository to a clean state")
    parser.add_argument("--test-commit", action="store_true", help="Create a test commit")
    
    args = parser.parse_args()
    
    if args.check:
        check_repo_exists()
        check_git_repo()
        check_remote()
        check_branches()
        check_log()
    elif args.reset:
        reset_repository()
    elif args.test_commit:
        create_test_commit()
    elif args.fix:
        fix_repository()
    else:
        # If no arguments, run the diagnosis
        check_repo_exists()
        check_git_repo()
        check_remote()
        check_branches()
        check_log()
        print("\nTo fix repository issues, run: python git_diagnostic.py --fix")
        print("To create a test commit, run: python git_diagnostic.py --test-commit")
        print("To reset the repository, run: python git_diagnostic.py --reset")
