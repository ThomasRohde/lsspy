<#
.SYNOPSIS
    Automates the complete LSSPY publishing workflow.

.DESCRIPTION
    This script handles the full release process:
    1. Runs linting, type checking, and tests to ensure everything passes
    2. Builds the frontend (React/Vite) and copies to static directory
    3. Builds the Python wheel and sdist
    4. Creates a git tag and pushes to trigger CI/CD
    5. GitHub Actions then publishes to PyPI

.PARAMETER Version
    The version to release (e.g., "1.0.1"). Either this or -Bump is required.

.PARAMETER Bump
    The type of version bump: "major", "minor", or "patch".

.PARAMETER Message
    Optional release message. Defaults to "Release vX.Y.Z".

.PARAMETER SkipTests
    Skip running tests (not recommended for production releases).

.PARAMETER SkipLint
    Skip running linting and type checks.

.PARAMETER SkipFrontend
    Skip building the frontend (use existing build).

.PARAMETER DryRun
    Show what would be done without making any changes.

.EXAMPLE
    .\scripts\publish.ps1 -Bump patch
    # Bumps patch version (0.1.0 -> 0.1.1) and publishes

.EXAMPLE
    .\scripts\publish.ps1 -Version 1.0.0 -Message "First stable release"
    # Releases specific version with custom message

.EXAMPLE
    .\scripts\publish.ps1 -Bump minor -DryRun
    # Shows what would happen without making changes
#>

