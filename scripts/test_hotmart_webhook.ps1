param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("professional", "constructor", "enterprise")]
    [string]$Plan,

    [Parameter(Mandatory = $true)]
    [string]$HotTok,

    [string]$Email = "prueba.hotmart.geosis@example.com",
    [string]$Name = "Cliente Prueba Hotmart",
    [string]$BaseUrl = "https://geosis.corporativoqbank.com",
    [ValidateSet("PURCHASE_APPROVED", "PURCHASE_REFUNDED", "PURCHASE_CHARGEBACK", "PURCHASE_EXPIRED", "PURCHASE_CANCELED", "SUBSCRIPTION_CANCELLATION")]
    [string]$Event = "PURCHASE_APPROVED"
)

$offerByPlan = @{
    professional = "q8o4jizl"
    constructor  = "xk90je6q"
    enterprise   = "5k5vwivl"
}

$transaction = "SIM-$($Plan.ToUpper())-$(Get-Date -Format 'yyyyMMddHHmmss')"
$offerCode = $offerByPlan[$Plan]

$payload = @{
    event = $Event
    data = @{
        product = @{
            id = 7786167
            name = "GEOSIS-PRO"
        }
        buyer = @{
            name = $Name
            email = $Email
        }
        purchase = @{
            transaction = $transaction
            offer = @{
                code = $offerCode
            }
        }
        subscription = @{
            subscriber = @{
                code = $transaction
            }
        }
    }
} | ConvertTo-Json -Depth 10

$uri = "$BaseUrl/api/hotmart/webhook"
$headers = @{
    "X-Hotmart-HotTok" = $HotTok
    "Content-Type" = "application/json"
}

Write-Host "Enviando webhook simulado a $uri"
Write-Host "Evento: $Event"
Write-Host "Plan: $Plan"
Write-Host "Oferta: $offerCode"
Write-Host "Email: $Email"

try {
    $response = Invoke-RestMethod -Uri $uri -Method Post -Headers $headers -Body $payload
    Write-Host "Respuesta Odoo:"
    $response | ConvertTo-Json -Depth 10
}
catch {
    Write-Host "Error al enviar webhook:"
    if ($_.Exception.Response) {
        Write-Host "HTTP Status:" ([int]$_.Exception.Response.StatusCode)
        Write-Host "HTTP Message:" $_.Exception.Response.StatusDescription
    }
    Write-Host $_.Exception.Message
    exit 1
}
