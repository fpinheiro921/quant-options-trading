# setup_scheduler.ps1
# Creates Windows Task Scheduler tasks for AutoTrader
# Run this ONCE as Administrator:
#   Right-click PowerShell -> Run as Administrator
#   cd "H:\02 - TRADING\OPTIONS TRADING\AUTOTRADER"
#   .\setup_scheduler.ps1
#
# TIMEZONE: Portugal (UTC+1 WET / UTC+2 WEST summer)
# US market opens 9:30 AM ET = 14:30 Portugal (summer, Mar-Nov)
#                             = 13:30 Portugal (winter, Nov-Mar)
#
# Tasks run at 14:40 Portugal time (summer) = 10 min after market open
# IMPORTANT: In winter (Nov-Mar) update times to 13:40 manually in Task Scheduler

$pythonPath  = (Get-Command python).Source
$scriptPath  = "H:\02 - TRADING\OPTIONS TRADING\AUTOTRADER\main.py"
$workingDir  = "H:\02 - TRADING\OPTIONS TRADING\AUTOTRADER"

Write-Host "Setting up AutoTrader scheduled tasks..."
Write-Host "Python: $pythonPath"
Write-Host "Script: $scriptPath"
Write-Host "Working Dir: $workingDir"

# -- Task 1: Monday Entry Scan (14:40 Portugal = 09:40 ET summer) ---------------------
$action1   = New-ScheduledTaskAction -Execute $pythonPath -Argument "`"$scriptPath`" --scan" -WorkingDirectory $workingDir
$trigger1  = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At "02:40PM"
$settings1 = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Minutes 10) -RunOnlyIfNetworkAvailable -StartWhenAvailable
Register-ScheduledTask -TaskName "AutoTrader_MondayScan" `
    -Action $action1 -Trigger $trigger1 -Settings $settings1 `
    -Description "Weekly breakout scan and entry - runs every Monday at 14:40 Portugal time (09:40 ET summer)" `
    -RunLevel Highest -Force
Write-Host "[OK] Task created: AutoTrader_MondayScan (14:40 Portugal time)"

# -- Task 2: Tue-Fri Exit Check (14:40 Portugal = 09:40 ET summer) --------------------
$action2   = New-ScheduledTaskAction -Execute $pythonPath -Argument "`"$scriptPath`" --exits" -WorkingDirectory $workingDir
$trigger2  = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Tuesday,Wednesday,Thursday,Friday -At "02:40PM"
$settings2 = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Minutes 10) -RunOnlyIfNetworkAvailable -StartWhenAvailable
Register-ScheduledTask -TaskName "AutoTrader_DailyExits" `
    -Action $action2 -Trigger $trigger2 -Settings $settings2 `
    -Description "Daily exit check for open positions - runs Tue-Fri at 14:40 Portugal time (09:40 ET summer)" `
    -RunLevel Highest -Force
Write-Host "[OK] Task created: AutoTrader_DailyExits (14:40 Portugal time)"

Write-Host ""
Write-Host "All tasks created. View in Task Scheduler -> Task Scheduler Library"
Write-Host ""
Write-Host "IMPORTANT: Your PC must be ON at 14:40 Portugal time Mon-Fri."
Write-Host ""
Write-Host "WINTER REMINDER (Nov-Mar): US clocks don't change with Portugal."
Write-Host "   Update task times to 13:40 when winter begins (US stays on ET)."
Write-Host "   Or just keep 14:40 - you'll just run 1 hour into the session instead of 10 min."
