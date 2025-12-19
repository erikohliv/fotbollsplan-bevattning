#!/usr/bin/env python3
"""
Tests for the automated deployment system.

These tests verify that:
1. Required files and directories exist
2. GitHub Actions workflow is properly structured
3. Scripts are executable and have valid syntax
4. Documentation is complete
"""

import os
import yaml
import subprocess
from pathlib import Path


def test_directory_structure():
    """Test that deployment directories and files exist."""
    base_dir = Path(__file__).parent
    
    # Check .github/workflows directory exists
    workflows_dir = base_dir / '.github' / 'workflows'
    assert workflows_dir.exists(), ".github/workflows directory should exist"
    assert workflows_dir.is_dir(), ".github/workflows should be a directory"
    
    # Check scripts directory exists
    scripts_dir = base_dir / 'scripts'
    assert scripts_dir.exists(), "scripts directory should exist"
    assert scripts_dir.is_dir(), "scripts should be a directory"
    
    print("✓ Directory structure is correct")


def test_workflow_file_exists():
    """Test that the GitHub Actions workflow file exists."""
    base_dir = Path(__file__).parent
    deploy_yml = base_dir / '.github' / 'workflows' / 'deploy.yml'
    
    assert deploy_yml.exists(), "deploy.yml should exist"
    assert deploy_yml.is_file(), "deploy.yml should be a file"
    
    print("✓ GitHub Actions workflow file exists")


def test_workflow_yaml_valid():
    """Test that the workflow YAML is valid."""
    base_dir = Path(__file__).parent
    deploy_yml = base_dir / '.github' / 'workflows' / 'deploy.yml'
    
    with open(deploy_yml, 'r') as f:
        workflow = yaml.safe_load(f)
    
    # Check basic structure
    assert 'name' in workflow, "Workflow should have a name"
    assert workflow['name'] == 'Deploy to Raspberry Pi', "Workflow name should be correct"
    
    assert 'on' in workflow, "Workflow should have triggers"
    assert 'push' in workflow['on'], "Workflow should trigger on push"
    assert 'branches' in workflow['on']['push'], "Push trigger should specify branches"
    assert 'main' in workflow['on']['push']['branches'], "Should trigger on main branch"
    
    assert 'jobs' in workflow, "Workflow should have jobs"
    assert 'deploy' in workflow['jobs'], "Should have deploy job"
    
    print("✓ GitHub Actions workflow YAML is valid")


def test_workflow_uses_secrets():
    """Test that the workflow uses required secrets."""
    base_dir = Path(__file__).parent
    deploy_yml = base_dir / '.github' / 'workflows' / 'deploy.yml'
    
    with open(deploy_yml, 'r') as f:
        content = f.read()
    
    # Check for required secrets
    assert 'secrets.RPI_HOST' in content, "Workflow should use RPI_HOST secret"
    assert 'secrets.RPI_USER' in content, "Workflow should use RPI_USER secret"
    assert 'secrets.RPI_SSH_KEY' in content, "Workflow should use RPI_SSH_KEY secret"
    
    print("✓ Workflow uses required secrets")


def test_deployment_scripts_exist():
    """Test that deployment scripts exist."""
    base_dir = Path(__file__).parent
    scripts_dir = base_dir / 'scripts'
    
    deploy_sh = scripts_dir / 'deploy.sh'
    post_receive = scripts_dir / 'post-receive.sample'
    scripts_readme = scripts_dir / 'README.md'
    
    assert deploy_sh.exists(), "deploy.sh should exist"
    assert post_receive.exists(), "post-receive.sample should exist"
    assert scripts_readme.exists(), "scripts/README.md should exist"
    
    print("✓ Deployment scripts exist")


def test_scripts_are_executable():
    """Test that scripts have executable permissions."""
    base_dir = Path(__file__).parent
    scripts_dir = base_dir / 'scripts'
    
    deploy_sh = scripts_dir / 'deploy.sh'
    post_receive = scripts_dir / 'post-receive.sample'
    
    assert os.access(deploy_sh, os.X_OK), "deploy.sh should be executable"
    assert os.access(post_receive, os.X_OK), "post-receive.sample should be executable"
    
    print("✓ Scripts are executable")


def test_bash_syntax_valid():
    """Test that bash scripts have valid syntax."""
    base_dir = Path(__file__).parent
    scripts_dir = base_dir / 'scripts'
    
    deploy_sh = scripts_dir / 'deploy.sh'
    post_receive = scripts_dir / 'post-receive.sample'
    
    # Test deploy.sh syntax
    result = subprocess.run(['bash', '-n', str(deploy_sh)], capture_output=True)
    assert result.returncode == 0, f"deploy.sh has syntax errors: {result.stderr.decode()}"
    
    # Test post-receive.sample syntax
    result = subprocess.run(['bash', '-n', str(post_receive)], capture_output=True)
    assert result.returncode == 0, f"post-receive.sample has syntax errors: {result.stderr.decode()}"
    
    print("✓ Bash script syntax is valid")


