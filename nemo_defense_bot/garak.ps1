# Ruta del archivo de opciones
$optPath = Join-Path $PSScriptRoot "garak_rest_generator.json"

# JSON del RestGenerator (exactamente el que necesita garak + tu endpoint)
$json = @'
{
  "rest": {
    "RestGenerator": {
      "name": "nemo_guardrails_local",
      "uri": "http://localhost:8000/v1/chat/completions",
      "method": "post",
      "headers": {
        "Content-Type": "application/json"
      },
      "req_template_json_object": {
        "model": "nemo",
        "messages": [
          {
            "role": "user",
            "content": "$INPUT"
          }
        ]
      },
      "response_json": true,
      "response_json_field": "$.messages[0].content",
      "request_timeout": 60
    }
  }
}
'@

# Guardar en UTF-8 sin BOM (forma compatible con PowerShell)
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($optPath, $json, $utf8NoBom)

Write-Host "Wrote generator file to $optPath"

# Ejecutar garak con probes limitadas primero
Write-Host "Ejecutando garak..."
python -m garak --target_type rest --target_name nemo_guardrails_local --generator_option_file $optPath --probes promptinject --verbose
