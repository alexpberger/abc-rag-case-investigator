param(
    [string]$Tag = "1"
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$TerraformDir = Join-Path $Root "infra\terraform"
$Registry = terraform -chdir="$TerraformDir" output -raw acr_name
if (-not $Registry) {
    throw "acr_name is empty. Apply infra/terraform before building images."
}

Push-Location $Root
try {
    az acr build --registry $Registry --image "abc-rag-api:$Tag" --file backend/Dockerfile .
    if ($LASTEXITCODE -ne 0) { throw "API image build failed." }
    az acr build --registry $Registry --image "abc-rag-web:$Tag" --file frontend/Dockerfile frontend
    if ($LASTEXITCODE -ne 0) { throw "Web image build failed." }
}
finally {
    Pop-Location
}

Write-Host "Pushed abc-rag-api:$Tag and abc-rag-web:$Tag. Set image_tag = `"$Tag`" and deploy_container_app = true, then apply again."