param(
    [string]$Version,
    [ValidateSet("major", "minor", "patch")]
    [string]$Bump,
    [string]$Message,
    [switch]$SkipTests,
    [switch]$SkipLint,
    [switch]$SkipFrontend,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

function Write-Step {
    param([string]$Step, [string]$Description)
    Write-Host "`n" -NoNewline
    Write-Host "[$Step] " -ForegroundColor Cyan -NoNewline
    Write-Host $Description -ForegroundColor White
    Write-Host ("=" * 60) -ForegroundColor DarkGray
}

function Write-Success {
    param([string]$Message)
    Write-Host "OK $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "!! $Message" -ForegroundColor Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "ERROR $Message" -ForegroundColor Red
}

function Get-CurrentVersion {
    # First try to get version from git tags
    git fetch --tags --quiet 2>$null

    $tags = git tag -l --sort=-v:refname "v*.*.*" 2>$null
    if ($tags) {
        $latestTag = $tags | Select-Object -First 1
        return $latestTag -replace '^v', ''
    }

    # Fallback to pyproject.toml if no tags exist
    $pyprojectFile = Join-Path $ProjectRoot "pyproject.toml"
    if (Test-Path $pyprojectFile) {
        $content = Get-Content $pyprojectFile -Raw
        if ($content -match 'version\s*=\s*"([^"]+)"') {
            return $matches[1]
        }
    }

    throw "Could not determine current version"
}

function Get-PyProjectVersion {
    $pyprojectFile = Join-Path $ProjectRoot "pyproject.toml"
    if (Test-Path $pyprojectFile) {
        $content = Get-Content $pyprojectFile -Raw
        if ($content -match 'version\s*=\s*"([^"]+)"') {
            return $matches[1]
        }
    }
    throw "Could not read version from pyproject.toml"
}

function Get-InitVersion {
    $initFile = Join-Path $ProjectRoot "src\lsspy\__init__.py"
    if (Test-Path $initFile) {
        $content = Get-Content $initFile -Raw
        if ($content -match '__version__\s*=\s*"([^"]+)"') {
            return $matches[1]
        }
    }
    throw "Could not read version from __init__.py"
}

function Set-PyProjectVersion {
    param([string]$NewVersion)

    $pyprojectFile = Join-Path $ProjectRoot "pyproject.toml"
    $content = Get-Content $pyprojectFile -Raw
    # Only match 'version = "..."' at the start of a line (the project version in [project] section)
    $newContent = $content -replace '(?m)^version\s*=\s*"[^"]+"', "version = `"$NewVersion`""
    Set-Content -Path $pyprojectFile -Value $newContent -NoNewline
}

function Set-InitVersion {
    param([string]$NewVersion)

    $initFile = Join-Path $ProjectRoot "src\lsspy\__init__.py"
    $content = Get-Content $initFile -Raw
    $newContent = $content -replace '__version__\s*=\s*"[^"]+"', "__version__ = `"$NewVersion`""
    Set-Content -Path $initFile -Value $newContent -NoNewline
}

function Get-BumpedVersion {
    param([string]$Current, [string]$BumpType)

    $parts = $Current.Split('.')
    if ($parts.Count -ne 3) {
        throw "Invalid version format: $Current"
    }

    $major = [int]$parts[0]
    $minor = [int]$parts[1]
    $patch = [int]$parts[2]

    switch ($BumpType) {
        "major" { return "$($major + 1).0.0" }
        "minor" { return "$major.$($minor + 1).0" }
        "patch" { return "$major.$minor.$($patch + 1)" }
    }
}

# Validate parameters
if (-not $Version -and -not $Bump) {
    Write-Host "LSSPY Publishing Script" -ForegroundColor Magenta
    Write-Host "=" * 40 -ForegroundColor DarkGray

    $currentVersion = Get-CurrentVersion
    Write-Host "Current version: $currentVersion"
    Write-Host ""
    Write-Host "Usage:"
    Write-Host "  .\scripts\publish.ps1 -Bump patch      # $currentVersion -> $(Get-BumpedVersion $currentVersion 'patch')"
    Write-Host "  .\scripts\publish.ps1 -Bump minor      # $currentVersion -> $(Get-BumpedVersion $currentVersion 'minor')"
    Write-Host "  .\scripts\publish.ps1 -Bump major      # $currentVersion -> $(Get-BumpedVersion $currentVersion 'major')"
    Write-Host "  .\scripts\publish.ps1 -Version X.Y.Z   # Release specific version"
    Write-Host ""
    Write-Host "Options:"
    Write-Host "  -SkipTests      Skip running tests"
    Write-Host "  -SkipLint       Skip linting and type checks"
    Write-Host "  -SkipFrontend   Skip building frontend"
    Write-Host "  -DryRun         Show what would happen"
    Write-Host "  -Message        Custom release message"
    exit 0
}

# Change to project root
Push-Location $ProjectRoot
try {
    # Calculate new version
    $currentVersion = Get-CurrentVersion
    if ($Version) {
        $newVersion = $Version -replace '^v', ''
    }
    else {
        $newVersion = Get-BumpedVersion $currentVersion $Bump
    }

    # Validate version format
    if ($newVersion -notmatch '^\d+\.\d+\.\d+$') {
        throw "Invalid version format: $newVersion. Expected X.Y.Z"
    }

    $tagName = "v$newVersion"
    $releaseMessage = if ($Message) { $Message } else { "Release $tagName" }

    Write-Host "`nLSSPY Publishing Script" -ForegroundColor Magenta
    Write-Host "=" * 60 -ForegroundColor DarkGray
    Write-Host "  Current version: $currentVersion"
    Write-Host "  New version:     $newVersion"
    Write-Host "  Tag:             $tagName"
    Write-Host "  Message:         $releaseMessage"
    if ($DryRun) {
        Write-Host ""
        Write-Warning "DRY RUN - No changes will be made"
    }
    Write-Host ""

    # Step 1: Check git status
    Write-Step "1/7" "Checking git status"
    $gitStatus = git status --porcelain
    if ($gitStatus) {
        Write-Host "Uncommitted changes detected:" -ForegroundColor Yellow
        Write-Host $gitStatus
        if (-not $DryRun) {
            $confirm = Read-Host "Commit all changes before release? (y/N)"
            if ($confirm -ne 'y') {
                throw "Aborted: Please commit or stash changes first"
            }
        }
    }
    else {
        Write-Success "Working directory is clean"
    }

    # Step 2: Run linting and type checks
    if (-not $SkipLint) {
        Write-Step "2/7" "Running linting and type checks"
        if ($DryRun) {
            Write-Host "Would run: uv run ruff check src tests"
            Write-Host "Would run: uv run ruff format --check src tests"
            Write-Host "Would run: uv run mypy src"
        }
        else {
            Write-Host "Running ruff check..."
            uv run ruff check src tests
            if ($LASTEXITCODE -ne 0) {
                throw "Linting failed! Fix issues before releasing."
            }

            Write-Host "Running ruff format check..."
            uv run ruff format --check src tests
            if ($LASTEXITCODE -ne 0) {
                throw "Formatting check failed! Run 'uv run ruff format src tests' to fix."
            }

            Write-Host "Running mypy..."
            uv run mypy src
            if ($LASTEXITCODE -ne 0) {
                throw "Type checking failed! Fix issues before releasing."
            }

            Write-Success "All checks passed"
        }
    }
    else {
        Write-Step "2/7" "Skipping linting (--SkipLint)"
        Write-Warning "Lint checks skipped - not recommended for production!"
    }

    # Step 3: Run tests
    if (-not $SkipTests) {
        Write-Step "3/7" "Running tests"
        if ($DryRun) {
            Write-Host "Would run: uv run pytest -v"
        }
        else {
            uv run pytest -v
            if ($LASTEXITCODE -ne 0) {
                throw "Tests failed! Fix issues before releasing."
            }
            Write-Success "All tests passed"
        }
    }
    else {
        Write-Step "3/7" "Skipping tests (--SkipTests)"
        Write-Warning "Tests skipped - not recommended for production!"
    }

    # Step 4: Build frontend
    if (-not $SkipFrontend) {
        Write-Step "4/7" "Building frontend"
        if ($DryRun) {
            Write-Host "Would run: npm ci (in frontend/)"
            Write-Host "Would run: npm run build (in frontend/)"
            Write-Host "Would copy frontend/dist/index.html to src/lsspy/static/"
        }
        else {
            Push-Location (Join-Path $ProjectRoot "frontend")
            try {
                Write-Host "Installing frontend dependencies..."
                npm ci
                if ($LASTEXITCODE -ne 0) {
                    throw "Failed to install frontend dependencies"
                }

                Write-Host "Building frontend..."
                npm run build
                if ($LASTEXITCODE -ne 0) {
                    throw "Failed to build frontend"
                }

                # Copy to static directory
                $distFile = Join-Path $ProjectRoot "frontend\dist\index.html"
                $staticDir = Join-Path $ProjectRoot "src\lsspy\static"
                $staticFile = Join-Path $staticDir "index.html"

                if (-not (Test-Path $staticDir)) {
                    New-Item -ItemType Directory -Path $staticDir -Force | Out-Null
                }

                Copy-Item $distFile $staticFile -Force
                $fileSize = (Get-Item $staticFile).Length / 1KB
                Write-Success "Frontend built and copied to static/ (${fileSize:N0} KB)"
            }
            finally {
                Pop-Location
            }
        }
    }
    else {
        Write-Step "4/7" "Skipping frontend build (--SkipFrontend)"
        Write-Warning "Using existing frontend build"
    }

    # Step 5: Update version in pyproject.toml and __init__.py
    Write-Step "5/7" "Updating version"
    $pyprojectVersion = Get-PyProjectVersion
    $initVersion = Get-InitVersion

    if ($pyprojectVersion -ne $newVersion -or $initVersion -ne $newVersion) {
        if ($DryRun) {
            Write-Host "Would update pyproject.toml version: $pyprojectVersion -> $newVersion"
            Write-Host "Would update __init__.py version: $initVersion -> $newVersion"
        }
        else {
            Set-PyProjectVersion $newVersion
            Set-InitVersion $newVersion
            Write-Success "Updated version to $newVersion in pyproject.toml and __init__.py"
        }
    }
    else {
        Write-Success "Version already set to $newVersion"
    }

    # Step 6: Commit version change and create tag
    Write-Step "6/7" "Committing and tagging"

    # Check if tag already exists
    git fetch --tags --quiet 2>$null
    $tagExists = git tag -l $tagName
    if ($tagExists) {
        Write-Error "Tag $tagName already exists!"
        Write-Host ""
        Write-Host "This means the version was already released." -ForegroundColor Yellow
        Write-Host ""
        Write-Host "Solutions:" -ForegroundColor Cyan
        Write-Host "  1. Bump to next version: .\scripts\publish.ps1 -Bump patch" -ForegroundColor White
        Write-Host "  2. Specify a different version: .\scripts\publish.ps1 -Version X.Y.Z" -ForegroundColor White
        throw "Tag already exists. See solutions above."
    }

    if ($DryRun) {
        Write-Host "Would commit version change"
        Write-Host "Would create tag: $tagName"
        Write-Host "Would push to origin"
    }
    else {
        # Commit version change if needed
        $gitStatus = git status --porcelain
        if ($gitStatus) {
            git add -A
            git commit -m "chore: bump version to $newVersion"
            Write-Success "Version change committed"
        }

        # Push commits first
        Write-Host "Pushing commits..."
        git push origin HEAD
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to push commits"
        }

        # Create annotated tag
        Write-Host "Creating tag $tagName..."
        git tag -a $tagName -m $releaseMessage
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to create tag"
        }

        # Push tag
        Write-Host "Pushing tag..."
        git push origin $tagName
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to push tag"
        }
        Write-Success "Tag $tagName created and pushed"
    }

    # Step 7: Summary
    Write-Step "7/7" "Release complete!"

    if ($DryRun) {
        Write-Host ""
        Write-Warning "DRY RUN completed - no changes were made"
        Write-Host ""
        Write-Host "To perform the actual release, run without -DryRun"
    }
    else {
        Write-Host ""
        Write-Host "Released $tagName!" -ForegroundColor Green
        Write-Host ""
        Write-Host "Next steps:" -ForegroundColor Cyan
        Write-Host "  1. Go to https://github.com/ThomasRohde/lsspy/releases/new"
        Write-Host "  2. Select tag: $tagName"
        Write-Host "  3. Add release notes"
        Write-Host "  4. Click 'Publish release'"
        Write-Host ""
        Write-Host "GitHub Actions will then:" -ForegroundColor Cyan
        Write-Host "  1. Run CI checks"
        Write-Host "  2. Build frontend and package"
        Write-Host "  3. Publish to PyPI"
        Write-Host ""
        Write-Host "Monitor progress at:" -ForegroundColor Cyan
        Write-Host "  https://github.com/ThomasRohde/lsspy/actions"
        Write-Host ""
        Write-Host "Once published, users can install with:" -ForegroundColor Cyan
        Write-Host "  pip install lsspy-cli"
        Write-Host "  pip install --upgrade lsspy-cli"
        Write-Host ""
        Write-Host "Or run directly with uvx:" -ForegroundColor Cyan
        Write-Host "  uvx lsspy-cli start"
    }

}
catch {
    Write-Host ""
    Write-Error $_.Exception.Message
    exit 1
}
finally {
    Pop-Location
}