def test_deploy_script_content():
    """Test that deploy.sh contains expected commands."""
    base_dir = Path(__file__).parent
    deploy_sh = base_dir / 'scripts' / 'deploy.sh'
    
    with open(deploy_sh, 'r') as f:
        content = f.read()
    
    # Check for essential commands
    assert 'git fetch' in content, "deploy.sh should fetch from git"
    assert 'source .venv/bin/activate' in content or '. .venv/bin/activate' in content, "deploy.sh should activate venv (using source or . command)"
    assert 'pip install -r api_requirements.txt' in content, "deploy.sh should install API requirements"
    assert 'pip install -r display_requirements.txt' in content, "deploy.sh should install display requirements"
    assert ('systemctl restart bevattning-api' in content or 'restart_service "bevattning-api"' in content), "deploy.sh should restart bevattning-api"
    
    print("✓ deploy.sh contains expected commands")


def test_post_receive_content():
    """Test that post-receive.sample contains expected commands."""
    base_dir = Path(__file__).parent
    post_receive = base_dir / 'scripts' / 'post-receive.sample'
    
    with open(post_receive, 'r') as f:
        content = f.read()
    
    # Check for essential commands
    assert 'git fetch' in content, "post-receive should fetch from git"
    assert 'git reset --hard origin/main' in content, "post-receive should reset to main"
    assert 'source .venv/bin/activate' in content, "post-receive should activate venv"
    assert 'pip install' in content, "post-receive should install dependencies"
    assert 'systemctl restart' in content, "post-receive should restart services"
    
    print("✓ post-receive.sample contains expected commands")


def test_readme_updated():
    """Test that README.md contains automatic deployment documentation."""
    base_dir = Path(__file__).parent
    readme = base_dir / 'README.md'
    
    with open(readme, 'r') as f:
        content = f.read()
    
    # Check for deployment section
    assert 'Automatic System Updates' in content, "README should have Automatic System Updates section"
    assert 'GitHub Actions' in content, "README should mention GitHub Actions"
    assert 'RPI_HOST' in content, "README should document RPI_HOST secret"
    assert 'RPI_USER' in content, "README should document RPI_USER secret"
    assert 'RPI_SSH_KEY' in content, "README should document RPI_SSH_KEY secret"
    assert 'ssh-keygen' in content, "README should document SSH key generation"
    assert 'sudoers' in content, "README should document sudoers configuration"
    
    print("✓ README.md contains deployment documentation")


def test_installation_md_updated():
    """Test that INSTALLATION.md contains deployment setup instructions."""
    base_dir = Path(__file__).parent
    installation = base_dir / 'INSTALLATION.md'
    
    with open(installation, 'r') as f:
        content = f.read()
    
    # Check for deployment section
    assert 'Automatisk Deployment' in content, "INSTALLATION.md should have deployment section"
    assert 'GitHub Secrets' in content, "INSTALLATION.md should mention GitHub Secrets"
    assert 'ssh-keygen' in content, "INSTALLATION.md should document SSH key generation"
    assert 'deploy.sh' in content, "INSTALLATION.md should reference deploy.sh"
    
    print("✓ INSTALLATION.md contains deployment instructions")


def test_scripts_readme_exists():
    """Test that scripts/README.md exists and has content."""
    base_dir = Path(__file__).parent
    scripts_readme = base_dir / 'scripts' / 'README.md'
    
    assert scripts_readme.exists(), "scripts/README.md should exist"
    
    with open(scripts_readme, 'r') as f:
        content = f.read()
    
    assert len(content) > 100, "scripts/README.md should have substantial content"
    assert 'deploy.sh' in content, "scripts/README.md should document deploy.sh"
    assert 'post-receive.sample' in content, "scripts/README.md should document post-receive.sample"
    
    print("✓ scripts/README.md exists with proper content")


if __name__ == '__main__':
    """Run all tests."""
    tests = [
        test_directory_structure,
        test_workflow_file_exists,
        test_workflow_yaml_valid,
        test_workflow_uses_secrets,
        test_deployment_scripts_exist,
        test_scripts_are_executable,
        test_bash_syntax_valid,
        test_deploy_script_content,
        test_post_receive_content,
        test_readme_updated,
        test_installation_md_updated,
        test_scripts_readme_exists,
    ]
    
    print("\n" + "=" * 70)
    print("Running Automated Deployment Tests")
    print("=" * 70 + "\n")
    
    failed = 0
    for test in tests:
        try:
            test()
        except AssertionError as e:
            print(f"✗ {test.__name__} failed: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {test.__name__} error: {e}")
            failed += 1
    
    print("\n" + "=" * 70)
    if failed == 0:
        print("All tests passed! ✓")
    else:
        print(f"{failed} test(s) failed ✗")
    print("=" * 70 + "\n")
    
    exit(0 if failed == 0 else 1)
