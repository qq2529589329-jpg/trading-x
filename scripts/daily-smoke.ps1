param(
    [Parameter(Mandatory = $true)]
    [string]$Date,

    [string]$Strategy = "A_SPACE_LEADER",

    [string]$ReplayInput = ""
)

$ErrorActionPreference = "Stop"

if ($ReplayInput -eq "") {
    $ReplayInput = "data/replay/$Date.csv"
}

function Invoke-TradingX {
    param([string[]]$CommandArgs)

    & uv run python -m trading_x @CommandArgs
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

Invoke-TradingX @("doctor", "--date", $Date)
Invoke-TradingX @("daily", "--date", $Date)
Invoke-TradingX @("acceptance", "--last-complete-n", "10")
Invoke-TradingX @("acceptance", "--list-incomplete")

Invoke-TradingX @("plans", "materialize", "--date", $Date)
Invoke-TradingX @("plans", "symbols", "--date", $Date)
Invoke-TradingX @("plans", "materialize", "--date", $Date, "--strategy", $Strategy)
Invoke-TradingX @("plans", "symbols", "--date", $Date, "--strategy", $Strategy)

if (Test-Path -LiteralPath $ReplayInput) {
    Invoke-TradingX @("replay", "--date", $Date, "--input", $ReplayInput)
    Invoke-TradingX @("replay", "--date", $Date, "--strategy", $Strategy, "--materialize", "--input", $ReplayInput)
    Invoke-TradingX @("watch", "--date", $Date, "--input", $ReplayInput)
} else {
    Write-Output "replay_input_missing=$ReplayInput"
}
