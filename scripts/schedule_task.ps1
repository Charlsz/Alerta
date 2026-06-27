# Creates a Windows scheduled task to run the pipeline daily at 5 AM and 5 PM.
# Run this script as Administrator once to register the task.
# Requires: Python, pip deps, and .env configured.

$taskName = "AlertaPipeline"
$scriptPath = "$PSScriptRoot\run.py"
$action = New-ScheduledTaskAction -Execute "python" -Argument "$scriptPath ingest; if (`$?) { python $scriptPath features }; if (`$?) { python $scriptPath risk }" -WorkingDirectory (Resolve-Path "$PSScriptRoot\..")
$trigger1 = New-ScheduledTaskTrigger -Daily -At "05:00AM"
$trigger2 = New-ScheduledTaskTrigger -Daily -At "05:00PM"

try {
    Register-ScheduledTask -TaskName $taskName -Action $action -Trigger @($trigger1, $trigger2) -RunLevel Highest -Force
    Write-Output "Scheduled task '$taskName' created. Runs daily at 5:00 AM and 5:00 PM."
} catch {
    Write-Output "Error: $_"
    Write-Output "Run this script as Administrator."
}
