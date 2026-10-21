# PowerShell script to update or import the workflow into the local n8n Docker container
param (
    [string]$ContainerName = "n8n",
    [string]$WorkflowFile = "$PSScriptRoot\telegram-gmail-agent.json",
    [string]$ProjectId = "r7bwiOzI1VMZbyt8"
)

Write-Host "Updating workflow in container '$ContainerName'..." -ForegroundColor Cyan

# Copy JSON to container
docker cp "$WorkflowFile" "${ContainerName}:/tmp/telegram-gmail-agent.json"
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to copy workflow file to docker container."
    exit 1
}

# Import workflow
docker exec $ContainerName n8n import:workflow --input=/tmp/telegram-gmail-agent.json --projectId=$ProjectId
if ($LASTEXITCODE -eq 0) {
    Write-Host "Successfully imported workflow into n8n project '$ProjectId'!" -ForegroundColor Green
    Write-Host "Open n8n at: http://localhost:5678" -ForegroundColor Yellow
} else {
    Write-Error "Failed to import workflow into n8n."
}
