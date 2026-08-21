param([Parameter(Mandatory=$true)][string]$PiHost,[string]$PiUser="pi",[string]$Destination="~")
$ErrorActionPreference="Stop"
& scp -r -- $PSScriptRoot "${PiUser}@${PiHost}:$Destination/"
if($LASTEXITCODE -ne 0){throw "scp failed: $LASTEXITCODE"}
Write-Host "cd $Destination/safenest_pi_thermal_lcd_test2"
