#!/bin/bash

# Configuration
REPO_NAME="crispy-dollop"
GITHUB_USERNAME="klevermonicker"
REPO_PATH="$HOME/code/${REPO_NAME}"

# Commit patterns for 3 dancing stick figures (0=no commit, 1=light, 2=medium, 3=dark)
# Each row represents a week, each digit represents a day (Sun to Sat)
FIGURE_1=(
    "0030300"  # Head
    "0303030"  # Arms up
    "0003000"  # Torso
    "0003000"  # Waist
    "0003000"  # Upper legs
    "0030000"  # Legs dancing
    "0300000"  # Foot out
)

FIGURE_2=(
    "0003000"  # Head
    "0033300"  # Arms out
    "0003000"  # Torso
    "0303030"  # Arms/hands out
    "0003000"  # Waist
    "0030300"  # Legs apart
    "0300030"  # Feet apart
)

FIGURE_3=(
    "0003000"  # Head
    "0030300"  # Arm up
    "0003000"  # Torso
    "0030300"  # Arm out
    "0003000"  # Waist
    "0300030"  # Legs dancing
    "0030300"  # Feet position
)

# Space between figures (in weeks)
SPACE_WEEKS=1

# Fixed files for commits (to avoid repo bloat)
FILE_1="$REPO_PATH/dancing_file_1.txt"
FILE_2="$REPO_PATH/dancing_file_2.txt"
FILE_3="$REPO_PATH/dancing_file_3.txt"

# Print colored messages
print_info() {
    echo -e "\033[0;34m[INFO]\033[0m $1"
}

print_success() {
    echo -e "\033[0;32m[SUCCESS]\033[0m $1"
}

print_error() {
    echo -e "\033[0;31m[ERROR]\033[0m $1"
}

# Ensure repository is set up correctly
setup_repo() {
    # Check if repository directory exists
    if [ ! -d "$REPO_PATH" ]; then
        print_info "Repository directory doesn't exist, creating it..."
        mkdir -p "$REPO_PATH"
    fi

    # Check if it's a git repository
    if [ ! -d "$REPO_PATH/.git" ]; then
        print_info "Initializing git repository..."
        cd "$REPO_PATH" || exit
        git init
        
        # Set up remote if needed
        if ! git remote | grep -q "origin"; then
            print_info "Setting up remote origin..."
            git remote add origin "git@github.com:$GITHUB_USERNAME/$REPO_NAME.git"
        fi
    else
        print_info "Using existing repository at $REPO_PATH"
        cd "$REPO_PATH" || exit
        
        # Ensure remote is set correctly
        git remote set-url origin "git@github.com:$GITHUB_USERNAME/$REPO_NAME.git"
        
        # Pull latest changes
        git pull origin $(git rev-parse --abbrev-ref HEAD) || true
    fi
    
    # Ensure commit files exist
    touch "$FILE_1" "$FILE_2" "$FILE_3"
    
    # Add them if they're new
    git add "$FILE_1" "$FILE_2" "$FILE_3"
    
    # Commit them if they're new 
    if git status --porcelain | grep -q "A"; then
        git commit -m "Setup commit files for dancing pattern"
    fi
    
    print_success "Repository is ready"
}

