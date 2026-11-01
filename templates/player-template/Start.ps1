param([int]$Port = 1997, [switch]$NoBrowser)
$ErrorActionPreference = 'Stop'
$serverRoot = [IO.Path]::GetFullPath($PSScriptRoot)
$listener = [Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback, $Port)

try {
  $listener.Start()
} catch {
  Write-Host "Port $Port is already in use. Close the other server or specify -Port <number>."
  exit 1
}

Write-Host "Demo Player running at http://localhost:$Port"
Write-Host "Keep this window open while watching. Close it to stop the server."

if (-not $NoBrowser) {
  Start-Process "http://localhost:$Port"
}

$utf8 = [Text.UTF8Encoding]::new($false)
$types = @{
  '.html' = 'text/html; charset=utf-8'
  '.css'  = 'text/css; charset=utf-8'
  '.mjs'  = 'text/javascript; charset=utf-8'
  '.js'   = 'text/javascript; charset=utf-8'
  '.json' = 'application/json'
  '.bin'  = 'application/octet-stream'
  '.woff2'= 'font/woff2'
  '.png'  = 'image/png'
}

try {
  while ($true) {
    $client = $listener.AcceptTcpClient()
    try {
      $stream = $client.GetStream()
      $stream.ReadTimeout = 3000
      $reader = [IO.StreamReader]::new($stream, [Text.Encoding]::ASCII, $false, 4096, $true)
      $first = $reader.ReadLine()
      if (-not $first) { continue }
      while ($reader.ReadLine()) {}

      $target = ($first -split ' ')[1]
      $relative = [Uri]::UnescapeDataString(($target -split '\?')[0]).TrimStart('/')
      if (-not $relative) { $relative = 'index.html' }
      
      $file = [IO.Path]::GetFullPath([IO.Path]::Combine($serverRoot, $relative.Replace('/', '\')))
      $code = '200 OK'
      $mime = $types[[IO.Path]::GetExtension($file)]
      if (-not $mime) { $mime = 'application/octet-stream' }

      if (-not $file.StartsWith($serverRoot + '\', [StringComparison]::OrdinalIgnoreCase) -and $file -ne $serverRoot) {
        $code = '403 Forbidden'
        $body = $utf8.GetBytes('Forbidden')
      } elseif (-not [IO.File]::Exists($file)) {
        $code = '404 Not Found'
        $body = $utf8.GetBytes('Not found')
      } else {
        $body = [IO.File]::ReadAllBytes($file)
      }

      $header = "HTTP/1.1 $code`r`nContent-Type: $mime`r`nContent-Length: $($body.Length)`r`nConnection: close`r`nCross-Origin-Opener-Policy: same-origin`r`nCross-Origin-Embedder-Policy: require-corp`r`n`r`n"
      $bytes = $utf8.GetBytes($header)
      $stream.Write($bytes, 0, $bytes.Length)
      $stream.Write($body, 0, $body.Length)
    } catch {} finally {
      $client.Close()
    }
  }
} finally {
  $listener.Stop()
}
