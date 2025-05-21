import os
import datetime
import random
import subprocess
import time
import argparse
import logging
from datetime import timedelta

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("dancing_figures.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("dancing_figures")

# Configuration with your specific repository
REPO_NAME = "bookish-octo-fortnight"
GITHUB_USERNAME = "klevermonicker"
REPO_SSH_URL = f"git@github.com:{GITHUB_USERNAME}/{REPO_NAME}.git"
REPO_PATH = os.path.expanduser(f"~/dancing_figs/{REPO_NAME}")  # Local path where repo will be cloned

# Define 3 dancing stick figures (each row represents a week, each digit represents a day)
# 0 = no commit, 1 = light (1-2 commits), 2 = medium (3-5 commits), 3 = dark (6+ commits)
DANCING_FIGURES = [
    # First dancing figure (arms up, one leg out)
    [
        "0030300",  # Head
        "0303030",  # Arms up
        "0003000",  # Torso
        "0003000",  # Waist
        "0003000",  # Upper legs
        "0030000",  # Legs dancing
        "0300000",  # Foot out
    ],
    # Second dancing figure (jumping)
    [
        "0003000",  # Head
        "0033300",  # Arms out
        "0003000",  # Torso
        "0303030",  # Arms/hands out
        "0003000",  # Waist
        "0030300",  # Legs apart
        "0300030",  # Feet apart
    ],
    # Third dancing figure (twist)
    [
        "0003000",  # Head
        "0030300",  # Arm up
        "0003000",  # Torso
        "0030300",  # Arm out
        "0003000",  # Waist
        "0300030",  # Legs dancing
        "0030300",  # Feet position
    ]
]

# Space between figures (in weeks)
SPACE_BETWEEN = 1
# Total width of the pattern (days)
PATTERN_WIDTH = sum([len(figure[0]) for figure in DANCING_FIGURES]) + (SPACE_BETWEEN * 7 * (len(DANCING_FIGURES) - 1))

# Define a fixed set of files that will be used for commits
# We'll reuse these files instead of creating new ones each time
MAX_FILES = 10
COMMIT_FILES = [f"dancing_file_{i}.txt" for i in range(MAX_FILES)]

def get_pattern_for_date(date):
    """Determine the commit intensity for a specific date based on the pattern."""
    # Convert date to days since epoch for consistent positioning
    days_since_epoch = (date - datetime.datetime(1970, 1, 1).date()).days
    
    # Position in the repeating pattern
    position_in_pattern = days_since_epoch % PATTERN_WIDTH
    
    current_pos = 0
    for figure_idx, figure in enumerate(DANCING_FIGURES):
        figure_width = len(figure[0]) * 7  # Width in days
        
        if position_in_pattern < current_pos + figure_width:
            # We're in this figure
            day_in_figure = position_in_pattern - current_pos
            week_idx = day_in_figure // 7
            day_idx = day_in_figure % 7
            
            if week_idx < len(figure) and day_idx < len(figure[week_idx]):
                return int(figure[week_idx][day_idx])
            return 0
        
        current_pos += figure_width
        
        # Add space between figures
        if figure_idx < len(DANCING_FIGURES) - 1:
            space_width = SPACE_BETWEEN * 7
            if position_in_pattern < current_pos + space_width:
                return 0
            current_pos += space_width
    
    return 0  # Default: no commit

def run_command(command, cwd=None, env=None):
    """Run a command and log the output."""
    try:
        logger.info(f"Running command: {command}")
        result = subprocess.run(
            command, 
            cwd=cwd, 
            env=env,
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        if result.stdout.strip():
            logger.info(f"Command output: {result.stdout.strip()}")
        return True, result.stdout.strip()
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed: {e}")
        logger.error(f"Error output: {e.stderr}")
        return False, e.stderr

def sync_repo():
    """Synchronize the local repository with the remote."""
    logger.info("Synchronizing repository with remote...")
    
    # Get the current branch
    success, branch = run_command(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=REPO_PATH)
    if not success:
        logger.warning("Failed to get current branch, trying common branches...")
        for b in ["main", "master"]:
            success, _ = run_command(["git", "show-ref", "--verify", f"refs/heads/{b}"], cwd=REPO_PATH)
            if success:
                branch = b
                break
        if not success:
            logger.error("Could not determine branch, defaulting to main")
            branch = "main"
    else:
        branch = branch.strip()
    
    logger.info(f"Current branch: {branch}")
    
    # Stash any local changes
    run_command(["git", "stash"], cwd=REPO_PATH)
    
    # Fetch the latest changes
    success, _ = run_command(["git", "fetch", "origin", branch], cwd=REPO_PATH)
    if not success:
        logger.warning(f"Failed to fetch from origin/{branch}")
    
    # Check if we need to rebase or merge
    success, merge_base = run_command(["git", "merge-base", f"origin/{branch}", branch], cwd=REPO_PATH)
    if not success:
        logger.warning(f"Failed to find merge-base with origin/{branch}")
        # Try direct pull
        success, _ = run_command(["git", "pull", "--rebase", "origin", branch], cwd=REPO_PATH)
        if not success:
            logger.warning("Failed to pull with rebase, trying normal pull")
            success, _ = run_command(["git", "pull", "origin", branch], cwd=REPO_PATH)
        return success
    
    # Check if branches have diverged
    success, local_commit = run_command(["git", "rev-parse", branch], cwd=REPO_PATH)
    success, remote_commit = run_command(["git", "rev-parse", f"origin/{branch}"], cwd=REPO_PATH)
    
    if local_commit.strip() == remote_commit.strip():
        logger.info("Local and remote branches are in sync")
        return True
    
    # Check if we can fast-forward
    success, _ = run_command(["git", "merge-base", "--is-ancestor", branch, f"origin/{branch}"], cwd=REPO_PATH)
    if success:
        # Our branch is behind, we can fast-forward
        logger.info("Fast-forwarding local branch")
        success, _ = run_command(["git", "merge", "--ff-only", f"origin/{branch}"], cwd=REPO_PATH)
        return success
    
    # Branches have diverged, try rebase
    logger.info("Branches have diverged, attempting rebase")
    success, _ = run_command(["git", "rebase", f"origin/{branch}"], cwd=REPO_PATH)
    if not success:
        logger.warning("Rebase failed, trying merge")
        run_command(["git", "rebase", "--abort"], cwd=REPO_PATH)  # Abort failed rebase
        success, _ = run_command(["git", "merge", f"origin/{branch}"], cwd=REPO_PATH)
    
    return success

def setup_commit_files():
    """Ensure the fixed commit files exist."""
    # Create the fixed files if they don't exist
    for file_path in [os.path.join(REPO_PATH, file) for file in COMMIT_FILES]:
        if not os.path.exists(file_path):
            with open(file_path, "w") as f:
                f.write("Initial setup for dancing stick figures pattern.")
    
    # Add the files to git if needed
    for file in COMMIT_FILES:
        run_command(["git", "add", file], cwd=REPO_PATH)
    
    # Commit them if there are changes
    success, output = run_command(["git", "status", "--porcelain"], cwd=REPO_PATH)
    if success and output.strip():
        run_command(["git", "commit", "-m", "Setup fixed commit files for dancing pattern"], cwd=REPO_PATH)
        
        # Push the changes
        branch = get_current_branch()
        if branch:
            push_changes(branch)

def get_current_branch():
    """Get the current git branch."""
    success, branch = run_command(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=REPO_PATH)
    if success:
        return branch.strip()
    
    # Try to determine if this is main or master
    for branch in ["main", "master"]:
        success, _ = run_command(["git", "show-ref", "--verify", f"refs/heads/{branch}"], cwd=REPO_PATH)
        if success:
            logger.info(f"Detected {branch} branch")
            return branch
    
    logger.warning("Could not determine branch, defaulting to main")
    return "main"

def push_changes(branch):
    """Push changes to remote with better error handling."""
    logger.info(f"Pushing changes to {branch}...")
    
    # First try a normal push
    success, error = run_command(["git", "push", "origin", branch], cwd=REPO_PATH)
    if success:
        return True
    
    # If that fails, check if it's a non-fast-forward error
    if "non-fast-forward" in error:
        logger.warning("Non-fast-forward error detected, trying to sync repository")
        if sync_repo():
            # Try pushing again after sync
            success, _ = run_command(["git", "push", "origin", branch], cwd=REPO_PATH)
            return success
    
    # If still failing, try push with force-with-lease (safer than --force)
    logger.warning("Normal push failed, trying force-with-lease")
    success, _ = run_command(["git", "push", "--force-with-lease", "origin", branch], cwd=REPO_PATH)
    return success

def create_commits_for_today(num_commits):
    """Create the specified number of commits for today using the fixed set of files."""
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    logger.info(f"Creating {num_commits} commits for today ({today})")
    
    # Get the current branch
    branch = get_current_branch()
    
    # Sync repo before making changes
    sync_repo()
    
    for i in range(num_commits):
        # Choose a file to modify
        file_index = i % MAX_FILES
        file_path = os.path.join(REPO_PATH, COMMIT_FILES[file_index])
        
        # Modify the file
        logger.info(f"Modifying file for commit: {file_path}")
        with open(file_path, "w") as f:
            f.write(f"Dancing stick figure commit - {today} - {timestamp} - {i}")
        
        # Add and commit the file
        success, _ = run_command(["git", "add", file_path], cwd=REPO_PATH)
        if not success:
            continue
            
        success, _ = run_command(["git", "commit", "-m", f"Dancing stick figure - {today} - {i}"], cwd=REPO_PATH)
        if not success:
            continue
            
        # Push after each commit (or every few commits for better performance)
        if i % 3 == 0 or i == num_commits - 1:  # Push every 3 commits or on the last commit
            if not push_changes(branch):
                logger.error(f"Failed to push commit {i}")
                # Try to sync and continue
                sync_repo()
        
        # Small delay between operations
        time.sleep(random.uniform(0.5, 1.0))
    
    # Final push to ensure all commits are pushed
    push_changes(branch)

def setup_repo():
    """Ensure the repository is set up properly using SSH."""
    if not os.path.exists(REPO_PATH):
        logger.info(f"Cloning repository {REPO_SSH_URL} to {REPO_PATH}")
        os.makedirs(os.path.dirname(REPO_PATH), exist_ok=True)
        
        # Clone the repository using SSH
        success, _ = run_command(["git", "clone", REPO_SSH_URL, REPO_PATH])
        if not success:
            logger.error("Failed to clone repository")
            return False
            
        # Verify SSH connection
        success, _ = run_command(["git", "remote", "-v"], cwd=REPO_PATH)
        if not success:
            logger.error("Failed to verify remote repository")
            return False
    else:
        logger.info(f"Using existing repository at {REPO_PATH}")
        
        # Make sure we have the latest changes and the remote is set to SSH
        run_command(["git", "remote", "set-url", "origin", REPO_SSH_URL], cwd=REPO_PATH)
        
        # Sync with remote repository
        if not sync_repo():
            logger.warning("Failed to sync with remote repository, will try to continue anyway")
    
    # Make sure our fixed commit files are set up
    setup_commit_files()
    
    return True

def initial_setup(start_date_str, force=False):
    """Run the initial setup to create the pattern from start_date until today."""
    if not setup_repo():
        logger.error("Repository setup failed")
        return False
    
    start_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d").date()
    today = datetime.datetime.now().date()
    
    logger.info(f"Creating initial pattern from {start_date} to {today}...")
    
    # Get the current branch
    branch = get_current_branch()
    
    current_date = start_date
    while current_date <= today:
        intensity = get_pattern_for_date(current_date)
        if intensity > 0:
            # Determine number of commits based on intensity
            if intensity == 1:
                num_commits = random.randint(1, 2)
            elif intensity == 2:
                num_commits = random.randint(3, 5)
            else:  # intensity == 3
                num_commits = random.randint(6, 8)
            
            date_str = current_date.strftime("%Y-%m-%d")
            logger.info(f"Creating {num_commits} commits for {date_str}")
            
            # Create backdated commits
            for i in range(num_commits):
                # Choose a file to modify
                file_index = i % MAX_FILES
                file_path = os.path.join(REPO_PATH, COMMIT_FILES[file_index])
                
                # Modify the file
                with open(file_path, "w") as f:
                    f.write(f"Initial setup - {date_str} - {i}")
                
                # Set environment variables for the git commit date
                env_vars = os.environ.copy()
                commit_date = datetime.datetime.combine(current_date, datetime.time(hour=random.randint(9, 18)))
                env_vars["GIT_AUTHOR_DATE"] = commit_date.strftime("%Y-%m-%d %H:%M:%S")
                env_vars["GIT_COMMITTER_DATE"] = commit_date.strftime("%Y-%m-%d %H:%M:%S")
                
                # Add and commit the file
                success, _ = run_command(["git", "add", file_path], cwd=REPO_PATH)
                if not success:
                    continue
                
                success, _ = run_command(
                    ["git", "commit", "-m", f"Initial setup - {date_str} - {i}"],
                    cwd=REPO_PATH,
                    env=env_vars
                )
                if not success:
                    continue
                
                # Push periodically to avoid large batches
                if i % 5 == 0 or i == num_commits - 1:  # Push every 5 commits or on the last commit
                    push_success = push_changes(branch)
                    if not push_success and force:
                        # If force is enabled and normal push fails, try with force
                        logger.warning("Normal push failed, attempting force push due to --force flag")
                        run_command(["git", "push", "--force", "origin", branch], cwd=REPO_PATH)
                
                # Small delay
                time.sleep(random.uniform(0.5, 1.0))
        
        current_date += timedelta(days=1)
    
    # Final push to ensure all commits are pushed
    push_success = push_changes(branch)
    if not push_success and force:
        # If force is enabled and normal push fails, try with force
        logger.warning("Final push failed, attempting force push due to --force flag")
        run_command(["git", "push", "--force", "origin", branch], cwd=REPO_PATH)
    
    logger.info("Initial setup completed successfully")
    return True

def daily_update():
    """Create commits for today based on the pattern."""
    if not setup_repo():
        logger.error("Repository setup failed")
        return False
    
    today = datetime.datetime.now().date()
    intensity = get_pattern_for_date(today)
    
    if intensity > 0:
        # Determine number of commits based on intensity
        if intensity == 1:
            num_commits = random.randint(1, 2)
        elif intensity == 2:
            num_commits = random.randint(3, 5)
        else:  # intensity == 3
            num_commits = random.randint(6, 8)
        
        create_commits_for_today(num_commits)
        logger.info(f"Daily update completed successfully for {today}")
        return True
    else:
        logger.info(f"No commits needed for today ({today}) according to the pattern.")
        return True

def cleanup():
    """Optional: Clean up the repository to reduce size (use with caution)."""
    logger.info("Cleaning up repository to reduce size...")
    
    # Only keep the fixed commit files and essential repo files
    for root, dirs, files in os.walk(REPO_PATH):
        for file in files:
            # Skip .git directory
            if '.git' in root:
                continue
                
            # Skip essential files
            if file in COMMIT_FILES or file == "README.md" or file == ".gitignore" or file.endswith('.py'):
                continue
                
            file_path = os.path.join(root, file)
            logger.info(f"Removing file: {file_path}")
            os.remove(file_path)
    
    # Add all changes
    run_command(["git", "add", "--all"], cwd=REPO_PATH)
    
    # Commit the cleanup
    run_command(["git", "commit", "-m", "Clean up repository to reduce size"], cwd=REPO_PATH)
    
    # Push the changes
    branch = get_current_branch()
    if branch:
        push_changes(branch)
    
    # Run git gc to compress the repository
    run_command(["git", "gc", "--aggressive", "--prune=now"], cwd=REPO_PATH)

def test_ssh_connection():
    """Test SSH connection to GitHub."""
    logger.info("Testing SSH connection to GitHub...")
    try:
        result = subprocess.run(
            ["ssh", "-T", "git@github.com"], 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            text=True
        )
        # GitHub's SSH test always returns exit code 1 with a welcome message
        if "successfully authenticated" in result.stderr:
            logger.info("SSH connection to GitHub successful")
            return True
        else:
            logger.error(f"SSH connection to GitHub failed: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"Error testing SSH connection: {e}")
        return False

def reset_repo():
    """Reset the local repository to match the remote."""
    if not os.path.exists(REPO_PATH):
        logger.error("Repository does not exist, cannot reset")
        return False
    
    logger.info("Resetting local repository to match remote...")
    
    # Get the current branch
    branch = get_current_branch()
    
    # Fetch the latest changes
    success, _ = run_command(["git", "fetch", "origin"], cwd=REPO_PATH)
    if not success:
        logger.error("Failed to fetch from remote")
        return False
    
    # Reset to the remote branch
    success, _ = run_command(["git", "reset", "--hard", f"origin/{branch}"], cwd=REPO_PATH)
    if not success:
        logger.error(f"Failed to reset to origin/{branch}")
        return False
    
    # Clean untracked files
    success, _ = run_command(["git", "clean", "-fd"], cwd=REPO_PATH)
    
    logger.info("Repository reset successfully")
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GitHub Contribution Graph Dancing Stick Figures")
    parser.add_argument("--setup", help="Run initial setup with start date (YYYY-MM-DD)", metavar="START_DATE")
    parser.add_argument("--daily", action="store_true", help="Run daily update")
    parser.add_argument("--test-ssh", action="store_true", help="Test SSH connection to GitHub")
    parser.add_argument("--cleanup", action="store_true", help="Clean up repository to reduce size (use with caution)")
    parser.add_argument("--reset", action="store_true", help="Reset local repository to match remote")
    parser.add_argument("--force", action="store_true", help="Use force push if necessary (use with caution)")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    
    args = parser.parse_args()
    
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")
    
    if args.test_ssh:
        test_ssh_connection()
    elif args.reset:
        reset_repo()
    elif args.setup:
        initial_setup(args.setup, force=args.force)
    elif args.daily:
        daily_update()
    elif args.cleanup:
        cleanup()
    else:
        parser.print_help()
