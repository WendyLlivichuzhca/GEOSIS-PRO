param(
    [Parameter(Mandatory = $true)]
    [string]$Username,

    [Parameter(Mandatory = $true)]
    [string]$Password,

    [Parameter(Mandatory = $true)]
    [string]$DbName,

    [string]$BaseUrl = "https://geosis.corporativoqbank.com",
    [int]$AvaluoId = 1
)

# Habilitar soporte TLS 1.2
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

# 1. AUTENTICAR CON ODOO (Obtener Session ID)
$authUrl = "$BaseUrl/web/session/authenticate"
$authBody = @{
    jsonrpc = "2.0"
    method = "call"
    params = @{
        db = $DbName
        login = $Username
        password = $Password
    }
} | ConvertTo-Json -Depth 10

Write-Host "Iniciando sesión en $BaseUrl (Base de datos: $DbName)..." -ForegroundColor Cyan
try {
    $authResponse = Invoke-WebRequest -Uri $authUrl -Method Post -Body $authBody -ContentType "application/json" -SessionVariable session
    $authJson = $authResponse.Content | ConvertFrom-Json
    
    if ($authJson.error) {
        Write-Error "Error de autenticación: $($authJson.error.data.message)"
        exit
    }
    
    Write-Host "¡Sesión iniciada con éxito! Usuario: $($authJson.result.username)" -ForegroundColor Green
} catch {
    Write-Error "Error al conectar con Odoo: $_"
    exit
}

# 2. CONSULTAR AVALÚOS DISPONIBLES
$listUrl = "$BaseUrl/web/geosis/avaluos"
$listBody = @{
    jsonrpc = "2.0"
    method = "call"
    params = @{}
} | ConvertTo-Json

Write-Host "`nConsultando listado de avalúos asignados..." -ForegroundColor Cyan
$listResponse = Invoke-WebRequest -Uri $listUrl -Method Post -Body $listBody -ContentType "application/json" -WebSession $session
$listJson = $listResponse.Content | ConvertFrom-Json

if ($listJson.result.status -eq "success") {
    $avCount = $listJson.result.data.Count
    Write-Host "Se encontraron $avCount avalúos:" -ForegroundColor Green
    foreach ($av in $listJson.result.data) {
        Write-Host "  - ID: $($av.id) | Código: $($av.code) | Objeto: $($av.title) | Estado: $($av.state) | Propietario: $($av.owner_name)" -ForegroundColor Yellow
    }
} else {
    Write-Error "Error al listar avalúos: $($listJson.result.message)"
}

# 3. ENVIAR UNA INSPECCIÓN DE PRUEBA (Submit Avalúo)
$submitUrl = "$BaseUrl/web/geosis/submit_avaluo"

# Simulación de una imagen pequeña en base64 (cuadro rojo de 1x1 píxeles)
$dummyImageBase64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="

$submitBody = @{
    jsonrpc = "2.0"
    method = "call"
    params = @{
        avaluo = @{
            id = $AvaluoId
            location = "Av. Francisco de Orellana y Plaza Dañin, Guayaquil"
            latitude = -2.158493
            longitude = -79.889312
            land_area = 300.0
            land_unit_value = 180.0
            land_topography_factor = 1.0
            land_shape_factor = 0.95
            construction_area = 150.0
            construction_replacement_cost = 450.0
            construction_age = 8
            construction_life_expectancy = 50
            construction_state_coef = "0.95" # Estado Bueno
            photos = @(
                @{
                    name = "Fachada Frontal Inmueble"
                    image = $dummyImageBase64
                    latitude = -2.158493
                    longitude = -79.889312
                }
            )
            comparables = @(
                @{
                    name = "Terreno Venta Alborada"
                    area = 250.0
                    price = 45000.0
                    distance_km = 0.8
                },
                @{
                    name = "Casa Comercial Orellana"
                    area = 180.0
                    price = 110000.0
                    distance_km = 0.3
                }
            )
        }
    }
} | ConvertTo-Json -Depth 10

Write-Host "`nEnviando datos de inspección de prueba para el Avalúo ID: $AvaluoId..." -ForegroundColor Cyan
$submitResponse = Invoke-WebRequest -Uri $submitUrl -Method Post -Body $submitBody -ContentType "application/json" -WebSession $session
$submitJson = $submitResponse.Content | ConvertFrom-Json

if ($submitJson.result.status -eq "success") {
    Write-Host "¡Inspección procesada correctamente!" -ForegroundColor Green
    Write-Host "Resumen de Resultados calculados en Odoo:" -ForegroundColor Green
    Write-Host "  - Código Avalúo: $($submitJson.result.data.code)" -ForegroundColor Yellow
    Write-Host "  - Depreciación Aplicada: $($submitJson.result.data.depreciation_percent)%" -ForegroundColor Yellow
    Write-Host "  - Valor Final Terreno: $($submitJson.result.data.land_value) USD" -ForegroundColor Yellow
    Write-Host "  - Valor Final Edificación: $($submitJson.result.data.construction_value) USD" -ForegroundColor Yellow
    Write-Host "  - AVALÚO COMERCIAL TOTAL: $($submitJson.result.data.total_value) USD" -ForegroundColor Yellow
} else {
    Write-Error "Error al subir la inspección: $($submitJson.result.message)"
}
