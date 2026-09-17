<#
.SYNOPSIS
    Claude Code PreToolUse Hook - Quality Gate Check
.DESCRIPTION
    Runs before every Bash tool call. Intercepts git commit/push operations
    and verifies that quality gate results (tests + audit) exist and pass.
    Non-git commands pass through immediately.
#>

$ErrorActionPreference = "Stop"

# -------------------------------------------------------------------
# 1. Parse the tool call from stdin
# -------------------------------------------------------------------
$stdinRaw = $input | Out-String

if ([string]::IsNullOrWhiteSpace($stdinRaw)) {
    exit 0
}

try {
    $toolCall = $stdinRaw | ConvertFrom-Json
} catch {
    exit 0
}

$toolName = $toolCall.tool_name
$command = $toolCall.tool_input.command

# -------------------------------------------------------------------
# 2. Only intercept git commit / git push
# -------------------------------------------------------------------
if ($toolName -ne "Bash") {
    exit 0
}

if ($command -notmatch '\bgit\s+(commit|push)\b') {
    exit 0
}

# -------------------------------------------------------------------
# 3. Check quality gate results
# -------------------------------------------------------------------
$checkDir = Join-Path $PWD.Path ".claude\check-results"
$testResultFile = Join-Path $checkDir "test-result.json"
$qualityResultFile = Join-Path $checkDir "quality-result.json"

$testPassed = $false
$qualityPassed = $false

if (Test-Path $testResultFile) {
    try {
        $testResult = Get-Content $testResultFile -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($testResult.passed -eq $true) {
            $testPassed = $true
        }
    } catch { }
}

if (Test-Path $qualityResultFile) {
    try {
        $qualityResult = Get-Content $qualityResultFile -Raw -Encoding UTF8 | ConvertFrom-Json
        $scoreOK = ($qualityResult.score -ge 70)
        $securityOK = ($qualityResult.security -ge 70)
        $criticalOK = ($qualityResult.critical -eq 0)
        if ($scoreOK -and $securityOK -and $criticalOK) {
            $qualityPassed = $true
        }
    } catch { }
}

# -------------------------------------------------------------------
# 4. Verdict
# -------------------------------------------------------------------
if ($testPassed -and $qualityPassed) {
    exit 0
}

# Gate failed - block the operation
$lines = @()
$lines += "===================================================="
$lines += "  QUALITY GATE: FAILED"
$lines += "===================================================="

if ($testPassed) {
    $lines += "  [PASS] Unit tests"
} else {
    $lines += "  [FAIL] Unit tests - result not found or not passed"
    $lines += "         Missing: $testResultFile"
}

if ($qualityPassed) {
    $lines += "  [PASS] Quality audit (score>=70, security>=70, critical=0)"
} else {
    $lines += "  [FAIL] Quality audit - result not found or not passed"
    $lines += "         Missing: $qualityResultFile"
}

$lines += "----------------------------------------------------"
$lines += "  Action: Use gitcommit-agent to run quality checks first"
$lines += "          Or use bypass keyword to skip gate"
$lines += "===================================================="

Write-Host ($lines -join "`n")
exit 1
