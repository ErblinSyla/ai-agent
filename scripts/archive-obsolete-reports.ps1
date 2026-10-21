$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$reportsRoot = Join-Path $repoRoot 'reports'
$archiveRoot = Join-Path $reportsRoot 'archive\obsolete-pre-demo'
$candidates = @(
    'assignment-01-review',
    'assignment-01-review-fixed',
    'assignment-01-review-final',
    'groq-diagnostic',
    'groq-smoke-test',
    'assignment-01-presentation-verification'
)

foreach ($name in $candidates) {
    $source = Join-Path $reportsRoot $name
    if (-not (Test-Path -LiteralPath $source -PathType Container)) { continue }

    $jsonReports = @(Get-ChildItem -LiteralPath $source -File -Filter '*.json')
    if ($jsonReports.Count -eq 0) {
        Write-Warning "Preserving $source because it has no JSON report to verify."
        continue
    }
    $allFailed = $true
    foreach ($jsonReport in $jsonReports) {
        try {
            $report = Get-Content -LiteralPath $jsonReport.FullName -Raw | ConvertFrom-Json
            if ($report.ai_review.status -ne 'failed') { $allFailed = $false }
        } catch {
            $allFailed = $false
        }
    }
    if (-not $allFailed) {
        Write-Warning "Preserving $source because not every JSON report is confirmed failed."
        continue
    }

    $destination = Join-Path $archiveRoot $name
    if (Test-Path -LiteralPath $destination) {
        Write-Warning "Preserving $source because archive destination already exists: $destination"
        continue
    }
    New-Item -ItemType Directory -Path $archiveRoot -Force | Out-Null
    Move-Item -LiteralPath $source -Destination $destination
    Write-Output "Archived confirmed failed report directory: reports/$name -> reports/archive/obsolete-pre-demo/$name"
}
