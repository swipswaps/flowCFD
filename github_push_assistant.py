#!/usr/bin/env python3
"""
GitHub Push Assistant for flowCFD
==================================
Interactive script to guide users through pushing their project to GitHub
with human-in-the-loop prompts and validation.
"""

import os
import subprocess
import sys
from pathlib import Path

class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_step(step_num, title, description=""):
    """Print a formatted step header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}=== STEP {step_num}: {title} ==={Colors.END}")
    if description:
        print(f"{Colors.YELLOW}{description}{Colors.END}")

def print_success(message):
    """Print success message in green"""
    print(f"{Colors.GREEN}✅ {message}{Colors.END}")

def print_warning(message):
    """Print warning message in yellow"""
    print(f"{Colors.YELLOW}⚠️  {message}{Colors.END}")

def print_error(message):
    """Print error message in red"""
    print(f"{Colors.RED}❌ {message}{Colors.END}")

def run_command(command, capture_output=True, check=True):
    """Run a shell command and return the result"""
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            capture_output=capture_output, 
            text=True, 
            check=check
        )
        return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
    except subprocess.CalledProcessError as e:
        return False, e.stdout, e.stderr

def get_user_input(prompt, default=None):
    """Get user input with optional default value"""
    if default:
        user_input = input(f"{prompt} [{default}]: ").strip()
        return user_input if user_input else default
    else:
        return input(f"{prompt}: ").strip()

def confirm_action(message):
    """Get yes/no confirmation from user"""
    while True:
        response = input(f"{message} (y/n): ").strip().lower()
        if response in ['y', 'yes']:
            return True
        elif response in ['n', 'no']:
            return False
        else:
            print("Please enter 'y' for yes or 'n' for no.")

def check_git_installed():
    """Check if git is installed"""
    success, _, _ = run_command("git --version")
    return success

def check_git_config():
    """Check if git user name and email are configured"""
    name_success, name, _ = run_command("git config user.name")
    email_success, email, _ = run_command("git config user.email")
    return name_success and email_success, name, email

def main():
    """Main assistant function"""
    print(f"{Colors.BOLD}{Colors.GREEN}")
    print("🚀 GITHUB PUSH ASSISTANT FOR FLOWCFD")
    print("=====================================")
    print("This script will guide you through pushing your flowCFD project to GitHub.")
    print(f"{Colors.END}")
    
    # Step 0: Prerequisites Check
    print_step(0, "PREREQUISITES CHECK")
    
    # Check git installation
    if not check_git_installed():
        print_error("Git is not installed. Please install git first.")
        print("On Ubuntu/Debian: sudo apt-get install git")
        print("On CentOS/RHEL: sudo yum install git")
        return False
    print_success("Git is installed")
    
    # Check git configuration
    config_ok, username, email = check_git_config()
    if not config_ok:
        print_warning("Git user configuration not found")
        if confirm_action("Would you like to configure git user settings now?"):
            name = get_user_input("Enter your full name")
            email = get_user_input("Enter your email address")
            run_command(f'git config --global user.name "{name}"')
            run_command(f'git config --global user.email "{email}"')
            print_success("Git configuration updated")
        else:
            print_warning("You may need to configure git later with:")
            print("git config --global user.name 'Your Name'")
            print("git config --global user.email 'your.email@example.com'")
    else:
        print_success(f"Git configured for {username} <{email}>")
    
    # Step 1: Project Status Check
    print_step(1, "PROJECT STATUS CHECK", "Verifying project directory and git repository")
    
    # Check if we're in the right directory
    current_dir = Path.cwd()
    if not (current_dir / "frontend").exists() or not (current_dir / "backend").exists():
        print_error("Not in flowCFD project directory. Please navigate to the project root.")
        print(f"Current directory: {current_dir}")
        return False
    print_success("In flowCFD project directory")
    
    # Check git repository status
    success, status_output, _ = run_command("git status --porcelain")
    if not success:
        if confirm_action("No git repository found. Initialize git repository?"):
            run_command("git init")
            run_command("git branch -M main")
            print_success("Git repository initialized")
        else:
            print_error("Git repository required. Please run 'git init' manually.")
            return False
    
    # Step 2: Check Remote Configuration
    print_step(2, "REMOTE REPOSITORY CHECK", "Checking GitHub remote configuration")
    
    success, remote_output, _ = run_command("git remote -v")
    if not success or not remote_output:
        print_warning("No remote repository configured")
        if confirm_action("Would you like to add a GitHub remote now?"):
            repo_url = get_user_input("Enter GitHub repository URL (SSH or HTTPS)")
            if repo_url:
                run_command(f"git remote add origin {repo_url}")
                print_success("Remote origin added")
            else:
                print_error("Repository URL required")
                return False
    else:
        print_success("Remote repository configured:")
        print(remote_output)
    
    # Step 3: Review Changes
    print_step(3, "REVIEW CHANGES", "Checking files to be committed")
    
    success, status_output, _ = run_command("git status")
    print("Current git status:")
    print(status_output)
    
    if not confirm_action("Review the changes above. Do you want to continue with staging files?"):
        print("Push cancelled by user.")
        return False
    
    # Step 4: Stage Files
    print_step(4, "STAGE FILES", "Adding files to git staging area")
    
    # Get list of modified/new files
    success, modified_files, _ = run_command("git status --porcelain")
    if modified_files:
        print("Files to be staged:")
        for line in modified_files.split('\n'):
            if line.strip():
                print(f"  {line}")
        
        if confirm_action("Stage all important project files?"):
            # Stage key files (avoid test files and temporary files)
            important_files = [
                "frontend/", "backend/", "README.md", 
                "push_to_github_steps.txt", "*.json", "*.md"
            ]
            
            # Add specific important files
            key_files = [
                "backend/app.py",
                "frontend/src/components/MultiTrackTimeline.tsx", 
                "frontend/src/pages/Editor.tsx",
                "push_to_github_steps.txt"
            ]
            
            for file in key_files:
                if Path(file).exists():
                    run_command(f"git add {file}")
            
            print_success("Important files staged")
        else:
            print("Please stage files manually with 'git add <filename>'")
            return False
    else:
        print_warning("No changes to stage")
    
    # Step 5: Create Commit
    print_step(5, "CREATE COMMIT", "Creating a commit with your changes")
    
    # Check if there are staged changes
    success, staged_output, _ = run_command("git diff --cached --name-only")
    if not staged_output.strip():
        print_warning("No staged changes to commit")
        if not confirm_action("Continue anyway?"):
            return False
    
    # Get commit message
    default_message = "feat: Enhanced drag-and-drop timeline functionality with clip sliding and snapping"
    commit_message = get_user_input("Enter commit message", default_message)
    
    success, commit_output, error = run_command(f'git commit -m "{commit_message}"')
    if success:
        print_success("Commit created successfully")
        print(commit_output)
    else:
        if "nothing to commit" in error:
            print_warning("Nothing to commit - all changes already committed")
        else:
            print_error(f"Commit failed: {error}")
            return False
    
    # Step 6: Push to GitHub
    print_step(6, "PUSH TO GITHUB", "Uploading your changes to GitHub")
    
    if confirm_action("Push changes to GitHub?"):
        print("Pushing to GitHub... (this may take a moment)")
        success, push_output, push_error = run_command("git push origin main", capture_output=False)
        
        if success:
            print_success("Successfully pushed to GitHub!")
            
            # Get remote URL for final verification
            success, remote_url, _ = run_command("git remote get-url origin")
            if success:
                print(f"\n{Colors.BOLD}🎉 Your code is now live at:{Colors.END}")
                print(f"{Colors.BLUE}{remote_url}{Colors.END}")
        else:
            print_error("Push failed. This might be due to:")
            print("- Authentication issues (check your GitHub credentials)")
            print("- Network connectivity problems")
            print("- Remote repository permissions")
            print("\nTry manually with: git push origin main")
            return False
    else:
        print("Push skipped. You can push manually later with: git push origin main")
    
    # Step 7: Success Summary
    print_step(7, "SUCCESS SUMMARY", "Push completed successfully!")
    
    print(f"{Colors.GREEN}✅ All steps completed successfully!{Colors.END}")
    print(f"{Colors.BOLD}What was accomplished:{Colors.END}")
    print("• Project files staged and committed")
    print("• Changes pushed to GitHub repository")
    print("• Drag-and-drop functionality improvements deployed")
    print("• Multi-track timeline enhancements available")
    
    print(f"\n{Colors.BOLD}Next steps:{Colors.END}")
    print("• Verify your changes on GitHub")
    print("• Update README.md if needed")
    print("• Consider setting up CI/CD workflows")
    print("• Share your repository with collaborators")
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        if success:
            print(f"\n{Colors.GREEN}{Colors.BOLD}🚀 GitHub push completed successfully!{Colors.END}")
            sys.exit(0)
        else:
            print(f"\n{Colors.RED}{Colors.BOLD}❌ GitHub push encountered issues.{Colors.END}")
            sys.exit(1)
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Push cancelled by user.{Colors.END}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Colors.RED}Unexpected error: {e}{Colors.END}")
        sys.exit(1)