# Get the pattern intensity for a specific date
get_pattern_intensity() {
    local date=$1
    local epoch_date=$(date -j -f "%Y-%m-%d" "$date" "+%s" 2>/dev/null)
    
    # If date conversion failed, try alternative format (Linux)
    if [ -z "$epoch_date" ]; then
        epoch_date=$(date -d "$date" "+%s" 2>/dev/null)
    fi
    
    # If still failed, return 0
    if [ -z "$epoch_date" ]; then
        print_error "Failed to parse date: $date"
        return 0
    fi
    
    # Convert to days since epoch
    local days_since_epoch=$((epoch_date / 86400))
    
    # Calculate total width of pattern
    local figure1_width=${#FIGURE_1[@]}
    local figure2_width=${#FIGURE_2[@]}
    local figure3_width=${#FIGURE_3[@]}
    local space_width=$SPACE_WEEKS
    local total_width=$((figure1_width + space_width + figure2_width + space_width + figure3_width))
    
    # Position in the repeating pattern
    local position_in_pattern=$((days_since_epoch % total_width))
    
    # Get the day of week (0=Sunday, 6=Saturday)
    local day_of_week=$(date -j -f "%Y-%m-%d" "$date" "+%w" 2>/dev/null)
    if [ -z "$day_of_week" ]; then
        day_of_week=$(date -d "$date" "+%w" 2>/dev/null)
    fi
    
    # Figure out which figure and week we're in
    local current_pos=0
    
    # Check Figure 1
    if [ $position_in_pattern -lt $figure1_width ]; then
        local week_in_figure=$position_in_pattern
        local intensity=${FIGURE_1[$week_in_figure]:$day_of_week:1}
        echo $intensity
        return
    fi
    current_pos=$((current_pos + figure1_width))
    
    # Check Space 1
    if [ $position_in_pattern -lt $((current_pos + space_width)) ]; then
        echo 0
        return
    fi
    current_pos=$((current_pos + space_width))
    
    # Check Figure 2
    if [ $position_in_pattern -lt $((current_pos + figure2_width)) ]; then
        local week_in_figure=$((position_in_pattern - current_pos))
        local intensity=${FIGURE_2[$week_in_figure]:$day_of_week:1}
        echo $intensity
        return
    fi
    current_pos=$((current_pos + figure2_width))
    
    # Check Space 2
    if [ $position_in_pattern -lt $((current_pos + space_width)) ]; then
        echo 0
        return
    fi
    current_pos=$((current_pos + space_width))
    
    # Check Figure 3
    if [ $position_in_pattern -lt $((current_pos + figure3_width)) ]; then
        local week_in_figure=$((position_in_pattern - current_pos))
        local intensity=${FIGURE_3[$week_in_figure]:$day_of_week:1}
        echo $intensity
        return
    fi
    
    # Default (shouldn't reach here)
    echo 0
}

# Create a commit for a specific intensity and date
create_commit() {
    local date=$1
    local intensity=$2
    local index=$3
    
    # Skip if intensity is 0
    if [ "$intensity" = "0" ]; then
        return
    fi
    
    # Determine number of commits based on intensity
    local num_commits=1
    if [ "$intensity" = "1" ]; then
        num_commits=$((1 + RANDOM % 2)) # 1-2 commits
    elif [ "$intensity" = "2" ]; then
        num_commits=$((3 + RANDOM % 3)) # 3-5 commits
    else # intensity 3
        num_commits=$((6 + RANDOM % 3)) # 6-8 commits
    fi
    
    print_info "Creating $num_commits commits for $date (intensity $intensity)"
    
    # Set commit date format
    local git_date=$(date -j -f "%Y-%m-%d" "$date" "+%Y-%m-%d 12:00:00" 2>/dev/null)
    if [ -z "$git_date" ]; then
        git_date=$(date -d "$date" "+%Y-%m-%d 12:00:00" 2>/dev/null)
    fi
    
    # Create commits
    for ((i=1; i<=num_commits; i++)); do
        # Choose file based on commit number
        local file_to_use
        case $((i % 3)) in
            0) file_to_use="$FILE_3" ;;
            1) file_to_use="$FILE_1" ;;
            2) file_to_use="$FILE_2" ;;
        esac
        
        # Update the file
        echo "Dancing stick figure commit - $date - $i/$num_commits (Figure $index)" > "$file_to_use"
        
        # Add and commit with date override
        git add "$file_to_use"
        GIT_AUTHOR_DATE="$git_date" GIT_COMMITTER_DATE="$git_date" git commit -m "Dancing figure $index - $date - $i/$num_commits"
        
        # Small delay to avoid overwhelming git
        sleep 0.5
    done
}

# Create the dancing pattern from a start date
create_pattern() {
    local start_date=$1
    local end_date=${2:-$(date "+%Y-%m-%d")} # Default to today
    
    print_info "Creating dancing stick figures pattern from $start_date to $end_date"
    
    # Setup repository
    setup_repo
    
    # Process each day
    local current_date="$start_date"
    local days_processed=0
    
    while [ "$(date -j -f "%Y-%m-%d" "$current_date" "+%s" 2>/dev/null || date -d "$current_date" "+%s")" -le "$(date -j -f "%Y-%m-%d" "$end_date" "+%s" 2>/dev/null || date -d "$end_date" "+%s")" ]; do
        # Get intensity for the current date
        local intensity=$(get_pattern_intensity "$current_date")
        
        # Create commits if needed
        if [ "$intensity" != "0" ]; then
            # Determine which figure based on position
            local figure_index=1
            create_commit "$current_date" "$intensity" "$figure_index"
        fi
        
        # Move to next day
        days_processed=$((days_processed + 1))
        current_date=$(date -j -v+1d -f "%Y-%m-%d" "$current_date" "+%Y-%m-%d" 2>/dev/null || date -d "$current_date + 1 day" "+%Y-%m-%d")
        
        # Push periodically to avoid large batches
        if [ $((days_processed % 7)) -eq 0 ]; then
            print_info "Pushing changes after processing $days_processed days"
            git push origin HEAD || true
        fi
    done
    
    # Final push
    print_info "Final push of all changes"
    git push origin HEAD
    
    print_success "Pattern created successfully! Check your GitHub profile."
}

# Create a commit for today based on the pattern
daily_update() {
    local today=$(date "+%Y-%m-%d")
    
    print_info "Performing daily update for $today"
    
    # Setup repository
    setup_repo
    
    # Get intensity for today
    local intensity=$(get_pattern_intensity "$today")
    
    # Create commits if needed
    if [ "$intensity" != "0" ]; then
        local figure_index=1 # Will be calculated correctly in full version
        create_commit "$today" "$intensity" "$figure_index"
        
        # Push changes
        git push origin HEAD
        print_success "Daily update completed successfully"
    else
        print_info "No commits needed for today according to the pattern"
    fi
}

# Display help
show_help() {
    echo "GitHub Dancing Stick Figures - Bash Version"
    echo
    echo "Usage:"
    echo "  $0 [OPTIONS]"
    echo
    echo "Options:"
    echo "  --setup <start_date>   Initial setup with start date (YYYY-MM-DD)"
    echo "  --daily                Run daily update"
    echo "  --help                 Show this help message"
    echo
    echo "Examples:"
    echo "  $0 --setup 2025-01-01"
    echo "  $0 --daily"
}

# Main script logic
case "$1" in
    --setup)
        if [ -z "$2" ]; then
            print_error "Start date is required"
            show_help
            exit 1
        fi
        create_pattern "$2"
        ;;
    --daily)
        daily_update
        ;;
    --help|*)
        show_help
        ;;
esac
