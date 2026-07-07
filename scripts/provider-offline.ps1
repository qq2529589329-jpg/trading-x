param(
    [Parameter(Mandatory = $true)]
    [string]$Date,

    [string]$Source = "tencent_snapshot",

    [string]$Strategy = "A_SPACE_LEADER",

    [string]$SampleInput = "",

    [string]$ReplayOutput = "",

    [string]$OutputDir = "reports/provider_eval",

    [string]$ComplianceUseStatus = "unknown",

    [switch]$TimestampOrderTrusted
)

$ErrorActionPreference = "Stop"

if ($SampleInput -eq "") {
    $SampleInput = "data/provider_samples/$($Date)_$($Source).json"
}
if ($ReplayOutput -eq "") {
    $ReplayOutput = "data/replay/$Date.csv"
}

function Invoke-TradingX {
    param([string[]]$CommandArgs)

    & uv run python -m trading_x @CommandArgs
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

$symbolOutput = & uv run python -m trading_x plans symbols --date $Date --strategy $Strategy
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
$symbols = ($symbolOutput | Out-String).Trim()
if ($symbols -eq "") {
    Write-Output "provider_offline=NO_PLANS $Date $Strategy"
    exit 0
}

if (-not (Test-Path -LiteralPath $SampleInput)) {
    $template = "data/provider_samples/$($Date)_$($Source)_template.json"
    Invoke-TradingX @("provider-sample-template", "--source", $Source, "--date", $Date, "--strategy", $Strategy, "--output", $template)
    Write-Output "provider_sample_missing=$SampleInput"
    Write-Output "provider_sample_template=$template"
    exit 1
}

$timestampFlag = "--no-timestamp-order-trusted"
if ($TimestampOrderTrusted) {
    $timestampFlag = "--timestamp-order-trusted"
}

Invoke-TradingX @(
    "provider-evaluate",
    "--source", $Source,
    "--date", $Date,
    "--symbols", $symbols,
    "--sample", $SampleInput,
    "--output-dir", $OutputDir,
    "--compliance-use-status", $ComplianceUseStatus,
    $timestampFlag
)
Invoke-TradingX @("provider-export-replay", "--source", $Source, "--date", $Date, "--sample", $SampleInput, "--output", $ReplayOutput)
Invoke-TradingX @("replay", "--date", $Date, "--input", $ReplayOutput)
Invoke-TradingX @("replay", "--date", $Date, "--strategy", $Strategy, "--materialize", "--input", $ReplayOutput)
Invoke-TradingX @("watch", "--date", $Date, "--input", $ReplayOutput)
